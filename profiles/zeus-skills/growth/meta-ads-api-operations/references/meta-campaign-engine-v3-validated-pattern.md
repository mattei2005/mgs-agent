# Validated Campaign Engine v3 pattern

Use this implementation pattern for high-scale Meta campaign executors; it was validated offline, not as proof of live Meta throughput.

1. Separate media pre-staging from campaign execution. Commit registry entries only after both required Meta media IDs are ready and match account + asset + checksum.
2. Seal the final manifest with a content digest after schema, media, source, UTM, schedule and payload checks. Any later mutation invalidates execute.
3. Bundle two campaigns from the same ad account. Run distinct accounts in independent `app_key + ad_account_id` lanes; never serialize unrelated accounts behind one global lock.
4. Treat local 100/120 as an executor safety budget, not Meta server quota. In `development_access`, retain reservations for the full 300-second window. In live `standard_access`, release a completed bundle only after a fresh usage header shows utilization below the safety threshold.
5. Use named Graph Batch dependencies for `creative → ad`, zero intermediate GETs, and one consolidated campaign/adsets/ads readback per two-campaign bundle.
6. Persist per-lane checkpoints with known campaign/adset IDs and stage timings. A failed request requires reconciliation and is blocked from blind replay under the same request ID.
7. Support server-side `appsecret_proof`, but enable Meta's Require App Secret only after every route and credential source is proven compatible.
8. Keep engine, write and media-upload gates independent and disabled at install. Offline tests and synthetic 40-campaign orchestration do not prove live Meta permission or throughput readiness.

Promotion order:

```text
source/template read-only refresh
→ media pre-stage canary
→ sealed manifest
→ one PAUSED campaign
→ two PAUSED campaigns with one consolidated readback
→ bounded multi-account rollout
```

Keep the old executor frozen as rollback until live canaries pass.