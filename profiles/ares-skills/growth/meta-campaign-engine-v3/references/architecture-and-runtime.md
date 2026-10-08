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

No intermediate GET occurs. The legacy `pure_clone` without tracking-aware ads uses one native copy batch plus one readback batch. Tracking-aware clones use campaign/adset shells and deterministic creative materialization/attachment; `full_media_two_phase` carries the complete flexible package instead of only a post ID. Source posts are not sufficient media representations for flexible references. `clone_prestaged` uses staged writes because campaign/adset IDs are dependencies, then one consolidated readback batch.

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

- Resolve credential type/reference from the registered account and operation; SHEIN corporate System User and advertiser User Access Tokens are not interchangeable fallbacks.
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
- Reusing the source post preserves social proof only when the post actually represents the required media. Flexible packages can exist outside the effective post; use the complete media route and declare new posts, or block an explicit `preserve_posts=true` request before write. Post reuse also does not prove per-creative Advantage+ parity: compare approved enrollments and contextual settings after attachment. Compare each source feature and contextual multi-ad setting after attachment; a missing feature is **unconfirmed**, not automatically OPT_OUT. Keep the test PAUSED and disclose any unresolved UI/API parity, even if the engine reports COMPLETE_PAUSED.
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

- Persistir intenção antes de cada batch mutante e IDs/slots confirmados imediatamente após a resposta, antes da próxima fase. `progress.py` usa contexto isolado por lane, journal de incerteza e checkpoint com fsync de arquivo/diretório; snapshots em memória não contam como persistência. Na retomada, registros IN_PROGRESS/RECOVERING são reconciliados, não tratados como bundles novos. Exercitar interrupção abrupta com BaseException antes do attach e comprovar zero campanha/adset/creative/ad duplicado. Um POST sem resposta/ID permanece incerto: consulta scoped e espera de convergência precedem qualquer missing-only; nunca replay de copy não identificado. Essa implementação supersede a limitação anterior de checkpoint somente entre bundles.
- Verifique pressão viva na decisão de admissão, não apenas coleta de headers. Exercite `reserve` com `acc_id_util_pct=100` e reset positivo em estado isolado; no código atual, `LaneQuotaStore.reserve` usa tier e pontos locais, não bloqueia por essa utilização. Coleta de BUC/usage por si só não comprova gate preventivo de pressão.
- Exercitar separadamente HTTPError externo e erro de child Graph Batch ao auditar headers. `GraphBatchTransport` limpa o header anterior antes do envio e preserva os headers da resposta atual também no HTTPError externo; nunca usar uma observação antiga como se viesse do erro atual. O transporte não recebe retry cego de POST.
- Separar sucesso HTTP, QA semântico, mídia renderizada e serving. Na rota SHEIN vigente, qualquer quantidade nasce PAUSED, o runner fecha QA/postprocess e só a fase central activate_verified aplica o ACTIVE previamente autorizado. Essa fase exige proofs vinculados aos mesmos IDs/digests e relê mídia/tracking/ownership antes do status write. Não extrapolar esse lifecycle para outras operações: seus contratos continuam soberanos. Toda mudança estrutural exige regressão e aprovação própria; testes offline não autorizam canário produtivo.
- Compare benchmarks externos somente com logs equivalentes de mídia fresca/reutilizada, modalidade, quantidade de anúncios, tier, chamadas HTTP, operações lógicas, pesos e tempo E2E. Um documento arquitetural sem esses registros não comprova velocidade superior nem eliminação de rate limit.
