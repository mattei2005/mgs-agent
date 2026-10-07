# Architecture and runtime

## Components

```text
schema.py          validates immutable manifests
planning.py        groups two campaigns per account bundle
quota.py           per-app+account rolling score/headers
coordination.py    persisted writer lease and reader exclusion
media_registry.py  checksum→vertical/square video IDs
transport.py       Graph Batch + appsecret_proof support
engine.py          independent account lanes and consolidated readback
adapters.py        operation-specific manifest builders
cli.py             validate, plan, media registry and guarded execute
```

## Hot path

```text
prevalidated manifest
→ quota reservation in account lane
→ campaign copy batch
→ shell/adset batch when replacing creatives
→ creative+ad batch with named dependencies
→ one consolidated campaign/adsets/ads readback
→ audit with phase timestamps
```

No intermediate GET occurs. `pure_clone` is one copy batch plus one readback batch. `clone_prestaged` uses staged writes because campaign/adset IDs are dependencies, then one readback batch.

## Account lanes

Quota/state is keyed by `app_key + ad_account_id`, protected with OS file locks and atomic JSON. Distinct accounts may run concurrently; bundles within one account are sequential.

Tier-aware local safety budget:

```text
unknown tier ceiling       100 soft / 120 hard
development_access ceiling  60 hard
standard_access ceiling   9000 hard
clone_prestaged estimate    30/campaign
bundle estimate             60/two campaigns
window                     300s
```

`X-Ad-Account-Usage` and `X-Business-Use-Case-Usage` are persisted separately, including headers returned by an outer batch whose child failed. Unknown tier keeps the configured 100/120 ceiling; `development_access` caps it at 60; `standard_access` uses 9000 and skips the fixed development readback cooldown. Do not infer server capacity only from a local number. A request that does not fit returns `PARTIAL_DEFERRED_QUOTA`, persists completed IDs and resumes without replay.

Each bundle uses separate quota reservation identities for initial write, missing-only recovery and readback-only resume. This prevents an old write reservation from authorizing immediate recovery. Once a fresh recovery reservation exists, its estimate includes targeted reconciliation GETs, missing mutations, required name normalization and the final consolidated readback; fitting recoveries finish in one wave instead of paying a redundant second 305-second cooldown.

Every writer claims a persisted per-account lease before preflight and keeps it across quota/readback deferrals. Diário, Intraday, Snapshot, first-delivery and guardrail reactivation all pass one centralized reader gate and a shared OS lock. They resume only after the writer lease and operation state are complete.

## Media

O registry é obrigatório somente para `clone_prestaged`. `pure_clone` reutiliza os creatives/mídias existentes da fonte e não consulta o registry.

Para `clone_prestaged`, registre somente IDs confirmados por Meta readback no edge `act_{AD_ACCOUNT_ID}/advideos`. O próprio pedido autorizado pode executar pre-stage/upload/readback antes da materialização; não existe obrigação de prepopular o registry sem pedido. A chave é account + asset ID + checksum, os IDs vertical e square precisam existir com `ready=true`, `upload_edge=ad_account_advideos` e `association_verified=true`, e uploads em `/{PAGE_ID}/videos` ficam bloqueados como mídia de campanha.

Never put token, app secret, Page token or signed URL in the registry.

## Security

- User Access Token path remains canonical.
- Token is loaded only for guarded execute through the existing protected credential provider.
- `appsecret_proof` is supported; enable `Require App Secret` only after app secret provisioning and full route validation.
- Canário técnico explicitamente solicitado nasce `PAUSED`.
- Pedido normal de produção preserva `ACTIVE` com `start_time` futuro já selado.
- O guard inicial é por lane: o primeiro bundle de cada `app_key + ad_account_id` funciona como fase guardada/fail-closed; lanes de contas diferentes podem começar em paralelo pelo `ThreadPoolExecutor`, sem canário global serial.
- Audit error records contain type/safe message only.

## Existing-post recovery

