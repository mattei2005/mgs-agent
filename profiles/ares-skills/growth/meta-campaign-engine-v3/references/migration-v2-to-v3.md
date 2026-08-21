# Migration v2 to v3

## Current state

- v2 runner remains at `/root/mgs-agent/scripts/ares-creditoparaveiculo-daily-create.py`.
- Pre-v3 backup is recorded in v3 config.
- No v2 or legacy file is deleted.
- v3 is installed disabled and has no cron.

## Promotion gates

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

Every real Meta canary requires separate operational authorization. Installing v3 does not authorize campaign writes.

A failed request is never blindly replayed. Each account lane writes an independent checkpoint with any known campaign/adset IDs and last stage; the main audit marks `manual_reconciliation_required=true`. Reconcile those PAUSED objects by GET before creating a new request ID or authorizing cleanup.

## Rollback

Before promotion, rollback is simply keeping `enabled=false` and using v2. After promotion, rollback requires:

1. stop new v3 manifests;
2. preserve v3 audits/state;
3. set v3 `write_enabled=false`;
4. validate v2 hashes against the pre-v3 backup/current Git;
5. resume only the exact v2 operation authorized;
6. never delete valid PAUSED Meta objects because readback was deferred.

## Legacy handling

Legacy/one-shot scripts are inventory, not active routing. Do not delete or move them without the file-deletion double-confirmation. The HOT map and skills must point campaign creation to v3 first, with v2 only as explicit rollback.
