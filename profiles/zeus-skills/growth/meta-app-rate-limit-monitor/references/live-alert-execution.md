# Live alert execution and contention recovery

Use for requested live deliveries across generic app routes and the dedicated DTR route. Keep credential gates, pause policy and delivery-only reporting in SKILL.md; use the native renderers rather than constructing replacement cards.

## 1. Prepare the request before launching writers

1. Freeze the current registry cohort, exact destination IDs, pause sets and latest message ID in each channel. Give the request a credential-free receipt directory and bind it to the actual source message and thread.
2. Inspect both canonical locks before starting. Resolve each runner's interpreter from its wrapper, including `PYTHON_BIN` or the native override for the dedicated runner; do not assume the generic Python process is the dedicated execution environment.
3. Estimate lock wait, full scan and enrichment separately from recent completed runs and the live target population. The dedicated DTR body iterates grouped credentials sequentially; its cron interval is not a runtime estimate. When that total may exceed the foreground ceiling, start one silent tracked process with bounded waiting from the outset and consume it before closing the task.
4. For generic fleet delivery, leave `MGS_META_APP_ROLE_ITEMS` unset, set `MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1`, and pass the canonical state and pause paths. For the dedicated route, set `MGS_B013_DTR_FORCE_LIVE_ALERT=1` and its canonical state path. Keep snapshot mode disabled and preserve all source reads and native reconciliation.

## 2. Resolve contention without replay

1. Preserve the scheduled writer. Inspect its owner, elapsed time, current job claim and persisted target-specific timestamps before declaring a stale lock or failed schedule.
2. If the PID from `/proc/locks` is absent from the visible process namespace, identify visible holders by matching the lock file's `st_dev` and `st_ino` against `/proc/<pid>/fd/*`; then inspect the matching visible PIDs and parents with `ps`. An unsuccessful direct PID lookup does not prove the lock is stale. An open descriptor alone does not prove ownership: distinguish the established writer from a waiting requester using its job claim, elapsed time and stage receipts.
3. Distinguish **waiting for the lock**, **body entered**, **fresh receipt persisted**, and **delivery read back**. Write a before-run stage receipt only after acquiring the lock. If the wait expires before entry, confirm that absence and inspect channel messages before another attempt; a missing final receipt alone does not establish zero side effects.
4. After zero side effects are established, resume only the undelivered runner with one bounded waiting process under its existing canonical lock. Acquire that lock once and execute the unchanged embedded body with its native interpreter; never invoke a self-locking wrapper while holding the same lock.
5. Treat a process-wait timeout as an observation window ending, not as operation failure. Continue observing the same process while it runs; do not launch a replacement writer. Preserve and verify the already-delivered generic routes while the dedicated route waits or scans.
6. If contention materially delays completion, tell Rodolfo briefly which destinations are complete and which route is still waiting or collecting. Finish with the actual result, not a promise of an untracked retry.

## 3. Verify each requested family independently

1. Require a fresh run receipt and an actual process exit. For generic routes, compare the completed processed-item set against the frozen registry cohort. For the dedicated route, use its own fresh account/link summary, not generic app roles.
2. Read messages newer than each saved channel baseline, paginate if necessary, then GET the exact native card object. Match the current app generation and requested-live description, and isolate that card's continuations from later scheduled families.
3. Parse section headings across every continuation code block. Count six-column data rows rather than messages or repeated headers: a later chunk may contain no header. Validate money cells and compare current-user counts with that run's operational roles or dedicated `linked` count. Use the native pending-section equivalent for each runner.
4. Require one complete requested logical family per destination. Do not hard-code three physical messages; large account tables split into additional continuations. Aggregate and deduplicate counts in code before claiming complete coverage.
5. Repair validator-only mistakes without resending landed alerts. If only one route remains undelivered, recover only that route. Preserve completed destinations, pauses and the sole writer.

## 4. Close with request-sized reporting

Persist final delivery receipts and clear pending execution stages. Report verified delivered/requested channels and freshness in one or two sentences; mention a recovered delay or material caveat without turning an alert-only request into a fleet audit. Keep detailed counts, runtime traces and proof paths in the receipt rather than the executive reply.