- Prioritize standalone creative IDs persisted by slot (`existing_post_creative_ids`, ordered `creative_ids` or successful partial batch children). GET each ID and verify account, source post and exact target `url_tags` before any mutation; a mismatch or conflicting slot identity fails closed.
- Preserve successful standalone IDs separately from the latest error, because a later read failure must not erase earlier side effects. Reconcile missing ads by source lineage in the existing target ad set; never replay campaign/adset copies or create a creative already proven present.
- Only when IDs are unavailable, read the account-scoped creative edge with bounded cursor pagination (100 pages), deduplicate IDs and reject missing/repeated cursors or changing semantic identity. Never follow authenticated `paging.next` URLs directly.
- Match fallback creatives by source post + exact target tags + request name (allowing Meta's appended name suffix); multiple distinct matches fail closed. A generated display-name suffix is not evidence that a creative is missing.
- Regression must cover persisted-ID preference, account/post/UTM mismatch, paginated fallback, repeated/bounded cursors, duplicate semantic matches and preservation of partial-success IDs. Validate maintenance separately before resuming the same sealed campaign request.
- Reusing the source post preserves media/copy/social proof, but does not prove per-creative Advantage+ parity: standalone creation with only `name/object_story_id/url_tags` can reset individual enrollments. Compare each source feature and contextual multi-ad setting after attachment; a missing feature is **unconfirmed**, not automatically OPT_OUT. Keep the test PAUSED and disclose any unresolved UI/API parity, even if the engine reports COMPLETE_PAUSED.
- Do not strip `targeting.age_range` or `targeting.user_age_unknown` as read-only fields. They are supported inputs: age_range controls age suggestions, while user_age_unknown controls WhatsApp Status audience inclusion. Re-sending targeting without them can alter the copy. Compare source/target automation markers as well; HTTP200 and validate-only do not prove the platform retained every marker. Official references: https://developers.facebook.com/documentation/ads-commerce/marketing-api/audiences/reference/advanced-targeting and https://developers.facebook.com/documentation/ads-commerce/marketing-api/audiences/reference/basic-targeting .

## Observability

Every bundle records:

```text
copy_submit
shells
creative_ads
readback
```

Each stage has start, finish and duration. Benchmark p50/p95 only from these audit timings, never from Discord conversation duration.

## Auditoria de confiabilidade e quota

- Diferencie IDs atribuídos ao `record` em memória de IDs persistidos em disco. Audite a janela entre a resposta de cada batch mutante e a próxima chamada; exercite interrupção abrupta com `BaseException` e transporte fake, porque o handler de `Exception` não prova recuperação após SIGKILL/restart. No código atual, `_run_lane` salva o checkpoint antes do bundle e ao concluir/deferir/capturar erro, mas os métodos `_run_*_bundle` não fazem commit intermediário dos IDs; não declare persistência por POST já implementada.
- Verifique pressão viva na decisão de admissão, não apenas coleta de headers. Exercite `reserve` com `acc_id_util_pct=100` e reset positivo em estado isolado; no código atual, `LaneQuotaStore.reserve` usa tier e pontos locais, não bloqueia por essa utilização. Coleta de BUC/usage por si só não comprova gate preventivo de pressão.
- Exercite separadamente HTTPError externo e erro de child Graph Batch ao auditar headers. No código atual, `GraphBatchTransport` preserva headers dos batches HTTP bem-sucedidos, inclusive children falhos, mas não captura os headers do HTTPError externo; `last_outer_headers` pode ficar vazio ou representar a resposta anterior.
- Separe sucesso HTTP do readback de QA semântico e barreira pré-ativação. O engine atual finaliza o status solicitado antes do readback consolidado; o runner realiza verificações adicionais. Não descreva isso como ativação somente após QA global. Qualquer alteração de checkpoint, quota ou ordem de ativação exige autorização estrutural, regressão offline e validação própria, sem canário produtivo implícito.
- Compare benchmarks externos somente com logs equivalentes de mídia fresca/reutilizada, modalidade, quantidade de anúncios, tier, chamadas HTTP, operações lógicas, pesos e tempo E2E. Um documento arquitetural sem esses registros não comprova velocidade superior nem eliminação de rate limit.
