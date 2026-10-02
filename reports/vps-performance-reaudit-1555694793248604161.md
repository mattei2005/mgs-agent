# Performance re-audit — 2026-10-02

Authority: Rodolfo Mattei, message `1555694793248604161`, thread `1555578276708356108`.
Scope: read-only revalidation of the prior VPS/Zeus/Atena/Ares performance audit and proposed improvements. No authorization inferred for rollout, installs, scheduler changes, deletion, model changes or gateway restarts.
Evidence directory: `/root/.hermes/profiles/zeus/cache/scratch/performance-reaudit-1555694793248604161/`.

## Executive verdict

The original diagnosis is supported: severe concurrent CPU pressure occurred, while current memory/disk capacity does not justify buying RAM or panels. The implemented browser budget, 90% hygiene threshold and Zeus 4 GiB checkpoint cap remain present and pass repeated tests. The previous audit was not a universal browser-governance proof or a production speedup benchmark. Further improvement remains available, particularly in scheduled direct-Playwright consumers, model-call round trips, context-window validation and recurrent SB authentication recovery.

## Revalidated findings

- Active launcher resolves to `/root/.hermes/hermes-agent-port-main-ad2d4822-mgs/.venv/bin/hermes`; real gateway executable/cwd evidence agrees. Runtime SHA `c559e65bcf43f9f41cbc2fa1d6ef8d47643dbc6e`; gateway-state Zeus agrees. All three gateways remain active/running, PIDs Zeus 2436781, Atena 2429908, Ares 2429393, NRestarts 0. No restart in this audit.
- `sar` at 03:30:03 Eastern: 99.63% busy, load1 30.47 on four CPUs. 03:10 and 03:20 were also >98% busy. This supports sustained contention, not merely one instantaneous 100% sample. The historical attribution to Chrome/overlapping DTR uses the original evidence; this re-audit does not invent per-PID accounting for exited processes.
- Final host snapshot 17:58:06 Eastern: CPU busy 13.1%, load1 0.939, available memory 13281.6 MiB, available root disk 76.25 GiB. Root filesystem 61% used and 4% inode usage; boot/EFI have ample headroom. PSI memory 0 in the initial window; current I/O wait and swap-in/out samples do not support a sustained memory/disk bottleneck. No failed systemd units or kernel warning/OOM entries in the checked current-day window.
- System services cron, Monarx, QEMU and actual `mgs-autocommit.service` are healthy. A probe initially queried the nonexistent spelling `mgs-auto-commit`; actual producer readback corrected that before any incident claim. Auto-versioning origin cannot be inferred from an unrelated service name.
- All three profile configs exactly equal their versioned mirrors. All keep compression.threshold 0.90. Checkpoint caps Zeus 4096 MiB, Atena/Ares 1024 MiB; enablement, 50 snapshots and 7-day retention preserved. Final stores: Zeus 1341.69 MiB, Atena 1.07 MiB, Ares 634.1 MiB. No new post-activation size-cap warnings identified. No pruning/deletion invoked.
- Shared browser settings remain slots=3, batch_slots=2, local_workers=1. The shared module/config shell hashes match the original verified change manifest; supplemental reverse-apply check passed.
- Repeated the exact original focused test suite against the current runtime in an isolated test home: **220 passed, zero failed**, 37.32 seconds. Original JUnit confirms the original 220 claim. The original guard receipt confirms **601 passed**, zero failed; those 601 are historical evidence, not a newly rerun suite.
- New real rendered local browser test: 5/5 readbacks PASS, peak batch leases 2 with settings 3/2, no external requests, protected sessions untouched. Isolated lock namespace avoids consuming live production slots. This proves the current admission behavior in that fixture, not real DTR throughput.
- SQLite quick_check is OK for all three profile state databases; journal_mode WAL and session/message indexes exist. No evidence presently justifies VACUUM, reset or transcript deletion as a speed repair.
- Provider MCP metrics query through the native trust/SDK path succeeded. Provider historical metrics complement guest metrics; they are not the same instantaneous observation.

## Corrections and limits on the earlier narrative

1. **Browser admission is opt-in, not universal.** Managed browser_exec is admitted per call, selected standalone DTR workflows per workflow. A retained browser can exist between admitted actions. A process count is not a workflow count: Chrome renderers/GPU/utility children must not be counted as independent browsers. The live controller sample contained one short-lived controller, not a renewed population of 50 abandoned controllers; no protected session closure is warranted.
2. **No production speedup percentage has been established.** In the same-day `sar` subset after 14:40, 19 samples had maximum busy 79.57%, with zero >90%; five load1 samples exceeded 4. The before/after workload, models, duration and concurrent changes differ, so these observations are not causal proof. The synthetic baseline previously completed its entire batch faster despite worse per-task contention.
3. **The large historical model context is route-specific.** Successful current-day log maxima: gpt-5.6-sol-900k 780747 tokens, gpt-6-astra-900k 406503, gpt-6.1-sol 283887. They do not establish a 1.05M gpt-6.1-sol window. Atena/Ares pin model.context_length to 1050000; their smoke logs warn that local metadata advertises 272000. The warning reads local endpoint/cache/catalog sources, not an actual provider capacity measurement; do not automatically treat 272000 as the true maximum or reduce the pin without route validation. The 90% threshold fix and context-capacity validation are distinct gates.
4. **Latency sums are aggregate, not elapsed wall time.** Deduplicated Zeus API logs after 14:33 contained 253 calls at that observation, median 24.7s, p95 121.8s, median input 122517 tokens, cache fraction 96.42%. Parallel calls overlap; 155.15 aggregate minutes are not 155.15 minutes of one user's wait. The earlier subset includes different models and tasks and cannot be used for a direct speed comparison. Boundary-aggregated SQLite usage rows are explicitly marked and not treated as exact-window token telemetry.
5. The old report `vps-performance-1555578276708356108.md` describes the implementation/pre-restart stage. Its pending wording is historical, superseded for active state by the joint activation receipt and current readbacks. This re-audit is the current assessment; it does not downgrade the earlier activated_validated checkpoint.

