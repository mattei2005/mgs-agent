# Full-VPS Cleanup Inventory and Exact Deletion

Use this reference when a maintenance window must remove an already-confirmed target set and then inventory every remaining backup or likely-unused artifact across the VPS.

## 1. Freeze before deletion

Create an immutable manifest containing, for each exact target:

- absolute listed path and action (`delete_file`, `delete_symlink`, or `delete_tree`);
- file, directory, and symlink counts;
- logical and allocated bytes;
- same-device metadata fingerprint over relative path, type, size, blocks, nanosecond mtime, and symlink target;
- process-reference count;
- explicit retained recovery paths;
- target-set SHA-256 computed from canonical JSON.

Never use globs. Immediately before the audit start boundary, re-read every target and abort on missing paths, type drift, fingerprint drift, process references, mount crossings, failed units, active-runtime drift, or loss of a retained rollback artifact. Record the user's confirmation message ID and target-set hash in the audit start event.

Delete only the exact confirmed set. Record every removed path. On any exception, emit a partial-failure event containing deleted and remaining paths before raising.

## 2. Estimate disk recovery correctly

Do not add `st_blocks * 512` naively when hardlinks may exist. That can materially overstate actual recovery.

For a target set:

1. Count each `(st_dev, st_ino)` once.
2. Count how many hardlinks to that inode are inside the target set.
3. Credit file blocks as reclaimable only when all links (`links_in_set >= st_nlink`) are removed.
4. Add directory inode blocks separately.
5. Report both the naive allocated sum and the inode-aware reclaim estimate.
6. After deletion, treat `df` free-space delta as the authoritative observed result; concurrent writes mean it can still differ from the estimate.

Never promise the manifest's naive allocated sum as actual reclaimed space.

## 3. Post-deletion acceptance

Before declaring success, verify:

- every confirmed target is absent;
- active runtime/launcher and upstream relation are unchanged;
- target services are active and use the expected runtime path;
- config checks and real agent smokes pass;
- failed systemd units remain zero;
- rollback launcher/runtime still work;
- retained archives pass integrity listing/readback;
- current disk bytes and observed free-space delta are captured;
- inventory, audit, checkpoint, REPORT-INFRA, and Git state are reconciled.

## 4. Whole-VPS read-only scan

Scan writable persistent filesystems independently. At minimum on the MGS VPS:

- scan `/` on its own device while pruning pseudo-filesystems and mount crossings;
- scan `/boot` separately when it is a different device;
- scan `/boot/efi` separately when it is a different device;
- inventory read-only loop/Snap mounts separately if relevant, but do not mix their immutable contents into deletion candidates.

Record file count, directory count, logical bytes, allocated bytes, and errors for every scanned filesystem. Zero errors is required for a complete claim.

Inventory backups in two layers:

1. Operational backup roots and their first-level sets.
2. Standalone backup-like files outside those roots (`*.bak*`, `*.backup*`, `*.orig`, `*.save`, `*~`, explicit `before-*`, and validated update archives).

Exclude dependency/source directories such as `.git`, `node_modules`, virtualenvs, and `site-packages` from filename-only backup detection. Avoid a broad `pre-*` pattern: it misclassifies precheck logs and ordinary source artifacts as backups.

Keep the exhaustive child-file list in a JSON/CSV artifact. Discord reporting should list exact deletion candidates at file or operational-set boundary, plus counts and bytes—not thousands of child paths.

## 5. Evidence tiers for "unused"

A filesystem scan cannot prove semantic non-use. Classify findings as:

- **High confidence, no runtime use:** superseded virtualenvs, stale temporary top-level entries, orphan browser bundles whose `.links` target is missing, rebuildable package caches, and test caches—only after process, service, cron, and script-reference checks.
- **Review required:** second-newest validated backups, closed repair rollback sets, local media/evidence mirrored remotely, update/build dependencies, old reports, old operation backups, package caches, and package-manager autoremove candidates.
- **Protected:** active runtime, minimum rollback, live profile state, institutional Git, current browser revisions, local models, latest validated archives, and unique secure backups.

Do not sum overlapping review roots into one reclaim figure. When a parent root and child candidates are both reported, label the aggregate as non-additive.

For old temporary material, list top-level entries individually, apply an explicit age threshold, exclude current lock files, and require zero process references. Temporary media may still carry evidence value, so keep it separate from purely rebuildable caches.

## 6. Housekeeping dry-run pitfalls

With `set -Eeuo pipefail`:

- `producer | head -N` can fail when `head` closes early and the producer receives SIGPIPE. Bound output inside the producer instead, e.g. `awk 'condition && shown < N { print; shown++ }'`.
- `find /optional/root ... 2>/dev/null` still returns nonzero when the root is absent. Guard optional roots with `[[ -d "$root" ]]` in both dry-run and live paths.

A dry-run is accepted only when it exits zero, prints its final summary, and a mutation check proves every named candidate still exists.

## 7. Authorization boundary

A user's confirmation applies only to the frozen target-set hash they were shown. A later whole-VPS scan creates a new scope. Do not remove newly discovered items—even obvious caches—until a new exact manifest and Critical Subset confirmation are obtained.
