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
3. Inventory targets and successful technical observations are not certifications of every business workflow. Validate semantic completion and required delivery using the workflow's own receipts. Preserve distinct report periods/slots; a later report is not evidence that an older missing slot was delivered.
4. A fresh progress log or a worker saying `Resolvido` is not completion. Check the active owner before accepting green telemetry, then require fresh target/readback evidence. Keep unsupported/ambiguous completion pending rather than manufacturing proof.
5. Busy resource waiting must not increment business failure budgets. Preserve first position and blockers across repeated ingestion. Repeated alerts must not reset due times, retry budgets or leases.
6. Keep `waiting_human`, `blocked_decision` and technical diagnosis gates intact when PC1 is busy or notice delivery fails. Never demote a human/critical gate to an unrestricted retry. Preserve `verifying` as read-only completion checking across resource waits, and never shorten an already-persisted cooldown/backoff to the busy polling interval. Preserve the missing-stage observation when a wait has no new observation.
7. Persist a newly discovered PC1 dependency after the first real diagnosis; subsequent busy checks must use the lease without repeatedly invoking an agent just to rediscover known contention.
8. Authentication probes are read-only. Only a real positive read of the same target may return `AUTH_READY:` to permit the next already-authorized retry. Missing evidence keeps the human gate. Do not bypass login/2FA.
9. Timeout/no-final-response requires reconciliation of possible effects. Kill only the isolated child group owned by that worker; never a gateway or another session. Persist child PID plus `/proc` start ticks so parent loss/PID reuse cannot authorize a duplicate writer.
10. Five consecutive dispatcher failures stop blind dispatch and remain visible to the watchdog; per-request diagnosis also stays open. Diagnose and correct the exact cause within authority before clearing the guard. Natural producer recovery can still supply verified evidence; stopping attempts is not cancellation.
11. Historical records outside the active inventory remain held for scope review, without mass replay or one unsolicited notice per ancient record. Synchronize validated closure back to the legacy ledger so the next tick cannot recreate the incident.

## Delivery and domain adapters

Use `mgs_alert_transport.post_verified`. Persist accepted message IDs before GET; a failed verification retries GET of that ID, not the business operation or a second POST. Bound nonces to Discord's accepted length and explicitly disable unintended mentions.

DTR daily audit uses `scripts/mgs_dtr_continuity.py`:

- Cache only complete per-user collections, scoped by target list/date/account limit. Do not reuse partial login/account results or expired checkpoints.
- A restarted collector reuses valid completed users and collects only missing users. Persist raw scope-complete data before publication.
- Validate unique user coverage, successful logins, raw page totals and zero nested collection errors before publication.
- Freeze the original report snapshot/payload in a per-day outbox. Reuse the canonical renderer and issue-key state; resume only missing delivery parts and GET-verify every accepted ID.
- `--no-post` proves collection only. It cannot advance the published state or close a missing-report incident.

SHEIN continues to use its canonical per-date/per-slot receipts and nonce rules in `references/shein-daily-and-intraday-reports.md`; this common layer does not change cutoffs, strategy, UI/API policy or report slots.

## Acceptance and operation

1. Run the affected queue/supervisor/PC1 ingress, worker lifecycle, integration, monitor, resolver and DTR tests in isolated temporary state. Use the installed SB venv for tests importing Playwright, with `PYTHONPATH` including scripts and tests. Set a fixture `CRON_STALE_STATE` to avoid contaminating root-log fixtures with live native job failures; never weaken production probes to make tests pass.
2. Exercise OS-process enqueue/claim races, reopen/persistence, busy/release/resume, timeout/backoff, stale lease, PID fingerprint, human/critical gate preservation, notice failure and accepted-POST/failed-GET behavior.
3. Register with the existing resolver's `--init` only when necessary. It records current observations/queue and does not execute work or move the Discord cursor. Registration alone is not an active-consumer acceptance test.
4. Observe subsequent **natural scheduled ticks** with different dispatcher PIDs, the exact durable request, state transitions and target receipt. Do not create a throwaway production request to prove queue mutation; recover an explicitly authorized real incident or use isolated fixtures.
5. Compare the root crontab and native immutable schedules before/after; inventory coverage and business success are separate claims. Do not execute sensitive jobs simply to test the generic layer.
6. Record exact deployment/test/receipt evidence in infra inventory, audit and the initiative checkpoint; send one canonical REPORT-INFRA and GET-verify that embed. Keep remaining resource/human/critical work open with owner and next executable step.

## Recovery/rollback cautions

Do not restore a legacy entrypoint and strand records marked `continuity_owned`. Pause dispatch deliberately if needed, preserve the database and accepted IDs, reconcile live child owners, repair/revalidate the same consumer, and resume the same requests. Do not delete queue/evidence, steal PC1, alter credentials, restart gateways or re-run completed business stages as a rollback shortcut.