## Additional improvement candidates, in order

### 1. Extend the existing budget to active direct-browser consumers

Confirmed scheduled consumers that launch Playwright without the shared admission module:
- `dtr-sb-page-health-sync.py` through its scheduled shell wrapper;
- `sync-sb-sms-revenue-daily.py` through its scheduled shell wrapper;
- `sync-sb-messenger-revenue-sheet.py`;
- `monitor-sb-messenger-token-invalid.py`.

Static broader script scan also identifies other direct consumers; not every archived/manual/test script is active. Independent job flock locks do not provide a shared resource budget across different jobs. Propose wrapper-level shared leases and bounded wait telemetry without changing cadence, dataset, credentials or business behavior. Preserve the batch/interactive reservation and avoid nested acquisition. Required rollout gates: per-consumer tests, one canary, exact consumer readback, resource/queue observation and rollback. Expected benefit is less overlap; queueing may lengthen some batch jobs. Do not claim these four jobs caused the original peak solely because they are ungoverned.

### 2. Reduce avoidable model round trips and verbose context

Use the deterministic status runner and consolidate independent lookups; route large references progressively and return compact counters instead of schemas/full logs. Current median model latency means reducing unnecessary calls has leverage even when host CPU is idle. Preserve the most capable approved model, the prompt cache, safety gates and task semantics. Do not replace authorizations or source validation with an overly broad batch. Native disabled generic-skill and missing-tool errors appeared in recent logs; these require real runtime/intent reconciliation, not a blind package install or policy change during this audit.

### 3. Validate each model/provider context route

Reconcile effective provider capacity, current endpoint metadata, real successful request size and the explicit pins. Preserve the approved 90% compacting percentage; do not confuse changing the context window with moving the percentage. No 1M synthetic/provider stress request was sent merely to test the limit, and no context pin was changed.

### 4. Make SB authentication recovery durable

During the audit, the transition consumer emitted another /company HTTP 401 after three bounded retries. A locked read-only exact-consumer recovery attempt also failed. No blind apply/retry loop or credential rotation followed.

A concurrent authorized alert-resolver operation renewed the canonical session with the **unchanged existing credential**, then verified /company 200, exact dry-run/apply rc=0, 54 publishers, 73 active users, 2886 scoped rows, 373 monitored rows, zero Discord transition posts, exact independent Sheet/state keys and watchdog OK. Reconciled audit events `cron_alert_remediated` at 21:52:16Z and `cron_alert_remediation_report_validated` at 21:53:01Z, REPORT-INFRA `1555699074764898397`. Current consumer state last_check 17:51:09 Eastern; final watchdog dry-run problems=0. This is a recovered incident, not a current blocker, and is not a foreground correction claimed by this audit.

This repeats an earlier current-day authentication failure, so permanent recurrence prevention is not yet proven. Propose bounded canonical session refresh after a confirmed authentication rejection, with exclusive session locking, /company 200 before state save, exact-consumer re-run, no credential change and existing alert/outbox semantics. Preserve all current business scopes/cadences. Recovery may reduce missed cycles and wasted retries; it is not a hardware speedup.

### 5. Maintenance remains separate

Cached local APT simulation showed 12 upgrade transactions plus kept/deferred packages; needrestart reports systemd-logind as a remaining service item, while running/expected kernel agree and no reboot marker exists. No APT index refresh/install was performed, so this is not a claim of the newest available package graph or of a fully updated VPS. No evidence links those updates to the measured latency. Keep standard maintenance separate from the performance optimization decision.

## Scope, scheduler coverage and artifacts

Collected root/system cron sources (61 non-comment entries), all three operational Hermes job registries (37 entries, active/disabled/once separated), systemd timers and the active browser-consumer chains above. Root is the only user crontab. Final cron-log watchdog independently assessed its own 48 rows with zero problems; 48 is its coverage predicate, not every scheduler/job on the host. Scheduler inventory does not authorize rescheduling or claim all possible remote application schedulers were benchmarked.

Foreground changes in this re-audit: scratch collector/test/evidence artifacts, this report, its own initiative checkpoint/inventory/audit entry, and three reusable rules in the Zeus browser-performance skill (transitive coverage, deduplicated/comparable latency, context-warning interpretation), synchronized with byte/hash-equal readback. No production script/config, credential, budget, scheduler, model, retention or gateway changed by the foreground audit. The concurrent SB recovery is separately attributed above.

Tool/probe failures were corrected or bounded: wrong checkpoint subcommand corrected to checkpoint-upsert; sar header mistaken for data fixed and rerun; old guessed documentation URL returned 404, then official llms.txt located the canonical page; nonexistent Python watchdog filename resolved to the actual .sh; unavailable generic Hermes skill was read on disk without enabling it. None of these failed probes was counted as a successful acceptance gate.

Recommendation: prioritize the shared budget coverage, fewer model round trips and reliable SB session recovery before considering 8 vCPU. More vCPU can help demonstrated residual browser CPU pressure but cannot proportionally accelerate remote model generation. No panel, Docker, extra RAM, forced swap clearing or incidental cleanup is justified by this audit.
