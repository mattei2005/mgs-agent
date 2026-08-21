# Campaign engine scheduler cutover — durable checklist

Use when a new Meta campaign engine is declared active but production is also expected to run on a recurring schedule.

## Core lesson

**Engine activation is not scheduler cutover.** A migration is incomplete while the recurring job is paused, points to the legacy wrapper, or lacks live scheduler readback. Before telling Rodolfo to “wait for the next schedule,” inspect the actual target job and prove that it invokes the new runner.

## Required cutover sequence

1. Inventory the live job by ID: name, script, enabled/state, schedule, next run, no-agent mode and delivery.
2. Preserve the legacy wrapper/runner as rollback; do not re-enable it as the new route.
3. Implement a deterministic scheduled materializer around the central engine:
   - account/Page/Business health preflight;
   - current budget and next sequence;
   - Drive Service Account and inventory;
   - pre-hot-path Meta×Drive reconciliation;
   - media selection/pre-stage/ready registry;
   - manifest creation, sealing and engine execution;
   - hierarchy readback, inventory/Drive finalization and stock report;
   - quota-deferred resume without replay.
4. Validate in this order: compile/bash syntax → focused tests → full relevant suite → offline smoke → live read-only plan.
5. Keep the recurring job paused until an independent reviewer accepts the code and live plan.
6. Switch the existing job ID in place to the v3 wrapper, retain no-agent/local delivery, and enable it.
7. Read back with the actual profile CLI (for Ares: `hermes -p ares cron list`) and verify active/scheduled, exact script and next run.
8. Align the operation source, checkpoint, inventory, audit and REPORT-INFRA.
9. Ask Ares to perform a final readback only; do not manually fire the production job during cutover.

Completion criterion: the engine, operation source and live scheduler all point to v3; the legacy runner is rollback-only; the next scheduled cycle can actually execute.

## Scheduler shape for timezone-gated/resumable work

A robust pattern is an hourly no-agent job whose deterministic wrapper:

- starts a fresh cycle only at the operation timezone gate (for CPV, 17:00 São Paulo);
- stays silent outside the gate;
- may resume later hours only for explicitly resumable states after `retry_after_epoch`;
- returns nonzero for manual-reconciliation states and zero for safe deferred continuation;
- posts only sanitized operational summaries.

## Planning and budget guards

- Desired campaign count is not automatically executable count.
- Compute `capacity = floor((account_cap - active_budget) / initial_budget)`.
- Select `min(desired, capacity)` when capacity is at least one; fail closed only when zero campaigns fit.
- Persist `desired_count`, `selected_count` and `deferred_by_budget_count`; do not silently claim all desired campaigns completed.
- Derive next numbers from non-deleted/non-archived live campaigns; test/archived campaigns must not advance the production sequence.

## Crash/idempotency P0 guards

Before enabling the cron, require tests for:

1. **Campaign collision:** exact manifest names found live block unless mapped to the same request IDs. This covers a hard crash after Meta commit but before checkpoint persistence.
2. **Checksum-bound media reuse:** deterministic Page-video titles include asset ID plus checksum prefix; never reuse by asset ID alone.
3. **Resumable side effects:**
   - possible upload → readback-deferred/resumable;
   - campaign write with known IDs → readback-deferred/resumable;
   - write without known IDs → manual reconciliation;
   - postprocess/move failure → postprocess-pending;
   - `FAILED` only when no external side effect occurred.
4. **Cache-first credentials:** recurring runners never force-refresh 1Password on each tick; use the canonical cache helper.
5. **Idempotent Drive move and postprocess:** already-moved assets do not receive a second PATCH.
6. **Pending-only budget on resume:** do not charge completed bundles again.

## Throughput observability

Because Rodolfo will judge the next cycle by real speed, instrument the scheduled audit before rollout. Keep a stable phase order and sanitized counters:

```text
meta_preflight
drive_preflight
reconciliation
asset_selection
prestage
manifest_prevalidation
engine
postprocess
```

Record `duration_ms`, logical call counts, skipped state and non-sensitive details. Pre-stage should expose download, render, upload and ready-readback time. Use the first live cycle to decide whether to separate/refresh reconciliation earlier or parallelize media uploads; do not optimize from Discord conversation duration.

## Workload distinction

- `pure_clone` does not require the media registry.
- `clone_prestaged` requires three ready media assets per CPV campaign.
- Raw media can be pre-staged by the authorized request; an empty registry is not a global v3 blocker.

## Pitfalls

- Declaring “v3 complete” after only code/skill/config activation.
- Telling the user to wait for 17:00 without reading the live cron.
- Pointing the enabled job back to the v2 wrapper for convenience.
- Full account reconciliation inside every mutation bundle; keep it pre-hot-path and measure it.
- Sequential media preparation with no phase timing, making later slowdown diagnosis impossible.
- Calling a plan “zero side effects” when it intentionally refreshes a local reconciliation/audit file; distinguish external writes from local evidence writes.

## Validated CPV precedent (2026-08-21)

- Existing job ID was migrated in place to `creditoparaveiculo-v3-daily-create.sh`.
- Live plan reduced desired 3 to selected C14/C15 because USD 213 + USD 60 = USD 273 under the USD 300 cap.
- Six assets reconciled; live dry-run had no reservation, upload, campaign write or Drive move.
- 132 relevant tests, offline deferred-resume smoke, live scheduler CLI readback and REPORT-INFRA passed before enabling.
