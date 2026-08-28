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

## Observability

Every bundle records:

```text
copy_submit
shells
creative_ads
readback
```

Each stage has start, finish and duration. Benchmark p50/p95 only from these audit timings, never from Discord conversation duration.
