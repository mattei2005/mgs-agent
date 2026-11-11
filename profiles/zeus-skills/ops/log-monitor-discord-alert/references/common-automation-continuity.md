# Common automation continuity — deployed MGS recovery

## Purpose and authority

Policy: `/root/mgs-agent/context/automation-recovery-policy.md`, Rodolfo `1569191908020981801`; implementation authorization `1569193434189668453`, thread `1569185140502954077`. This reference owns the reusable procedure, not business authority or new permissions.

## Runtime and admission

- `scripts/mgs_automation_continuity.py`: SQLite queue `/root/.hermes/shared/automation-continuity/queue.sqlite3`, dedupe, events, leases, due times, FIFO PC1 admission and bounded exponential backoff with jitter.
- `scripts/mgs_automation_supervisor.py`: inventories root/system cron, native Zeus/Atena/Ares jobs and systemd timers; observes producer/receipt health; reconciles owners, handles safe recovery and delivery.
- `scripts/alerts-infra-failed-alert-resolver.py` entrypoint dispatches the common supervisor. Reuse its existing five-minute root cron and outer flock; do not add a second dispatcher or change business schedules.
- `scripts/mgs-pc1-computer-use-lock.py` persists busy requests before returning `lock_held`, exposes `continuity_queued` and `continuity_key`, and denies a newcomer ahead of an eligible older PC1 request. An unknown/persistence failure is not an empty healthy queue.
- `scripts/mgs_continuity_health.py`, called by the existing stale monitor, independently checks the consumer heartbeat and diagnosis backlog. A file existing or an `enabled` flag is not sufficient runtime proof.

Native cron correlation requires a unique exact profile/original-thread match. Generic PC1 requests retain profile, session and source thread; the worker must recover the actual original command and current authority before business writes. Never guess credentials, original scope or a replacement identity.

## Safety and state rules

1. Never replay an arbitrary stored shell command. Reconcile the same request using its canonical runner, current authority, checkpoint and receipts.
2. Native contract hashes freeze prompt/script/origin/schedule/provider/delivery and repeat limit, excluding mutable run counters. A changed contract must preserve the original metadata and block automatic replay; a paused/completed/missing job is not re-enabled.
3. Inventory targets and successful technical observations are not certifications of every business workflow. Validate semantic completion and required delivery using the workflow's own receipts. Preserve distinct report periods/slots; a later report is not evidence that an older missing slot was delivered. Keep an explicit `blocked_decision` gate closed until an authorized transition; neither a later green observation nor another slot's success clears that gate.
4. A fresh progress log or a worker saying `Resolvido` is not completion. Check the active owner before accepting green telemetry, then require fresh target/readback evidence. Keep unsupported/ambiguous completion pending rather than manufacturing proof.
5. Busy resource waiting must not increment business failure budgets. Preserve first position and blockers across repeated ingestion. Repeated alerts must not reset due times, retry budgets or leases.
6. Keep `waiting_human`, `blocked_decision` and technical diagnosis gates intact when PC1 is busy or notice delivery fails. Never demote a human/critical gate to an unrestricted retry. Preserve `verifying` as read-only completion checking across resource waits, and never shorten an already-persisted cooldown/backoff to the busy polling interval. Preserve the missing-stage observation when a wait has no new observation.
7. Persist a newly discovered PC1 dependency after the first real diagnosis; subsequent busy checks must use the lease without repeatedly invoking an agent just to rediscover known contention.
8. Authentication probes are read-only. Only a real positive read of the same target may return `AUTH_READY:` to permit the next already-authorized retry. Missing evidence keeps the human gate. Do not bypass login/2FA.
9. Timeout/no-final-response requires reconciliation of possible effects. Kill only the isolated child group owned by that worker; never a gateway or another session. Persist child PID plus `/proc` start ticks so parent loss/PID reuse cannot authorize a duplicate writer. Pass the actual wall-time limit to the worker and reserve time for a durable checkpoint/final response; split UI work into bounded batches while preserving the entire approved target set. A saved partial batch is not full business recovery; validate the next resumed stage before claiming the timeout recovered.
10. Five consecutive dispatcher failures stop blind dispatch and remain visible to the watchdog; per-request diagnosis also stays open. Diagnose and correct the exact cause within authority before clearing the guard. Natural producer recovery can still supply verified evidence; stopping attempts is not cancellation.
11. Historical records outside the active inventory remain held for scope review, without mass replay or one unsolicited notice per ancient record. Synchronize validated closure back to the legacy ledger so the next tick cannot recreate the incident.

## Owner cancellation of one historical delivery

1. Resolve the exact existing request, reporting period/slot, source decision and current owner. Read the queue row and its initiative checkpoint; inspect the legacy alert entry only when it references that request. A producer-wide source key is not a period identifier: preserve current/future slots and unrelated technical recovery.
2. Check cancellation semantics before choosing a terminal state. Inspect `Queue.open()`, `enqueue()`, the partial unique index and the supervisor's legacy ingestion/closure paths. `cancelled_owner` being excluded from the open set does not prove suppression: an unresolved legacy alert or unchanged producer observation can enqueue a fresh row. Never use `completed_validated` to disguise a waived delivery as successful delivery.
3. Check writer ownership before editing a ledger. A held `dispatcher.lock` may protect an unrelated long-running worker; do not kill it or rewrite its JSON snapshot concurrently, because its later save can overwrite the decision. Use a supported serialized transition when available. For a request already held in `blocked_decision`, a conditional SQLite transaction can record the scoped owner decision and event while preserving the non-dispatchable gate; require the expected request identity/state and no owner, then read back. Treat this as an interim anti-replay hold, not proof of terminal cancellation across all consumers. Do not reopen or claim the row merely to acknowledge cancellation.
4. Reconcile terminal closure only when the legacy re-ingestion path and producer observation cannot recreate the same historical delivery. Keep the decision scoped to its original period; never suppress all subsequent producer failures. If runtime support is missing, preserve the safe gate and describe the remaining bookkeeping accurately rather than claiming a new cancellation adapter was deployed.
5. Update the initiative checkpoint so it no longer waits for the waived authorization, preserving independent work. Record the decision source and exact scope in evidence/audit. Verify that the request cannot dispatch, the checkpoint no longer asks for that approval, and recurring configuration was not changed. A queue readback proves the persisted gate; it does not prove a later natural tick or unrelated report recovery.

