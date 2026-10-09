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

## Same-ID SHEIN CBO recovery and explicit NOW continuation

- In CBO cap changes, build a campaign-atomic `bid_strategy` + `adset_bid_amounts={confirmed_adset_id: integer_minor_units}` through the central `cbo_bid.shell_payloads`; do not send the cap again as an independent adset bid update. Use the same builder for initial execution and shell recovery. Confirm account/parent identities and live cap/budget before filling missing ads; never repeat campaign/adset copies when their IDs are already confirmed.
- Resume an explicitly approved NOW continuation through `scripts/ares-shein-recovery.py --continuation <descriptor.json> --confirm-execute`, which delegates to the existing runner/Engine and locks. Never rewrite the original request/sealed manifests, change request identity, reset the original E2E clock or create a parallel writer to bypass an immutable-request guard.
- Bind the descriptor to the exact human message and live sender permissions, original account/channel/quantity/budget/strategy, persisted campaign/adset IDs and original manifest digests. A reviewed late recovery remains request-scoped; it does not disable the global SLA or authorize late activation of another request. Record the missed original SLA honestly.
- If Meta normalized the already-created copy's schedule by one second, prove both original live shell times before recovery and bind that exact preserved time to the authenticated continuation. Only that request may reconcile the bounded normalization; ordinary schedules remain exact, and no start_time write is implied. A later ACTIVE-target parse can also reject an elapsed schedule before activation: allow only the exact original target inside the verified continuation, never a global future-time bypass.
- `COMPLETE_PAUSED` plus runner `POSTPROCESS_PENDING` means creation is finished but QA/activation is not. Read the persisted core result first; retry only QA/proof/status/readback. Compact readbacks are not full creative-definition evidence. Rendered-media proof, semantic QA, status-only activation and exact final readback remain mandatory.
- Keep one execution owner. At handoff, prove no active writer, freeze runtime patches, name exact remaining QA gates and entry point, and transfer operational execution to Ares. Zeus may close inventory/audit/documentation but must not retry Meta concurrently.
- Zeus accepts authentic technical handoffs derived from already-authorized manager/operator commands without another Rodolfo OK under `context/routes.md#delegação-permanente-de-recovery-ares-zeus`. This is limited recovery delegation, not Full bot access; Critical Subset, credential/billing and changed-scope gates remain unchanged.

## Independent executor audit gates

- Exercise HTTP-200 readbacks containing a wrong campaign identity/budget and missing children. Require semantic rejection against the sealed manifest; recording a response count or HTTP success is not QA. Distinguish engine completion from the runner's independent semantic acceptance.
- Exercise controlled abrupt interruption after a mutating response and before the next request. Check the durable file, not the in-memory record; exception handlers alone do not prove recovery from process death. Include write intent and partial-success children in the recovery model, without replaying uncertain POSTs.
- Test usage observation separately for outer successful responses, outer HTTP errors and Graph Batch child headers. Confirm that the actual capacity decision respects observed utilization/reset, rather than merely storing them. Preserve header provenance/freshness and never present stale pressure as a new live observation.
- Derive phase reservations from the concrete mode, ad count, mutations, reads and bounded recovery margin. Fixed per-mode costs can understate a two-phase existing-post route. Label the general documented read/write weighting as a projection, not a measured server charge, because endpoint-specific copying/materialization costs require live evidence.
- Measure user-visible latency from the exact Discord request timestamp to semantic final readback, and report request-to-final-response separately when relevant. A timer starting at the first tool excludes dispatch/pre-tool delay and must be labeled as such; never call it the entire user wait. Keep engine duration separate from both.
- Treat unweighted local limiter units as a design convention, not automatically an implementation error or a Meta quota. Verify conservative calibration and header-based backoff. Compare external speed claims using equivalent media freshness, structure, tier and complete phase timings; an architecture document alone neither proves nor disproves a reported live success.