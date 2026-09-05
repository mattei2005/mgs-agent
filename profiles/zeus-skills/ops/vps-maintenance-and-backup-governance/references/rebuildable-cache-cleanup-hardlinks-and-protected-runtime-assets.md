# Rebuildable Cache Cleanup — Hardlinks and Protected Runtime Assets

Use this reference after an update/port when package-manager and test caches may be safely rebuilt but the same cache roots can contain hardlinks or assets required by live browser/transcription workflows.

## Classification boundary

Treat these as **candidate classes**, never automatic targets:

- package/build caches: UV, pip, npm content cache, npx, Electron, node-gyp;
- OS package payload cache: downloaded APT `.deb` files only;
- recent test/compiler temporaries with zero process references.

Keep separate and protected until a live consumer map proves otherwise:

- Playwright/Chromium revisions used by active Hermes, browser collectors, or persistent login tooling;
- persistent browser profiles containing cookies, Local State, IndexedDB, or sessions;
- Hugging Face/Whisper model caches used by transcription;
- active venvs, `node_modules`, rollback runtimes, state snapshots, checkpoints, and current update backups.

## Default post-update cleanup policy

A routine update closure removes **residue created by that update**, not general working caches that will immediately refill.

1. Tag every candidate by origin: pre-existing, created by the current update, or the same volatile target re-fingerprinted after drift.
2. After activation and validation, clean only update-created material that is no longer a recovery path: inactive staging/worktrees, superseded candidate venvs, duplicate update archives beyond the validated keep-latest policy, downloaded package payloads after their rollback window, transient test/build directories, and stale finalizer/unit artifacts.
3. Preserve ordinary UV/pip/npm, compiler, browser, model, and test caches by default when they support current tools or continue changing during the maintenance window. Their regeneration cost and network churn are real operational costs even when deletion is technically safe.
4. Clear a general cache only for one of four reasons: material disk pressure (normally the MGS warning threshold around 75%), confirmed corruption, a retired tool/version that no longer consumes it, or an explicit owner request after an exact hardlink-aware manifest.
5. A cache that changes between confirmation and execution is evidence of current use. Block without mutation; do not keep chasing refreshed hashes. Unless disk pressure or corruption still justifies removal, cancel that cache target and close it as intentionally retained.
6. If the update created only compact evidence and left no bulky inactive staging or duplicate rollback set, the correct cleanup result is `no deletion needed`. Do not manufacture savings by deleting useful caches merely because the maintenance window ended.

## Hardlink-aware accounting

Cache directory `du` totals can materially overstate reclaim when UV or similar stores hardlink files into active venvs.

1. Inventory every node in the proposed target set by `(st_dev, st_ino)`.
2. Count links inside the complete target set.
3. Credit file blocks only when `links_inside >= st_nlink`; credit directory blocks separately.
4. Report both naive allocated bytes and inode-aware reclaimable bytes.
5. Bind authorization and the projected disk state to the inode-aware value.
6. After deletion, use the observed `df` free-space delta as authoritative.

Do not call a multi-gigabyte cache tree a multi-gigabyte saving when most blocks remain through hardlinks in active environments.

## Exact target construction

- Freeze cache roots as exact `delete_tree` targets only after proving each root is a directory, not a symlink or mount, and has zero process references.
- For APT, enumerate exact current `.deb` files as `delete_file` targets. Preserve `/var/cache/apt/archives`, `lock`, and `partial`; do not delete the cache root.
- Store a metadata fingerprint per target over relative path, type, size, blocks, nanosecond mtime, inode, link count, and symlink target without following symlinks.
- Keep large fingerprint streams outside Git, preferably under `/run`; persist only the hash and compact manifest needed for audit.
- Volatile `/tmp` targets may drift between proposal and confirmation. Revalidate every fingerprint immediately before deletion. Any added, removed, or changed target—including a reduction—invalidates the manifest and requires a new confirmation.

### Coherent freeze for caches that mutate during enumeration

A large cache can change while its own inventory walk is still running. A zero-reference check performed at the end does not prove that counts, sizes, mtimes, and the fingerprint came from one coherent state. Before showing the critical hash:

1. wait for cache-writing package/build processes to quiesce;
2. generate the complete target inventory twice, with a short quiet interval;
3. normalize every node to a relative path and sort by that path before comparing or hashing; raw `rglob`/filesystem traversal order is not stable and must never create a false drift;
4. require exact equality of the normalized target list, per-target counts, logical/allocated bytes, mtimes, and fingerprint hashes across both passes;
5. freeze and hash only the second stable pass;
6. immediately before deletion, regenerate the same normalized fingerprint map and compare it to the confirmed pass.

If the first execution preflight finds real metadata drift, record `blocked_no_mutation`, prove every target remains present, discard that authorization, and repeat the two-pass freeze. If only list order differs while the relative-path keyed metadata maps are identical, fix the validator to compare normalized maps and retain the same target hash; do not enter a confirmation loop for nondeterministic enumeration. Never update a manifest in place and reuse the previous “sim” after a real target change, even when the path list is unchanged or the byte delta is only a few KiB.

A user message such as “apaga” before the target hash is shown authorizes preparation only. Critical deletion confirmation comes after the exact hash, counts, current/projected disk state, retained assets, and irreversible effect are presented.

## Consumer mapping before protecting or deleting

- Derive required Playwright revisions from each active consumer's `playwright-core/browsers.json`; do not hardcode revisions from a previous maintenance window.
- Distinguish browser binaries from persistent browser profiles. A disposable Playwright temp profile is not equivalent to a named authenticated profile.
- Identify Hugging Face model families from cache metadata and active transcription configuration before classifying them.
- Check systemd, cron, scripts, process cwd/exe/cmdline, and open file descriptors for target references.

## Post-deletion acceptance

Require:

- exact absence of every confirmed target and zero scope expansion;
- active runtime HEAD/launcher/patch unchanged;
- rollback integrity and required retained caches/profiles still present;
- gateways active/running with real per-profile smokes;
- failed units zero and observed `df` delta recorded;
- inventory, audit, checkpoint, REPORT-INFRA readback, and scoped Git auto-versioning closed.
