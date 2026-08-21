# High-scale Meta campaign engine architecture (2026-08-21)

## Trigger

Use when Ares is asked to create/clone campaigns in bulk, operate several ad accounts in parallel, reduce visible `Searching`/live patching, or approach a benchmark such as 40 clones across three accounts in 15 minutes.

## Confirmed external executor pattern

Rodolfo's operator screenshots confirmed the benchmark engine is a standardized program separate from the agent, shared by every topic and currently described as optimization v23. It uses separate API-protection and flow-validation components. Its operating loop is reference → build → audit → execute PAUSED → final GET; improvements happen after execution, not by editing code inside the production request. New media is uploaded to the Facebook library before campaign construction; the operator attributes about five extra minutes to the Drive/upload route. The same executor reportedly handled 100 campaigns in one operation after mapping an initial >99 barrier.

This evidence strengthens the hot-path invariant below: do not let each Ares conversation invent or patch its own executor.

## First distinction: three workloads

```text
Pure clone                  copy campaign/adsets/ads/creatives as-is
Clone + pre-staged media    copy structure; create creatives from ready video_id/image_hash
Clone + raw media           download/transform/upload/process media before campaign objects
```

Never compare throughput without identifying the workload. Pure clone can be one asynchronous copy operation per hierarchy. Raw-media replacement is a different product.

## MGS benchmark interpretation

Forty clones over three accounts in 15 minutes is 22.5 seconds per clone globally, but about 67.5 seconds per clone in each account lane if work is evenly distributed. The successful CPV v2 path measured about 115.6 and 123.2 seconds per campaign. Its clean-path gap was therefore roughly 1.77x per lane; the 30–40 minute user-visible delay came from failed attempts, cleanup, quota separation and live engineering.

## Hot-path invariant

Production execution is:

```text
request -> manifest -> one deterministic command -> final result
```

No `search_files`, skill exploration, code edits, test authoring, cron creation or ad-hoc retries inside the campaign transaction. If the operation is unsupported, fail before asset reservation and improve the engine separately.

## Required decomposition

1. `planner`: validates operation contract, numbers, budget, source and idempotency.
2. `media_registry`: maps checksum/account/Page to ready vertical/square video IDs.
3. `account_lane`: owns app+ad-account quota state and mutation lock.
4. `batch_executor`: submits copy/create stages with dependencies.
5. `validator`: accepts `IN_PROCESS`, polls boundedly and fails only terminal issues/timeouts.
6. `state_audit`: persists request IDs, stage timestamps, copied IDs and readback.

Do not keep these in a single multi-thousand-line writer.

## Throughput architecture

### Pre-stage media

When an asset enters READY, prepare derivatives and upload them before a campaign request exists. The campaign hot path receives only ready Meta IDs. Meta documents creation from existing `video_id`; use that capability instead of reuploading the same bytes.

### Account lanes

Use one lane/lock/state per `app_id + ad_account_id`. Keep app-level protection separately. Do not serialize unrelated accounts through one global `last_request_monotonic`; Meta mutation QPS is scoped per app+ad-account combination.

### Pure clone

Use campaign/adset copies through asynchronous batch. Campaign deep copy supports up to 51 child ads asynchronously. Adset copy documentation explicitly recommends asynchronous batch for large numbers and allows up to 50 requests in one HTTP submission.

### New pre-staged creatives

Use normal Graph batch with named operations/JSONPath dependencies:

1. copy campaign/adset shells;
2. create up to three campaigns' creatives/ads per ads batch (Meta recommends <=10 ads per batch);
3. consolidated ID readback.

Every child still counts toward quota; batching is for latency/dependencies, not quota bypass.

### Native scheduling

Name by delivery date. Create the adset with future `start_time` and `ACTIVE`, validate the exact timestamp, then leave the campaign `ACTIVE`. This removes the normal activation job. Keep one-shot activation only for legacy adsets whose start time is already immutable.

### Post-processing

`IN_PROCESS` is normal. Meta documents that regular updates to objects/children can continue in this state. Replace blind fixed sleeps with bounded status polling and inspect `WITH_ISSUES`/`issues_info` only as terminal failure evidence.

## Current CPV findings to fix before scale

- Writer is 1,740 lines/69 functions; `execute()` is 491 lines.
- Media preparation/upload occurs before campaign/adset copy, contrary to the stated clone-first route.
- Downloads, ffmpeg crops, six uploads, three creatives, three validates and three ad creates are sequential.
- Two fixed five-second sleeps remain.
- Async deep-copy helpers exist but are not called.
- `CLONE_WRITE_CALLS_PER_CAMPAIGN=12` undercounts the current path; campaign copy+update, adset copy+update, 3 creatives, 3 validates and 3 ad creates equals 13 mutations.
- Shared Meta throttle uses one global state/lock, blocking independent accounts.
- CPV runtime has 26 files, including 16 legacy/completed artifacts and 19 pycache residues near the live route.
- Active rules conflict: older skill/config text says PAUSED plus later activation; newer operation state prefers native future scheduling.

## Verification targets

```text
Searching/editing in hot path          0
Global reconciliation per creation     0
Pure clone p95 per account lane         <= 70s target
Pre-staged replacement p95 per lane     <= 75s target
Account concurrency                     independent lanes
Activation jobs on normal route         0
Known-rule failures in production       0
```

These are targets, not validated performance claims. Instrument `plan`, `asset_ready`, `copy_submit`, `copy_ready`, `creatives`, `ads`, and `readback` timestamps, then compare p50/p95.

## Rollout

1. Freeze v2 as rollback.
2. Remove/archive legacy route artifacts only under an approved exact manifest.
3. Build the modular engine and per-account throttle state.
4. Pre-stage a bounded asset pool.
5. Canary 1 campaign, then 3, then 10.
6. Run a 40-clone three-account test only with explicit approval, future start/PAUSED safety and no immediate delivery.
7. Promote only after hierarchy, UTM, quota, throughput and rollback pass.

## Official sources

- https://developers.facebook.com/docs/marketing-api/asyncrequests/
- https://developers.facebook.com/docs/graph-api/batch-requests/
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies/
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/
- https://developers.facebook.com/docs/marketing-api/guides/videoads/
- https://developers.facebook.com/docs/marketing-api/using-the-api/post-processing/
- https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/
- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting/
