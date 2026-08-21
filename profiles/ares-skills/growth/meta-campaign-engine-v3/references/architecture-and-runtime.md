# Architecture and runtime

## Components

```text
schema.py          validates immutable manifests
planning.py        groups two campaigns per account bundle
quota.py           per-app+account rolling score/headers
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

Initial local safety budget:

```text
soft score                 100
hard score                 120
clone_prestaged estimate    45/campaign
bundle estimate             90/two campaigns
window                     300s
```

`X-Ad-Account-Usage` and `X-Business-Use-Case-Usage` are persisted separately when Meta returns them. Do not infer server capacity only from the local counter. In `development_access` the rolling reservation remains for 300 seconds: if a request has more bundles than fit, the engine returns `PARTIAL_DEFERRED_QUOTA`, persists completed IDs and next bundle, and resumes the same request after the window without replaying completed bundles. In live `standard_access`, a completed bundle releases its local reservation only when the latest account usage is below 80%; server headers remain the controlling safety signal for the next wave.

## Media

O registry é obrigatório somente para `clone_prestaged`. `pure_clone` reutiliza os creatives/mídias existentes da fonte e não consulta o registry.

Para `clone_prestaged`, registre somente IDs confirmados por Meta readback. O próprio pedido autorizado pode executar pre-stage/upload/readback antes da materialização; não existe obrigação de prepopular o registry sem pedido. A chave é account + asset ID + checksum, e os IDs vertical e square precisam existir com `ready=true`.

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
