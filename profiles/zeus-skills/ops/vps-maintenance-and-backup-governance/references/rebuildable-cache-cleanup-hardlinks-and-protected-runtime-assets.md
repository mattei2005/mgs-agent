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
