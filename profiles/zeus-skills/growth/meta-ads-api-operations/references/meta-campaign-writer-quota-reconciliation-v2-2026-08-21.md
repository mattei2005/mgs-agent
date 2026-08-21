# Meta campaign writer quota and reconciliation v2 (2026-08-21)

## Durable lesson

A campaign writer must not audit the whole ad-account portfolio before every dry-run, retry or write. Graph batch reduces HTTP round-trips, but every child request still consumes logical Meta quota. In the CPV incident, repeated global reconciliation dominated quota far more than the requested two campaigns.

## Validated architecture

1. Run current+archived ad/media reconciliation in a separate read-only process.
2. Persist an expiring manifest keyed by asset ID, Drive ID and checksum, with per-asset conflicts and approval state.
3. The campaign writer accepts only assets approved by that manifest and performs zero portfolio scans. Missing, expired, conflicted or identity-drifted manifests block before upload/write.
4. Parse `X-Ad-Account-Usage` separately from `X-Business-Use-Case-Usage`. A low BUC percentage does not prove ad-account score capacity.
5. Meta may omit `X-Ad-Account-Usage` while still returning the tier in BUC. Treat absence as unknown, not zero. Use a local 300-second rolling ledger only after a full warmup: Ads Management reads cost 1, mutations cost 3, every batch child counts, and the outer transport is not charged again.
6. Project each stage plus a readback reserve before the first write. During ledger warmup, fail closed.
7. In `development_access`, if two campaigns do not fit but one does, prepare only the first PAUSED and persist the next sequential slot as `preflight_deferred`. If one does not fit, do nothing.
8. `17/2446079` after object IDs exist defers readback; it does not justify deleting otherwise valid PAUSED objects. Use header reset when present, otherwise the documented 300-second fallback.

## Clone route separation

- Daily new-creative replacement: shallow native campaign/adset clone, then attach approved new creatives.
- Faithful source clone above the synchronous child limit: `async_batch_requests` + deep copy, PAUSED, bounded request-set polling and source-to-copy ID mapping.
- Async/batch is orchestration, never a quota bypass.

## Validation evidence

The validated CPV route-v2 dry-run used a 6/6 approved manifest, performed zero global reconciliation calls in the writer, selected C12, deferred C13, and projected 50 logical points for one campaign versus 95 for two. Unit/behavior coverage passed 38 tests. Creation and activation remained paused and no Meta write was used for validation.

## Verification checklist

- Separate reconciler and expiring manifest exist.
- Writer source contains no full-account ad/media traversal.
- Every selected asset passes manifest ID/Drive/checksum/conflict checks.
- Tier and quota source are explicit: X-Ad header or mature local ledger.
- Logical score includes batch children and readback reserve.
- PAUSED staging and sequential continuation are persisted.
- Production crons stay paused until the approved canary gate.
