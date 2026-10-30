# SHEIN queue — inert historical human reviews and dry ownership handoff

## Diagnose before touching scheduling

1. Reconcile the same human request, live channel authority, account partition, immutable input, durable queue job and runner state. Read the historical review and every later human message with complete pagination; a new independent order is not approval/cancellation of an old material divergence.
2. Separate an idle process lock from the persisted Engine writer lease. Confirm `COMPLETE_PAUSED` Engine result, exact campaign IDs, completed checkpoint with `manual_reconciliation_required=false`, released `COMPLETE` lease with `blocks_readers=false`, and live historical campaigns PAUSED. Missing/ambiguous facts remain dependencies.
3. Verify exact asset coverage and reservations, including lineage, canonical filename, checksums/pixel identity and account media IDs. Distinct filenames alone do not prove distinct media. Never release a reservation, change a manifest, forge a terminal phase or accept a targeting difference to unblock scheduling.

## Central representation

- `ares_campaign_v3.shein_decision_wait` represents `WAITING_HUMAN_DECISION` separately under `state/shein-campaigns/queue/decision-waits/<request>.json`. It is scheduling evidence, not human authorization, QA, cancellation or campaign completion.
- The descriptor pins SHA256 of the original, unmodified runner state and completed Engine checkpoint, exact IDs/account, the Ares review question and unanswered material-difference classification, readback evidence and maintenance provenance.
- The central queue omits only account-wide serialization for that evidenced idle wait when the incoming explicit media selection is complete and disjoint. Reservation conflicts remain independent blockers. An active/ambiguous lease, held account/lease-update lock, shared media, partial QA/activation, changed evidence or unprovable selection retains the dependency, fail closed. The existing runner account lock and Engine writer lease remain mandatory at execution. A lease owned by the **same exact resumable incoming request** may continue its missing-only recovery when its persisted request/phase match; never treat that as a foreign writer and deadlock it behind the historical review. A held process lock, missing/mismatched recovery state or foreign/unknown lease still blocks; no lease is released or rewritten.
- Any decision-wait record prevents automatic historical queue execution, including stale records. Future human review resolution must use the existing approved central review/QA route; never delete a marker to simulate approval or activate historical objects by inference.

## Contain a live worker before installation

- Coordinate explicitly with the owning Ares card before changing a dependency predicate. Verify the worker has no child execution and the job has not begun; stop only the request-queue service, not a gateway. Back up source, original input, historical state and queued job.
- Install/test under a durable job `maintenance_hold`. Restart the queue service only after the hold is installed and read back. Verify natural heartbeats with `attempts` unchanged; service active alone does not prove the hold works.
- `tick` reloads the durable hold/owner and serializes dispatch with a separate `.dispatch.lock`, so a stale worker snapshot cannot overwrite or execute the handoff. Foreground handoff and worker dispatch use that same lock.

## Read-only inspection and Ares-only takeover

From `/root/mgs-agent`, with the normal `PYTHONPATH=scripts`:

- Inspect only: `python3 -m ares_campaign_v3.shein_request_queue --inspect ORIGINAL_INPUT`. This reports dependencies and zero writes/uploads/reservations; it is NOT media readiness or a live campaign plan.
- Only the actual owning Ares profile may run `python3 -m ares_campaign_v3.shein_request_queue --take-foreground ORIGINAL_INPUT`. Never impersonate Ares by changing Zeus's profile environment. It rechecks live authority, exact queued original input, dependencies and dispatch lock, then changes only scheduler ownership to `FOREGROUND_OWNED`; it performs no provider mutation.
- A foreground-owned job is never auto-executed or auto-notified by the worker. After the exact terminal QA/readback passes, the worker may only close its scheduling record as `FOREGROUND_COMPLETE`, with delivery still owned by Ares. Ares remains sole executor and delivery owner using the same central `prepare-media -> request-ready -> campaign --dry-run -> campaign --confirm-execute` flow. Do not create a second writer, new request, new SLA clock or ad hoc manifest. Normal reservations, QA, billing/credential/critical gates and account locks remain unchanged.
- Do not restore a pre-maintenance queued-job backup after Ares takes ownership or execution starts. Reconcile current effects first. Keep the hold during rollback; restore code without replaying jobs or rewriting historical state. Removing files/records remains subject to the normal destructive-operation gate.

## Required validation

Exercise synthetic negatives for active state/lease, held account and lease locks, shared lineage/checksum/media identity, missing/changed descriptor, incomplete historical media, partial QA/activation, unknown phase/lease and conflicting channel. Prove the positive disjoint-media idle-review case without mutating input/state/inventory. Exercise stale-worker hold, dispatch/handoff contention, wrong-profile takeover, immutable/running-job rejection and no automatic historical execution. Read back installed source hashes, original-state/input hashes, durable hold, service heartbeat and exact REPORT-INFRA receipt. Persist audit/inventory/checkpoint; report through the coordinating cards, not an operational-thread fallback.
