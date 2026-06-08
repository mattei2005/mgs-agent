# Drive bulk upload controller pattern

Use this when a large Drive clean-copy/import job is already approved and may run for many minutes or hours.

## Problem this prevents

Bulk upload jobs can produce confusing background-process alerts, duplicate starts, or repeated `UPLOADED` rows when an agent launches a resume while an older executor is still active. The correct response is not to keep explaining each transient alert to Rodolfo; the agent should take operational control, prevent parallel execution, and report only meaningful status/final results.

## Pattern

1. Before starting or resuming, check for an active executor matching the exact script + queue path.
2. If one exists, do **not** start another uploader. Start only a lightweight watcher/controller, or wait for the existing process.
3. The controller should:
   - wait while the existing executor is active;
   - summarize progress from the CSV report using unique successful `queue_id`, not raw `UPLOADED` row count;
   - resume the queue only when no executor is running;
   - stop after an attempt/no-progress limit;
   - preserve RAW folders and never delete duplicates automatically.
4. When reporting progress, use:
   - total queue rows;
   - auto-processable rows;
   - manual-review rows;
   - unique uploaded queue IDs;
   - remaining auto rows;
   - real error count.
5. Do not treat process `exit 143` from a deliberately killed duplicate as a job failure. Report it only if needed as “duplicate process killed intentionally.”
6. If brief parallel overlap happened, consolidate final impact before any deletion: identify duplicate destination files first, then ask before deleting anything.

## Reporting style for Rodolfo

If Rodolfo gives full autonomy or shows confusion/frustration, reduce intermediate technical chatter. Say that you are handling it, state the guardrails, and keep working. Avoid repeated explanations of shell/PTY noise unless it changes the operational state.

## Minimal controller behavior

```text
while executor is active:
  sleep and summarize from report
if remaining_auto == 0:
  finish
else:
  resume queue once no executor is active
if no progress after repeated attempts:
  stop and report blocker
```