## Delivery and domain adapters

Use `mgs_alert_transport.post_verified`. Persist accepted message IDs before GET; a failed verification retries GET of that ID, not the business operation or a second POST. Bound nonces to Discord's accepted length and explicitly disable unintended mentions.

A financial recovery whose business writes are already verified but whose source-thread report is missing needs a delivery-only domain adapter, not another agent recollection. `scripts/mgs_finance_continuity.py` handles the frozen Digital Trust incident only: exact original job/hash and slot gates, corporate-SA live parity with the validated workbook, frozen outbox, accepted ID persisted before GET, and a read-only supervisor observation. A later native slot cannot be certified by this older receipt. An accepted-but-unverified POST resumes GET of its ID; an ambiguous POST without an ID remains pending unless the exact nonce/content can be reconciled. Never turn repeated `delivery_pending` handoffs into another business writer or close from worker wording alone.

For a human/decision gate, preserve the exact final question and required CEO push in a bounded embed; do not cut the tail of a long diagnostic into a content-only message. Freeze the entire notice payload before POST so a changed probe response cannot break GET reconciliation. Upgrade an already-accepted legacy notice by PATCH of its exact ID plus GET, never by a replacement POST.

DTR daily audit uses `scripts/mgs_dtr_continuity.py`:

- Cache only complete per-user collections, scoped by target list/date/account limit. Do not reuse partial login/account results or expired checkpoints.
- A restarted collector reuses valid completed users and collects only missing users. Persist raw scope-complete data before publication.
- Validate unique user coverage, successful logins, raw page totals and zero nested collection errors before publication.
- Freeze the original report snapshot/payload in a per-day outbox. Reuse the canonical renderer and issue-key state; resume only missing delivery parts and GET-verify every accepted ID.
- `--no-post` proves collection only. It cannot advance the published state or close a missing-report incident.

SHEIN continues to use its canonical per-date/per-slot receipts and nonce rules in `references/shein-daily-and-intraday-reports.md`; this common layer does not change cutoffs, strategy, UI/API policy or report slots.

For a failed SHEIN D-1 wrapper followed by canonical delivery recovery, reconcile the observer instead of replaying the report or rewriting `last-cron-result.json`. `mgs_report_scheduler_health.daily_recovery_receipt` resolves the failed wrapper's New York delivery date to its exact D-1 directory and requires a later completion, matching request/account/thread coverage, per-account delivery journals, unique accepted IDs, GET_VERIFIED intents and frozen content hashes. Other periods, newer failures/logs, partial or mismatched journals remain non-green. Validate the deployed monitor and the supervisor's observation parser, preserve the original failure evidence, and leave the actual queue transition to its active supervisor. A green local predicate and live Discord GET proof are separate checks; neither authorizes touching a concurrent intraday writer or its shared lock.

## Acceptance and operation

1. Run the affected queue/supervisor/PC1 ingress, worker lifecycle, integration, monitor, resolver and DTR tests in isolated temporary state. Use the installed SB venv for tests importing Playwright, with `PYTHONPATH` including scripts and tests. Set a fixture `CRON_STALE_STATE` to avoid contaminating root-log fixtures with live native job failures; never weaken production probes to make tests pass.
2. Exercise OS-process enqueue/claim races, reopen/persistence, busy/release/resume, timeout/backoff, stale lease, PID fingerprint, human/critical gate preservation, notice failure and accepted-POST/failed-GET behavior.
3. Register with the existing resolver's `--init` only when necessary. It records current observations/queue and does not execute work or move the Discord cursor. Registration alone is not an active-consumer acceptance test.
4. Observe subsequent **natural scheduled ticks** with different dispatcher PIDs, the exact durable request, state transitions and target receipt. Do not create a throwaway production request to prove queue mutation; recover an explicitly authorized real incident or use isolated fixtures.
5. Compare the root crontab and native immutable schedules before/after; inventory coverage and business success are separate claims. Do not execute sensitive jobs simply to test the generic layer.
6. Record exact deployment/test/receipt evidence in infra inventory, audit and the initiative checkpoint; send one canonical REPORT-INFRA and GET-verify that embed. Keep remaining resource/human/critical work open with owner and next executable step.
7. Parse the actual top-level inventory arrays before editing them: nested artifact snapshots may also contain a `scripts` label, so the first textual occurrence is not the root collection. Filter record types, select the exact path/ID, require one match, and use uniquely anchored item edits rather than rewriting an old whole-file snapshot. After a wrapper failure, inspect landed files/records and resume only the missing write; do not recreate the report or resend its embed.

## Recovery/rollback cautions

Do not restore a legacy entrypoint and strand records marked `continuity_owned`. Pause dispatch deliberately if needed, preserve the database and accepted IDs, reconcile live child owners, repair/revalidate the same consumer, and resume the same requests. Do not delete queue/evidence, steal PC1, alter credentials, restart gateways or re-run completed business stages as a rollback shortcut.
