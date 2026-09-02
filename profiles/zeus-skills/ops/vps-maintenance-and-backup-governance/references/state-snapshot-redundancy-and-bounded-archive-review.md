# State Snapshot Redundancy and Bounded Archive Review

Use this reference when old Hermes/profile state snapshots look redundant after an update but may contain unique session/cron history, may be referenced by immutable checksum evidence, or require large SQLite members from a compressed archive for comparison.

## Classification: newer is not automatically redundant

Classify each snapshot against **all** retained recovery sources, not only the newest directory:

1. **Exact duplicate** — every substantive file is byte-identical to a retained snapshot; only label/manifest metadata may differ. Eligible for an exact destructive manifest.
2. **Logically subsumed** — SQLite integrity passes and every meaningful primary-key row exists in at least one retained source (latest snapshot or validated full archive). Config/auth/state differences must also be preserved by a retained source.
3. **Unique historical state** — meaningful rows or files exist in the candidate but in neither retained source. Protect it, or disclose the unique classes/bytes and require an explicit owner override.
4. **Checksum-coupled evidence** — any file under the snapshot is named by an activation/profile SHA manifest. Treat the directory as protected even if its content is otherwise duplicated; deleting it would invalidate the evidence set.

Never classify from directory age, size, or label alone.

## Meaningful SQLite comparison

- Run `PRAGMA quick_check` and `PRAGMA foreign_key_check` read-only on every candidate DB.
- Compare candidate DBs to the latest retained snapshot and the validated full archive.
- For tables with primary keys, count candidate rows absent from retained sources by PK.
- Treat `sessions`, `messages`, routing, model usage, delivery obligations, system prompts, and cron executions as meaningful history.
- Keep FTS shadow/index tables separate: candidate-only FTS internals do not by themselves prove unique user history.
- For tables without primary keys, report row-count differences and fail closed rather than claiming set containment.
- If union coverage across retained sources cannot be proven, classify the snapshot as protected.

## Archive-member staging capacity gate

Before extracting large SQLite members from a compressed archive:

1. Read selected `TarInfo.size` values without extraction and sum the exact logical bytes.
2. Read free bytes on the intended staging filesystem with `statvfs`.
3. Require selected bytes plus a safety margin (at least 25%, and never less than 512 MiB) to fit.
4. Prefer hash-only streaming for files that do not need SQLite queries.
5. If DB extraction is required and `/run` is too small, use a secure disk-backed staging root outside Git. Freeze its exact cleanup manifest **before** extraction so residue removal already has an authorized, bounded path.
6. Never begin extraction into `/run` when the capacity gate is red. A partial tar extraction can fill tmpfs, make SQLite return `disk I/O error`, and endanger unrelated services.

If staging still fails, stop: prove original snapshots unchanged, inventory the exact temporary residue, and obtain the Critical Subset confirmation before deleting it. Do not conceal the residue or treat a reboot as cleanup.

## Reporting decision

Report separately:

- bytes safely removable now (exact duplicate/subsumed and not checksum-coupled);
- bytes protected by immutable update evidence;
- bytes containing unique historical state;
- bytes still unclassified because the retained-source union was not proven.

A user request to “reavaliar” authorizes read-only comparison, not deletion of snapshots or temporary extraction residue.
