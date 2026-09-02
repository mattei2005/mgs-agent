# State Snapshot Redundancy and Bounded Archive Review

Use this reference when old Hermes/profile state snapshots look redundant after an update but may contain unique session/cron history, may be referenced by immutable checksum evidence, or require large SQLite members from a compressed archive for comparison.

## Classification: newer is not automatically redundant

Classify each snapshot against **all** retained recovery sources, not only the newest directory:

1. **Exact duplicate** — every substantive file is byte-identical to a retained snapshot; only label/manifest metadata may differ. Eligible for an exact destructive manifest.
2. **Logically subsumed** — SQLite integrity passes and every meaningful primary-key row exists in at least one retained source (latest snapshot or validated full archive). Config/auth/state differences must also be preserved by a retained source.
3. **Unique historical state** — meaningful rows or files exist in the candidate but in neither retained source. Protect it, or disclose the unique classes/bytes and require an explicit owner override.
4. **Checksum-coupled evidence** — any file under the snapshot is named by an activation/profile SHA manifest. Treat the directory as protected even if its content is otherwise duplicated; deleting it would invalidate the evidence set.

Never classify from directory age, size, or label alone.

### Directional proof when the retained snapshot is a superset

Deletion safety is directional: the candidate may be fully subsumed even when the retained snapshot contains additional files.

1. Enumerate both trees with a hidden-file-aware filesystem walk; shell globs such as `*` can omit `.env` and make counts misleading.
2. Exclude only known candidate-local label/manifest metadata from the payload comparison.
3. Require every substantive candidate file to exist at the same relative path in at least one retained recovery source with the same externally computed SHA-256.
4. A retained-only file does not invalidate subsumption. In particular, extra `state.db-shm` or `state.db-wal` sidecars in the retained snapshot are acceptable when the candidate has no unmatched substantive file and the retained recovery set remains intact.
5. Any candidate-only substantive file, hash mismatch, missing retained path, or ambiguous file role fails closed and keeps the candidate protected.
6. Report the comparison asymmetrically: candidate payload count, byte-identical count, candidate-only count, retained-only count, and whether manifest metadata differs. Do not call two directory trees “identical” when the retained tree is actually a verified superset.
7. Freeze the exact candidate tree fingerprint after the comparison and revalidate it immediately before deletion; do not reopen original SQLite databases during this hash-only pass.

## Meaningful SQLite comparison

- Run `PRAGMA quick_check` and `PRAGMA foreign_key_check` read-only on every candidate DB.
- Compare candidate DBs to the latest retained snapshot and the validated full archive.
- For tables with primary keys, count candidate rows absent from retained sources by PK.
- Treat `sessions`, `messages`, routing, model usage, delivery obligations, system prompts, and cron executions as meaningful history.
- Keep FTS shadow/index tables separate: candidate-only FTS internals do not by themselves prove unique user history.
- For tables without primary keys, report row-count differences and fail closed rather than claiming set containment.
- Prove union coverage directly: a candidate primary-key row is unique only when it exists in neither the validated archive nor the newest retained snapshot. Separate meaningful tables from FTS shadow/index tables before summing uniqueness.
- If union coverage across retained sources cannot be proven, classify the snapshot as protected.

### Never query the original snapshot DB in place

A SQLite connection intended as read-only can still remove or recreate stale `state.db-shm`/`state.db-wal` auxiliaries when URI flags, journal state, or library behavior differ. Those auxiliaries may be named by a checksum evidence set.

1. Fingerprint the original snapshot tree before inspection.
2. Copy the exact DB and any existing `-shm`/`-wal` files into the capacity-gated staging root; run `quick_check`, FK checks, attaches, and union queries only against the staged copy.
3. Open the staged DB with verified `mode=ro&immutable=1`, set temporary work to memory only when bounded, and confirm no new sidecars appeared in the original directory.
4. Revalidate the original tree after analysis. Missing or changed auxiliaries are an analysis-induced mutation, not harmless noise.
5. If recovery is required, restore only from a same-profile file whose external checksum equals the frozen expected checksum, recreate an expected empty WAL exactly, and require the full backup checksum manifest to pass before closure. Record the incident and recovery explicitly.

## Archive-member staging capacity gate

Before extracting large SQLite members from a compressed archive:

1. Read selected `TarInfo.size` values without extraction, verify that every requested member name exists, and sum the exact logical bytes.
2. Abort before extraction if even one selected member is missing. `tar` can extract the other members and still exit nonzero, leaving a large partial residue.
3. Read free bytes on the intended staging filesystem with `statvfs`.
4. Require selected bytes plus a safety margin (at least 25%, and never less than 512 MiB) to fit.
5. Prefer hash-only streaming for files that do not need SQLite queries.
6. If DB extraction is required and `/run` is too small, use a secure disk-backed staging root outside Git. Freeze its exact cleanup manifest **before** extraction so residue removal already has an authorized, bounded path.
7. Never begin extraction into `/run` when the capacity gate is red. A partial tar extraction can fill tmpfs, make SQLite return `disk I/O error`, and endanger unrelated services.
8. Build temporary-tree fingerprints as relative-path keyed, sorted records. Raw traversal order is nondeterministic; compare normalized metadata maps so an unchanged tree cannot trigger repeated critical-confirmation loops.

If staging still fails, stop: prove original snapshots unchanged, inventory the exact temporary residue, and obtain the Critical Subset confirmation before deleting it. Do not conceal the residue or treat a reboot as cleanup.

## Reporting decision

Report separately:

- bytes safely removable now (exact duplicate/subsumed and not checksum-coupled);
- bytes protected by immutable update evidence;
- bytes containing unique historical state;
- bytes still unclassified because the retained-source union was not proven.

A user request to “reavaliar” authorizes read-only comparison, not deletion of snapshots or temporary extraction residue.
