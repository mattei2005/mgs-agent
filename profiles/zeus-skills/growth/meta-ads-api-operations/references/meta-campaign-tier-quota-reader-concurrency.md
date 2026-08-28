# Meta campaign tier, quota and reader-concurrency contract

Use this reference when campaign creation is correct but unexpectedly slow, a peer benchmark uses the same permission scopes, transient Meta batch children fail, or reporting crons can overlap a resumable campaign request.

## Evidence classification

- Accept Rodolfo's confirmation that a peer uses the same permissions as evidence of equal scope coverage; do not dismiss or relitigate it.
- Equal permission names do not establish equal Marketing API tier, batching, media readiness, call cost or account-lane distribution. Require a peer header only before claiming equal tier.
- Keep three quantities separate: configured client ceiling, live tier-derived effective ceiling, and projected operation cost.
- Parse `X-Ad-Account-Usage` and `X-Business-Use-Case-Usage` independently. Persist headers from a failed outer batch in a `finally` path so a transient child error does not erase tier evidence.

## Tier-aware quota

- Unknown tier may use the configured soft/hard ceiling.
- Live `development_access` must cap the lane at Meta's development ceiling even when local config says 120.
- Live `standard_access` must skip development-only fixed cooldowns and follow its production ceiling plus live utilization/reset evidence.
- A client-side increase from 60 to 120 restores configuration intent; it does not increase server capacity by itself.

## Safe transient recovery

1. Persist successful child IDs immediately.
2. Reconcile ambiguous slots/lineage before any retry.
3. Repeat only children proven missing; normalize names/status only when live state differs.
4. Use distinct quota reservation identities for initial `write`, missing-only `recovery`, and `readback`. Never reuse an old write reservation to authorize recovery.
5. A fresh recovery reservation should estimate reconciliation GETs, missing mutations, necessary normalization and final consolidated readback. If it covers the total, finish in the same wave instead of adding a redundant post-recovery cooldown.
6. If capacity is insufficient, persist a resumable state and defer without replay.

## Reader exclusion

- Claim a persisted per-account writer lease before campaign preflight and keep it across quota/readback/recovery deferrals.
- Every recurring reader for the same account must pass one central gate and defer silently while the lease or operation state is resumable.
- Use a shared OS lock as a second process-level guard, not as the only cross-tick coordination mechanism.
- Do not rely only on cron rescheduling: manual campaign requests can arrive at any time.

## Validation

- Test development and standard behavior separately.
- Test failed outer-batch headers are still recorded.
- Test immediate recovery cannot reuse the write reservation.
- Test a fresh sufficient recovery reservation performs final readback without a second cooldown.
- Test every active reader wrapper uses the central gate and shared lock.
- Run an offline smoke proving unique IDs, no replay and zero external network calls.
- Report measured preparation, execution and wait time separately; label benchmark projections as projections.
