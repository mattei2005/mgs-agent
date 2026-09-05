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

### 3.1 Git closure when confirmed targets contain tracked files

A destructive cleanup can be filesystem-correct while its Git evidence looks incomplete if the auto-commit watcher divides hundreds of deletions and policy edits into several commits. Close the versioned boundary this way:

1. Before deletion, capture the repository HEAD and enumerate every tracked file under the frozen target roots from that exact tree.
2. Pause the auto-commit watcher before the first removal so it cannot commit a partially deleted target set or half-applied policy change. Keep gateway services untouched.
3. Finish filesystem validation, policy readbacks, audit, inventory, checkpoint, and REPORT-INFRA before letting the watcher flush the repository.
4. After synchronization, validate `pre_operation_head..post_operation_head`; never inspect only the final commit. Require every tracked deletion in the range to equal the pre-operation tracked files under the confirmed roots, with zero unexpected deletions and zero expected files left behind.
5. Validate required script/skill/data changes across the same range. A manifest that was committed before the owner's confirmation is correctly absent from the post-confirmation diff; prove that it remains tracked and still contains the confirmed operation-set hash instead of calling it missing.
6. Require a clean worktree, active auto-commit service, and `HEAD == origin/main`. Record the commit range when the watcher produced more than one commit.

### 3.2 Upstream advancement discovered during cleanup

A final fetch may show that an application upstream advanced after the destructive manifest was confirmed. Do not let that moving ref rewrite the cleanup result or silently widen the authorized scope.

- Re-fetch only after filesystem/runtime acceptance and freeze the newly observed upstream SHA.
- If the active launcher, runtime, patches, and services are unchanged, the cleanup may still be `completed_validated`; record the installed base, upstream SHA, behind count, and concise delta as a separate follow-up.
- Never claim `behind=0` from a pre-cleanup observation after a later fetch disproves it.
- Porting patches, building a new runtime, or restarting production belongs to a separate controlled-update scope and its own Critical Subset confirmation.
- Do not classify ordinary upstream movement as a cleanup anomaly.

### 3.3 Final-result checksum ordering

Treat the cleanup result as mutable until transport and governance closure have finished. REPORT-INFRA message IDs/readback, `governance_errors`, final status, and closure timestamps are part of the canonical result, so hashing an earlier version creates a stale inventory receipt.

Use this order:

1. Complete filesystem/runtime/archive acceptance and write the result body.
2. Send REPORT-INFRA and obtain exact Discord readback.
3. Add transport IDs/readback, final status, governance errors, and closure timestamp to the result.
4. Compute the canonical result checksum with the external checksum tool, write its checksum file, and verify it immediately.
5. Persist that final checksum in inventory and append the dedicated audit receipt.
6. Read back the result, checksum file, inventory record, and audit event before reporting closure.

If anything writes the result after step 4, recompute the checksum and replace the inventory/audit receipt before closure. Never leave an intermediate checksum labeled as final.

### 3.4 Residual-only open-item ledger

After deletion, build a fresh residual inventory and classify what remains into three separate lists:

- **required operational blockers** — prevent completion and keep the parent task open;
- **optional housekeeping** — safe follow-ups such as stale Git metadata with negligible disk impact;
- **intentionally retained or out-of-scope** — active runtime, minimum rollback, latest validated backups, and moving-main commits outside the selected stable release.

When the owner asks what remains open, list only these current residuals. Do not repeat deleted targets, call protected recovery artifacts “unused,” or turn commits arriving after a frozen stable tag into a failed cleanup/update gate. State `none` explicitly when no required operational blocker remains.

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

### 5.1 Persistent browser sessions are not browser caches

A large Playwright/Chromium tree may contain either a rebuildable binary bundle or irreplaceable authenticated session state. Never classify them together by size, age, or the word `browser`.

Before proposing a browser-related target:

1. Resolve the consumer script's persistent profile path, lock path, tool/runtime directory, and `browsers.json` revision.
2. Separate binary caches such as `home/.cache/ms-playwright/<revision>` from profile state such as `browser-profiles/<purpose>` containing Cookies, Local State, IndexedDB, Sessions, and storage.
3. Prove required browser revisions from the union of **all installed** Playwright `browsers.json` manifests under active Python venvs and Node runtimes, plus live process `exe`/open-file references. Do not rely only on `.links`: it can contain stale entries pointing to removed `/tmp` venvs while another unlinked active runtime still requires a cached revision. Protect every revision in that union even if only one browser is running at scan time.
4. Treat a stale `.links/<id>` file as a separate tiny candidate only when its target is missing, no process references it, and deletion cannot remove the only provenance for a required revision. Never infer that the corresponding browser bundle is orphaned from the stale link alone.
5. Freeze the persistent profile, lock, collector runtime, and required browser revision as an explicit protected set. Do not delete cache-looking subdirectories inside the persistent profile unless the owner separately authorizes session compaction.
5. Treat collector outputs/evidence as a different storage class. They may be reviewed for retention without touching authentication state.

6. For a named session that must survive, hash a minimal set of non-secret state containers such as `Cookies`, `Local State`, and `Preferences` immediately before the destructive boundary and compare them after cleanup. Report only pass/count, never contents. Authentication may already be expired; that does not make the owner-protected profile deletable.

When the owner says a named browser session must survive cleanup, that protection overrides generic orphan/cache classification and belongs in the manifest's protected paths.

### 5.2 Drive-backed local media must close by lineage

For creative/media staging, remote existence is proven by the canonical Shared Drive—not by filename coincidence or an old success message.

1. Validate the canonical Service Account and Shared Drive `driveId`.
2. For uploaded/final media, require a live non-trashed destination ID plus exact size and MD5; require recorded SHA-256/readback parity when the operation manifest provides it.
3. For execution trees containing raw and readback copies, require every completed item's destination ID live and its recorded size/hash valid. Empty abandoned execution directories may be classified separately as stale temporary material.
4. Derived frames/contact sheets may be deleted with their local batch only when their parent media has exact remote closure and no independent evidentiary retention applies.
5. If legacy IDs are missing after a migration, exclude that local root from the destructive manifest. Do not infer a replacement by name alone.
6. A future upload workflow may remove transient local media immediately after this readback, but must preserve a compact provenance manifest containing source ID, destination ID, filename, size, checksum, and status.

## 6. Housekeeping dry-run pitfalls

`npm cache verify` is **not** a read-only verification command: npm may garbage-collect stale cache objects while validating the cache. During discovery, size npm caches with metadata-only filesystem reads and use non-mutating listings where needed. Run `npm cache verify` only inside an authorized cache-cleanup scope, capture its reported garbage-collected bytes, and verify the post-command cache size and filesystem delta before reporting the effect.

With `set -Eeuo pipefail`:

- `producer | head -N` can fail when `head` closes early and the producer receives SIGPIPE. Bound output inside the producer instead, e.g. `awk 'condition && shown < N { print; shown++ }'`.
- `find /optional/root ... 2>/dev/null` still returns nonzero when the root is absent. Guard optional roots with `[[ -d "$root" ]]` in both dry-run and live paths.

A dry-run is accepted only when it exits zero, prints its final summary, and a mutation check proves every named candidate still exists.

## 7. Authorization boundary

A user's confirmation applies only to the frozen target-set hash they were shown. A later whole-VPS scan creates a new scope. Do not remove newly discovered items—even obvious caches—until a new exact manifest and Critical Subset confirmation are obtained.
