# Migration v2 to v3

## Current state

- v2 runner remains at `/root/mgs-agent/scripts/ares-creditoparaveiculo-daily-create.py`.
- Pre-v3 backup is recorded in v3 config.
- No v2 or legacy file is deleted.
- v3 is active as the production route under `development_access` guards and has no recurring cron.

## Activation gates

```text
Gate 1  unit/behavior tests
Gate 2  live read-only source/template refresh
Gate 3  six media assets pre-staged and read back
Gate 4  manifest validate + plan
Gate 5  one PAUSED campaign canary
Gate 6  two PAUSED campaign bundle + one readback batch
Gate 7  three-account synthetic/live-approved lane test
Gate 8  1→3→10→40 rollout with p50/p95
```

Gates 1–4 and the synthetic scale validation are complete. The first authorized production request executes Gate 5 automatically/fail-closed; if it succeeds, the same request can continue to Gate 6 and remaining bundles according to the lane quota. A normal campaign request is the operational authorization for its own objects; no extra architecture confirmation is inserted.

A failed request is never blindly replayed. Each account lane writes an independent checkpoint with any known campaign/adset/ad IDs and last stage; the main audit marks `automatic_recovery_required=true`, `manual_reconciliation_required=false` and preserves the same request ID. The engine reads back the target hierarchy, reuses every valid object already created and writes only the missing or invalid layer. Cleanup, budget expansion, billing, credentials or strategy changes remain outside this standing recovery scope.

## Rollback

Rollback from the active v3 route requires:

1. stop new v3 manifests;
2. preserve v3 audits/state;
3. set v3 `write_enabled=false`;
4. validate v2 hashes against the pre-v3 backup/current Git;
5. resume only the exact v2 operation authorized;
6. never delete valid PAUSED Meta objects because readback was deferred.

## Legacy handling

Legacy/one-shot scripts are inventory, not active routing. Do not delete or move them without the file-deletion double-confirmation. The HOT map and skills must point campaign creation to v3 first, with v2 only as explicit rollback.
