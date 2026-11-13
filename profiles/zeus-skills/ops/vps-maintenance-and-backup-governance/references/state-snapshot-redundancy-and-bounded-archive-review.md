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
- For tables with primary keys, count candidate rows absent from retained sources by PK, then independently compare the full candidate-column payload for each row. A surviving session ID can have a different historical system prompt, usage, routing or runtime version; PK coverage alone is not full historical-state coverage. Report missing keys separately from same-key/different-payload versions and distinguish message preservation from old technical-state retirement.
- Inspect the schema of every candidate phase before building retained-source coverage. Preparation, activation and recovery can legitimately have different tables/columns despite equal file size. Cache union coverage by the candidate's table/column/PK projection, not by date or the first phase's schema; keep missing retained columns fail-closed and rerun all affected variants after an over-strict schema equality gate fails. Fingerprint source files before/after to distinguish legitimate schema versions from drift.
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

## Bounded RAM shadow for coherent standalone SQLite backups

Use this optional integrity-check route only for already consistent, standalone backup DBs with no nonempty WAL/SHM sidecars by default; the narrowly validated stale-SHM exception below is the only additional route. Do not use it for live databases or to infer WAL recovery or historical-row subsumption from integrity alone.

1. Test `sqlite3.Connection.deserialize` on a synthetic fixture first, including `quick_check`, FK checks, known row counts and a `query_only` write rejection. A SQLite URI under `/proc/self/fd/<memfd>` may fail to open; do not keep retrying that route or touch the original snapshot to compensate.
2. Before each DB, require live `MemAvailable >= 3 × DB logical bytes + 1 GiB`; process sequentially and release each connection/buffer before the next. Use a bytearray/readinto clone to avoid unnecessary full-buffer copies, `temp_store=MEMORY` and a bounded SQLite cache. Fall back to the separately capacity-gated file staging workflow when RAM cannot safely hold the clone.
3. A coherent DB can retain SQLite WAL journal-format header bytes even after checkpointing. If deserialize cannot open that standalone form, normalize only header offsets 18 and 19 from 2 to 1 **in the disposable RAM clone**. First prove that exact two-byte transformation on a fixture; require the source signature and header versions, and never apply it to the original or to a DB requiring a nonempty WAL.
4. Run `query_only=ON`, `quick_check` and `foreign_key_check` against the RAM clone only. Record checks and exception findings without exposing rows, messages, credentials or config contents. This is an integrity check of a coherent backup, not a production restore or proof that one snapshot subsumes another.
5. Verify each original inode, size, nanosecond mtime and external SHA-256 before/after inspection. Reuse an integrity result only for an identical complete DB digest. Bind the validation to retained archive/snapshot manifests and record zero persistent staging bytes.

### Checksum-frozen native backups with empty WAL and stale SHM

A sealed native backup may retain a standard 32 KiB SHM index with an absent/zero-byte WAL. This is not a nonempty WAL recovery case. Permit a RAM-only inspection only after validating the standalone deserialize fixture (known rows, integrity/FK, query-only write rejection and copy-only header normalization), proving the backup's recorded hashes and zero source `cwd`/`exe`/FD consumers, and applying the same per-DB RAM gate. Copy the SHM bytes into RAM for preservation bookkeeping but do not use them as an input to SQLite; require its size to be exactly zero or 32768 bytes and reject a nonempty WAL before any clone. Never connect SQLite to the original DB or sidecars. Require quick/FK checks on the RAM image, then revalidate every original node, file hash and sidecar's inode/size/mtime after analysis. Unknown SHM layout, a live/changed source, nonempty WAL or failed integrity returns to the separately gated staging route; do not broaden the exception. Any historical-row claim still requires the independent schema-aware retained-union comparison, not this integrity fixture.

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

## Compact preservation before historical snapshot retirement

When Rodolfo authorizes compact preservation rather than loss of old technical state, prefer a lossless dependency-aware capsule over exporting only selected SQL rows. Native `zstd --patch-from=RETAINED_DB` can preserve an old DB byte for byte relative to a checksum-frozen retained native DB; preserve unmatched non-DB files as deduplicated compressed objects and reference only proven-identical files/members in retained recovery sources. This also keeps old auth/config/skills and SQLite WAL/SHM bytes recoverable, not just message rows.

1. Discover the installed codec and read its native help/manual before use; do not install a system package implicitly. Test plain and delta roundtrips, wrong-base checksum rejection, truncation/corruption and unchanged inputs on private synthetic fixtures. Exercise the wrapper's isolated-new-directory restore and rejection of an existing destination.
2. Keep the capsule under a protected backup class with 0700 directories and 0600 files, outside Git; put only code, counts, hashes and receipts in canonical evidence. Never print restored contents or ship the archive as a Discord attachment. A `.tar` of individually compressed `.zst` objects is a compact archive even without whole-container compression and permits bounded random-access validation.
3. Gate disk peak and per-process RAM before encoding/decoding. A tested invocation is `zstd -q -3 --single-thread -M2048MB --check -c --patch-from=EXACT_BASE -- EXACT_OLD_FILE`; decode through `zstd -q -d -c -M2048MB --check --patch-from=EXACT_BASE`. The 2048 MB dictionary/window limit is not a complete process-RAM estimate; conservatively reserve at least `3*(base bytes + output bytes) + 1 GiB` and process sequentially. Retain interrupted new artifacts rather than implicitly deleting them.
4. Record every external dependency's exact path/hash and require all of them to lie outside the proposed retirement roots and remain immutable. Mark the capsule explicitly **not self-contained**. Pin those base files/archive members in inventory until an independently verified rebase or standalone successor exists; creating a delta must not silently change future retention.
5. Include the frozen per-path file hashes, directory/link metadata, per-object codec/reference recipe, code and usage instructions. Keep the portable recovery helper beside and inside the capsule. Recover only to a new isolated destination, never overwrite a live profile; recreate links last without following them and never execute historical skills/config as instructions.
6. Independently decode every unique object using only the capsule and retained dependencies, then verify its original full-file SHA-256 for every target pathname. Reconstruct complete old DB images in bounded RAM and run query-only integrity/FK checks there; report this honestly as byte-exact RAM reconstruction, not a full filesystem restore. Revalidate original trees/sidecars and all dependencies afterward.
7. Preserve old immutable SHA manifests unchanged. Exact-byte recovery permits preparing an explicit archival-relocation gate, not automatic deletion: state that the direct old expanded paths and direct old rollback access will disappear and require reconstruction before using legacy rollback tooling. Freeze the exact roots/counts/reclaim, capsule/base hashes and the same pre/post validator; test scope reduction, count/metadata drift and missing approval without deleting anything. Ask the separate Critical confirmation only after that gate passes.
8. Report capsule occupancy, source occupancy, validated prospective reclaim and observed savings separately. A newly written capsule increases disk use until old copies are explicitly removed; never count its source size as already freed.

## Reporting decision

Report separately:

- bytes safely removable now (exact duplicate/subsumed and not checksum-coupled);
- bytes protected by immutable update evidence;
- bytes containing unique historical state;
- bytes still unclassified because the retained-source union was not proven.

A user request to “reavaliar” authorizes read-only comparison, not deletion of snapshots or temporary extraction residue.
