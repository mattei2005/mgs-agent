# High-volume Meta benchmark preflight — 2026-09-05

## Scope

Use this evidence when a production-like benchmark creates many campaigns across multiple ad accounts and the speed result is only meaningful if the input state and downstream safety lanes are healthy first.

The observed test requested 40 CPV campaigns: 20 in account 05 and 20 in account 13, each `1×1×3`, USD25, future 00:30 São Paulo start, unique Drive creatives, no automatic deletion and no Drive status movement.

## Validated preflight stop

The first attempt stopped before any side effect because account 05 had ambiguous duplicate campaign numbering/source selection. The verified stop state was:

```text
campaigns created     0/40
Meta uploads          0
assets reserved       0
Drive moves           0
budget writes         0
```

This was correct fail-closed behavior. Selecting “latest” only by `created_time` was unsafe because current candidates shared the same timestamp and duplicate sequence labels existed.

After Rodolfo cleaned the duplicates, live readback confirmed account 05 contained one non-deleted campaign for each C01–C14, all PAUSED, with C15–C34 free. Rodolfo then explicitly required a complete restart “as a new request,” not continuation from the aborted preflight.

## Required gates before a new high-volume run

1. Paginate live campaigns in every target account and classify terminal versus non-terminal objects.
2. Parse the campaign sequence from the canonical naming contract and require uniqueness across all non-terminal objects. Report duplicate IDs explicitly; never resolve a tie by array order or `created_time` alone.
3. Confirm the exact source campaign/adset/ad IDs and their operational role. Historical and current objects with the same visible sequence are not interchangeable.
4. Validate the proposed target ranges are fully free before reservation or upload.
5. Check the health of every downstream consumer that must protect the new campaigns: first-delivery watcher, reactivation, intraday, daily and relevant guardrails. Require the consumer to accept the exact provenance key emitted by the planned engine and require its failure streak to be healthy before writes.
6. Confirm `standard_access` independently per `app_key + account_id` lane. A shared cache is not sufficient.
7. Seal separate account plans and prove lanes are independent; do not serialize unrelated accounts behind a global lock.
8. Only after all gates pass: reserve assets, pre-stage media, seal manifests and execute.

## Provenance mismatch evidence

A background audit found the account-13 first-delivery monitor in a repeated-failure state because its validator accepted one v3 provenance label while current campaign records emitted another. The durable lesson is not to hardcode a guessed replacement string. The gate is to prove producer/consumer compatibility with a fixture and a real healthy monitor tick before the benchmark. A campaign-creation success is not operational success when the safety consumer cannot recognize the result.

## Fresh restart semantics

When the owner explicitly says the benchmark must restart as a new request:

- issue a new request ID, checkpoint, manifest digest and reservation identity;
- clear/reconcile old writer leases and prove no side effects remain;
- do not reuse old selections as authoritative; run live preflight again;
- anchor timing at the fresh authorization message;
- exclude the aborted zero-write attempt from the primary campaigns/minute metric;
- retain the aborted attempt separately as agent/preflight overhead and evidence of a caught defect.

## Timing/reporting

Separate:

```text
conversation/human wait
agent discovery and broad search
preflight and reconciliation
Drive/render/pre-stage
engine/API per account lane
quota/cooldown/recovery
readback/postprocess
```

Only the engine/API segment can prove the throughput effect of `standard_access`. The final audit must programmatically dedupe and verify 20+20 campaigns, 40 adsets and 120 ads before declaring completion.

## Temporary-test asset exception

Rodolfo clarified that, for this explicitly temporary benchmark, `ares_eligible=false`, `RESERVADO_PELO_GESTOR` and `LEGACY_NEEDS_META_RECONCILIATION` were not blockers by themselves. This exception is benchmark-scoped, not a production rule. Required checks remained: exact Drive ID/checksum, unique asset use inside the 120-asset selection, no forbidden status/folder movement and no impact on production campaigns.

A monitor must not combine a waived reservation rule with an unrelated guardrail failure. Classify each gate independently and stop repeating a corrected false alert.

## Interrupted pre-stage and cancellation evidence

The fresh attempt was stopped before the Campaign Engine ran. Terminal readback showed zero campaigns, ad sets, ads, budget/spend, Drive moves and inventory reservations, but pre-stage had already materialized 40 account-level technical videos: 26 in account 05 and 14 in account 13. Seventeen registry records represented 34 videos; six videos had no registry record. No ad referenced those videos.

The durable design rules are:

1. Before the first media upload, persist a preparatory request record with request ID, account, exact asset set and per-asset states such as `pending`, `uploaded_vertical`, `uploaded_square`, `registered` and `cancelled`. The final campaign manifest may still depend on returned media IDs; do not confuse the preparatory checkpoint with the sealed execution manifest.
2. Register each successfully materialized orientation immediately, not only after a vertical+square pair completes. Include request ID, account, worker, asset and phase so cancellation can enumerate every side effect.
3. Use cooperative cancellation between assets plus process-group termination. Do not wait through a long blocking poll before killing sibling workers; measure stop-message-to-last-worker latency.
4. Do not switch from a serial ad-hoc runner to newly authored parallel workers inside the benchmark hot path. Version and test the bounded parallel pre-stage runner before authorization.
5. Before scaling temporary uploads, prove a cleanup route for the same Meta object type, account and actor, or disclose that cancellation can leave media residues. In this incident, both advertiser and Page-token deletion attempts were rejected with `code=10/subcode=1363055`; the first object remained present, so the operation correctly stopped rather than presenting an unverified retry route as cleanup.
6. Report cancellation and cleanup separately. `0 campaigns` and `0 spend` can coexist with residual Meta media.

## Executive closure format

For a cancelled benchmark, lead with:

```text
Cancelado/parado     exact zero-state for campaigns, ads, spend and processes
Não desfeito         exact Meta/media residues and cleanup blocker
```

Only then include detailed throughput and architecture findings. This avoids making a correct but long audit sound as though campaign objects still exist when the only residue is unattached technical media.
