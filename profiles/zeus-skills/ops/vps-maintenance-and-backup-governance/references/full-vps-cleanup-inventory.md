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

Never use globs. Immediately before the audit start boundary, re-read every target and abort on missing paths, type drift, fingerprint drift, process references, mount crossings, failed units, active-runtime drift, or loss of the explicitly retained recovery artifact. Record the user's confirmation message ID and target-set hash in the audit start event.

Keep the deletion-time verifier self-contained, or freeze and verify the SHA-256 of every helper it imports before the audit start. The target-set hash authenticates the data being interpreted, not transient code under `/run` or `/tmp`; an unhashed helper can otherwise change the meaning of a valid manifest between preparation and execution.

Run Git cleanliness, worktree, alternates, and HEAD readbacks **before** the final metadata fingerprint. Commands such as `git status` can refresh `.git/index` metadata even when the worktree is clean, so running them after the fingerprint can manufacture false drift and trigger a re-freeze loop. Freeze the clean Git result in the manifest, then perform two normalized fingerprint passes separated by a short quiet interval and require exact equality before showing the hash. After that hash is shown, the deletion-time verifier must not invoke `git status`, `git worktree list`, `git rev-parse`, or any other Git command inside a target tree; it consumes the frozen Git assertions and performs only manifest-hash, metadata-fingerprint, process, mount, retained-path and active-runtime checks. If any helper or preflight touches target Git metadata after the freeze, stop before the audit boundary, prove zero deletions, supersede the manifest with a fresh double-pass hash, and obtain a new confirmation for that hash.

When the owner requests latest-only retention, define the operational class before building the manifest and resolve its newest validated recovery set from the activation receipt. For backup-only requests, target older backups in that class; do not infer retirement of source checkouts or launchers. If inactive runtime/candidate cleanup is also authorized, apply the sibling-checkout sweep and alternate/worktree gates before adding those targets. Keep active-code dependencies, `/var/backups`, site/WordPress backups, persistent browser profiles, credential stores and offsite retention excluded unless separately named.

Detect process use from `/proc/<pid>/cmdline` as well as `cwd`, `exe`, and open file descriptors. A virtualenv can resolve `/proc/<pid>/exe` to a shared UV base interpreter while `argv[0]` still points inside the active runtime; checking `exe` alone can falsely classify the source repository as unused.

Exclude the auditor PID and its ancestor shell/tool-wrapper chain from literal command-line matches: an inline Python or shell audit can contain every candidate path as data and otherwise report itself as a consumer. Compare exact paths or directory-boundary prefixes (`root + '/'`), not arbitrary substrings; `hermes-agent` must not match every `hermes-agent-port-*` sibling. Keep the exclusion list and scope in the receipt; do not exclude independent workers or infer semantic non-use from a zero-reference result.

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

Compute hardlink closure across the **whole confirmed target set**, not independently per root. If an inode is linked between two candidate trees, summing per-root `du` or reclaim values still double-counts it even though every link is deletable. This also changes executor sequencing: validate every target fingerprint, process reference, mount boundary, and retained path in one complete pre-mutation pass. After the audit start boundary, do not recompute metadata fingerprints for later roots after deleting an earlier root, because legitimate removal of a cross-root hardlink changes `st_nlink` and would manufacture drift midway through an otherwise valid deletion. Before each removal, recheck only exact path identity, allowed root, expected type, and no symlink; journal each result and validate global target absence at the end.

## 3. Post-deletion acceptance

Before gating REPORT-INFRA on an own-profile skill's versioned mirror, compare that exact live/mirror pair and reconcile the native export state. Export may be asynchronous; successful `skill_manage` proves neither immediate mirror parity nor a failed sync. Prefer the canonical scoped exporter or a bounded wait for its existing writer, then reread both hashes and the affected hunk. Do not start a manual mirror writer while native export is pending or in flight; use its coordinated exporter or let it converge first. If manual mirror synchronization is still needed, require the exact expected old hunk and zero copies of the new hunk in a fresh read; treat an already-present new hunk as a no-op. Never apply a prefix-only insertion from a stale mirror observation: export can land between the read and patch and duplicate the lesson. Apply only the owned delta, verify external SHA-256 equality and single occurrence, and preserve another profile or concurrent writer's content. Do not bypass native Git batching. Mirror delivery is governance work, not a failed filesystem operation; never repeat deletion to repair it.

Before declaring success, verify:

- every confirmed target and descendant is absent; independently compare the deletion journal with the immutable node index by exact normalized path and node type, require equal sets and counts, and reject duplicate entries—an exit-zero executor plus absent top-level folders does not prove that only approved nodes were removed;
- explicitly retained state still matches its frozen metadata and payload hashes; keep this independent preservation check separate from service health and do not start a database merely to hash its files;
- active runtime/launcher and upstream relation are unchanged;
- target services are active and use the expected runtime path;
- config checks pass and any required availability smoke stays within the owner's validation scope; use section 3.4 to distinguish configuration/process integrity from a permitted model request;
- failed systemd units remain zero;
- rollback launcher/runtime still work;
- retained recovery paths are resolved from the fresh manifest/inventory, confirmed to exist, and then pass integrity listing/readback; never reconstruct a backup path from a historical label, approximate size, or remembered directory name;
- each smoke's reported claim matches its actual assertion contract—a diagnostic command that merely logs anomalies and exits zero proves execution or reopen only, not UI/layout correctness; use an assertion-bearing test before claiming the broader property;
- the immediate pre/post-deletion filesystem readings establish observed reclaim, and a fresh reading just before delivery establishes current disk/free space; keep these observations separate when validation or native Git batching allows concurrent writers to change occupancy;
- inventory, audit, checkpoint, REPORT-INFRA, and Git state are reconciled.

Before running a monolithic closure validator, inspect each retained state file's current top-level keys and status vocabulary with a bounded readback, then freeze those exact assertions. Normalize only known equivalent success values such as `PASS` versus `success`; never guess field names such as `last_success` versus `last_successful_backup`. A schema mismatch is a validator defect, not an operational failure: correct it from live readback before retrying so repeated guessed assertions do not consume the anti-loop budget or obscure the already-validated cleanup.

### 3.1 Git closure when confirmed targets contain tracked files

A destructive cleanup can be filesystem-correct while its Git evidence looks incomplete if the auto-commit watcher divides hundreds of deletions and policy edits into several commits. Close the versioned boundary this way:

1. Before deletion, capture the repository HEAD and enumerate every tracked file under the frozen target roots from that exact tree.
2. Pause the auto-commit watcher before the first removal so it cannot commit a partially deleted target set or half-applied policy change. Keep gateway services untouched.
3. Finish filesystem validation, policy readbacks, audit, inventory, checkpoint, and REPORT-INFRA before letting the watcher flush the repository.
4. After synchronization, validate `pre_operation_head..post_operation_head`; never inspect only the final commit. Require every tracked deletion in the range to equal the pre-operation tracked files under the confirmed roots, with zero unexpected deletions and zero expected files left behind.
5. Validate required script/skill/data changes across the same range. A manifest that was committed before the owner's confirmation is correctly absent from the post-confirmation diff; prove that it remains tracked and still contains the confirmed operation-set hash instead of calling it missing.
6. Require a clean worktree, active auto-commit service, and `HEAD == origin/main`. Record the commit range when the watcher produced more than one commit.

Exception: if audit, expected-service state, and the owning security checkpoint prove auto-commit is intentionally disabled for active sensitive-data containment, do not restart it or make a manual commit merely to close the cleanup. Reconcile every dirty path to authorized concurrent work, keep the validated filesystem/result/inventory/audit closure local, and record versioning as governed by the parent security incident. An intentionally paused writer is different from an unexplained inactive writer; only the latter blocks closure as an infrastructure fault.

#### Untracked targets and native batching

Resolve Git ownership before running a tracked-file gate: walk the target's ancestors for a `.git` file/directory and confirm the worktree boundary. For a target inside a repository, rerun `git ls-files -z -- <exact paths>` from that owning repository immediately before deletion and compare paths programmatically. For a profile artifact outside the institutional repository with no owning Git root, record that structural exclusion; do not pass its absolute path to an unrelated repository and interpret an outside-repository error as either tracked or safely untracked. If the intersection remains empty, leave the healthy auto-commit watcher running; pausing it adds no tracked-deletion protection. If a repository appears or a target becomes tracked, stop before deletion and apply the tracked-target closure above.

After filesystem acceptance, verify the governance artifacts independently of the deletion targets:

1. Resolve the real writer and its log before starting a waiter. Check `systemctl show mgs-autocommit.service -p ActiveState -p SubState -p UnitFileState`, then inspect `scripts/auto-commit-watcher.sh` for `LOG_FILE`, `BATCH_TARGET`, `BATCH_QUIET_SECONDS` and `BATCH_MAX_WAIT_SECONDS`, including service-environment overrides. Read the resolved log's latest batch count/start/flush; do not guess a similarly named unit or log. A batch counter can represent coalesced observation windows rather than individual file writes, so many new files do not necessarily trigger an immediate commit.
2. Classify the delivery set before fetching or starting a wait loop. Run `git check-ignore -v -- <path>` for each scoped artifact, inspect the native writer's negative pathspecs without sourcing its executable, and resolve eligible paths with `git ls-files --cached --others --exclude-standard -z -- <scope> <native-negative-pathspecs...>`. Partition expected-public files, intentionally local/private evidence and unexplained omissions; an untracked file can be writer-excluded even when `check-ignore` finds nothing. Record each exclusion's policy and purpose, validate its local receipt, and leave unexplained omissions blocking. Keep private logs, recovery evidence and runtime locks local; never rename private evidence, force-add it or weaken a guard just to make remote comparison pass. A nonprivate immutable delivery accidentally named like an excluded heartbeat may receive an eligible canonical projection only when the native policy permits that content; preserve the intermediate. Fetch the remote and checksum only the expected-public set against `git show origin/main:<path>`, including the frozen manifest, executor, approval receipt, final result/checksum and public validation evidence. Compare shared inventory/checkpoint rows separately from whole-file equality because unrelated writers may legitimately change sibling records.
3. Parse the remote inventory and checkpoint blobs and require this operation's final status and result checksum. `HEAD == origin/main` alone does not prove closure: both refs can still point to the previous planning commit while completed local records await batching.
4. If the watcher is active and the only gap is normal batching, derive the deadline from its actual batch-start time plus configured maximum wait, not an arbitrary retry count. Wait only the remaining window in bounded foreground chunks shorter than the tool transport limit. Return/persist `native_batch_pending` when a chunk ends before that deadline instead of asserting delivery failure; resume only the missing Git checks. Persist the scoped mismatch list and synchronization receipt outside the sealed result. If a wait call times out, check whether its process survived and whether a PASS receipt was already written before starting another waiter; never replay deletion to recover a Git-closure timeout. After a native flush, fetch and repeat exact blob and owned-record checks. Diagnose a writer fault only when logs/service evidence show a guardrail/error or the native deadline expires without progress. Do not manufacture events, shorten batching or manually commit merely to accelerate a healthy writer.
5. Keep the synchronization receipt outside the already-sealed result so recording verification cannot invalidate the checksum just checked. Freeze the delivery set, verify its remote blobs and exact inventory/checkpoint rows, and write one receipt naming their containing commit. If that receipt is also versioned, expect one additional native batch and verify its exact remote blob separately; do not rewrite the receipt or sealed result on every poll, because each write creates another convergence target. Distinguish operational acceptance, remote delivery of the original evidence and pending delivery of the final receipt; a newly created receipt awaiting a healthy batch is not a failed cleanup or failed push.

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

Separate result-producing collectors from read-only receipt verification. Before a collector opens an existing result for writing, reject reruns when that result is already sealed with verified transport/closure evidence; otherwise a later validation can silently reset report status, timestamps and the inventory-bound checksum. Exercise this guard after sealing: require its explicit refusal and identical external SHA-256 values before and after, without replaying the operation. Put subsequent health observations or Git-delivery receipts in separate artifacts, and use a reader—not the original result-producing collector—to verify the completed receipt.

Render confirmation/question message IDs and the manifest identifier in closure documentation directly from the native approval receipt, rather than retyping them. Build report target/path fields from the frozen manifest as well: shortening a directory name into a nonexistent path is not a valid summary. Assert exact identifiers and target values before publication/versioning. Correct a documentation-only error from native evidence without replaying the filesystem action or rewriting approval; if an already-posted owned report needs correction, update that same message, preserve its silent embed-only delivery and read back the exact fields again before sealing the result. Do not send a duplicate report to repair a field.

### 3.4 No-tool profile availability smoke

First resolve the validation scope. When the owner excludes model requests, database startup or application execution, do not turn a filesystem check into one of those operations. Validate configuration, gateway PIDs/launcher and retained-file hashes; record the excluded provider/application layer as not tested rather than calling it healthy. If that layer is an explicit acceptance requirement, surface the scope conflict instead of silently running or waiving it.

When a model availability probe is permitted and required, use a bounded, tool-disabled one-shot through the launcher reconciled with live gateway PIDs. Check the current CLI help before reusing flags, then run once for each named production profile:

```bash
/root/.local/bin/hermes -p <profile> config check
/root/.local/bin/hermes -p <profile> chat --oneshot -Q -t '' --max-turns 1 --run-budget 60 -q 'Reply only MGS_CLEANUP_SMOKE_OK. Do not use tools or modify files.'
```

Require both exit codes to be zero and the marker in the final answer; retain compact per-profile results and elapsed times. Compare the gateway PIDs with the immediate pre-deletion baseline to prove no restart occurred. A successful text smoke proves agent/provider availability, not browser login, financial UI correctness or unchanged database contents; retain those independent checks. Keep the probe free of delegated work and operational tool calls so validation does not become another production task.

### 3.5 Residual-only open-item ledger

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

Record file count, directory count, logical bytes, allocated bytes, and errors for every scanned filesystem. Install an `os.walk(..., onerror=...)` collector as well as per-entry `lstat` error handling; a traversal can otherwise suppress inaccessible-directory errors and falsely report complete coverage. Zero recorded errors is required for a complete claim.

Persist the metadata ledger before beginning content hashes or remote verification so an interrupted expensive stage can resume without another filesystem sweep. Precompute string roots and use boundary-aware prefix tests in large walks rather than rebuilding `Path` objects against every category for every node. Hash selected regular-file batches with `sha256sum --zero -- <paths>` and, when needed, `md5sum --zero -- <paths>`; parse NUL-delimited output and recheck inode/size/mtime afterward. Preserve unmatched files and disclose excluded scopes instead of broadening a small verified reclaim amount into the whole parent-directory total.

Inventory backups in two layers:

1. Operational backup roots and their first-level sets.
2. Standalone backup-like files outside those roots (`*.bak*`, `*.backup*`, `*.orig`, `*.save`, `*~`, explicit `before-*`, and validated update archives).

Exclude dependency/source directories such as `.git`, `node_modules`, virtualenvs, and `site-packages` from filename-only backup detection. Avoid a broad `pre-*` pattern: it misclassifies precheck logs and ordinary source artifacts as backups.

Keep the exhaustive child-file list in a JSON/CSV artifact. Discord reporting should list exact deletion candidates at file or operational-set boundary, plus counts and bytes—not thousands of child paths.

### 4.1 Provider control-plane connector boundary

Treat an official hosting-provider Connector/MCP as a **control-plane** route, not a guest-filesystem auditor. A VPS-scoped connector can add high-value readbacks such as VM status, provider metrics, action history, backups/snapshots, SSH keys, and firewall state; it does not replace live guest checks such as `df`, mount-bounded `du`, inode accounting, `/proc` references, file lineage, or an exact deletion manifest. Use it to close the off-host backup/restore-capability gap before retiring local recovery artifacts, never to infer that a large guest path is safe to delete.

For MGS, expose only the provider's VPS product group or VPS-scoped MCP server when that is the requested scope; do not enable a unified connector that also exposes billing, domains, DNS, ecommerce, or unrelated hosting actions merely for disk maintenance. Prefer read-only inventory first and prove the connector is bound to the exact VPS. OAuth or an API token is a separate credential/configuration change, so do not install, connect, or generate credentials just because documentation was supplied. Store approved secrets through the governed credential route, validate one real non-mutating call, and inventory/report the integration. Provider restart, firewall/SSH mutation, backup restore, billing, and purchase tools retain their own Critical gates; a whole-VPS restore overwrites guest data and is never an incidental cleanup step.

### 4.2 Live backup high-water marks are not abandoned residue

- Correlate a large temporary backup/encryption workspace with its actual scheduler, wrapper, producer lifecycle and exact success receipt before calling it waste. A full scan can observe profile ZIPs, plaintext bundle and encrypted upload together; a pre-existing `TemporaryDirectory` producer may legitimately remove that workspace before delivery. Preserve the scan ledger, record the exact departed subtree and native lifecycle separately, then capture fresh `df`; never count that automatic removal as savings caused by the audit or offer the already-absent subtree as a new deletion lot.
- Partition application trees and agent profiles by role before assigning necessity: separate source/dependencies, exports/archives, generated database state, historical snapshots, working/test copies, media/evidence, live conversation state and installed tools. A repository `backups/` or `tmp/` directory is not institutional source code; a profile `work/` or `workspace/` is not automatically conversation memory. Recompute one inode-aware category partition and keep detailed child views non-additive to the parent totals.

## 5. Evidence tiers for "unused"

A filesystem scan cannot prove semantic non-use. Classify findings as:

- **High confidence, no runtime use:** superseded virtualenvs, stale temporary top-level entries, orphan browser bundles whose `.links` target is missing, rebuildable package caches, and test caches—only after process, service, cron and script-reference checks **plus the owning initiative checkpoint/thread gate**. Age, untracked Git status and zero process references do not make a test directory deletable while its owning operational thread is active or the checkpoint still expects follow-up; classify it as conditional until the initiative is closed and a fresh no-reference scan passes.
- **Generated local test databases require evidence-lineage, family-consumer, and retention-horizon checks.** For roots such as `private/{test-pg,ui-test,ui-browser,catalog-test,TEST-payroll,TEST-periods}-*`, search retained JSON/reports/inventory for exact-path references and inspect helpers that reopen a directory by prefix or “latest” selection. Split the result into two queues: preserve every evidence-linked cluster through the owner's defined acceptance horizon (for example, closed-period validation after a beta) and preserve one compatible current cluster for each family still consumed by a helper, unless the evidence is explicitly superseded/migrated or the helper first regenerates a fresh source and passes readback. Exact unreferenced clusters do **not** need to wait for the entire product initiative to end: after a fresh process/service/cron/script/mount/Git scan proves no dependency, the retained queue covers current verification, and the owner confirms a newly frozen destructive manifest, they may be removed while beta work continues. Re-audit the preserved queue at the acceptance horizon instead of carrying every redundant test cluster until then. “Untracked” proves only Git status, not absence of audit or test value.
- **Git alternate object stores are runtime dependencies, not inactive clones.** Before classifying an old Hermes checkout, recursively read the active repository's `.git/objects/info/alternates` chain and search active scripts/units for hardcoded checkout paths. A zero process-reference count is insufficient: protect every alternate ancestor until the active repository has been fully repacked/dissociated, the alternate pointer is removed or neutralized under the confirmed destructive scope, `git fsck` passes without alternates, and canonical consumers resolve the active launcher. If an exact cleanup manifest included an alternate ancestor, supersede that manifest instead of asking the owner to confirm an unsafe target-set.

### 5.1 Hermes sibling checkout and launcher sweep

A post-update cleanup that inspects only the current evidence directory can miss older top-level runtime trees. Run this residual pass whenever the owner asks what still remains to clean:

1. Enumerate every top-level `hermes-agent*` checkout and every executable or symlink matching `hermes*` under the canonical launcher directory. Resolve symlinks and inspect regular shell/Python wrappers without executing them: a canonical main launcher can be current while another configured wrapper still hardcodes an older tree. Capture allocated bytes per checkout; do not infer size from the update report that created it.
2. Resolve the canonical launcher and the three gateway `ExecStart` values, then scan `/proc` `cmdline`, `cwd`, `exe`, and file descriptors. Derive the active checkout from live resolution and derive exactly one immediate rollback from the latest validated activation receipt. Protect both.
3. Resolve the canonical profile/session roots independently and prove they are outside every candidate tree and launcher target. In the confirmation summary, distinguish storage roles explicitly: checkout = application code/environment; launcher = symlink to executable; profile/session root = conversations and agent state. A historical thread, receipt, or log mentioning a checkout proves provenance only and must not be described as conversation data stored inside that checkout.
4. Search systemd units, crons, active scripts, and current configuration for exact candidate paths. Separate historical logs, inventories, and receipts from executable consumers: an evidence-only mention does not make an inactive runtime operationally required.
5. For each remaining checkout, require no live or unresolved executable consumer, no inbound alternate-object dependency from any active or retained repository, and no unhandled linked-worktree registration. Prefer a clean Git tree; if it is dirty, apply the exact source/patch/untracked/meaningful-ignored preservation and replay procedure in `references/backup-retention-scope-and-redundancy.md` before classifying it as removable. A historical helper reference is releasable only when its exact owning run is demonstrably complete, no current scheduler/process consumes it and recovery-before-replay is documented; do not cancel blocked work or invoke campaigns to prove non-use. `git worktree list` showing a standalone repository as its own primary worktree is descriptive, not a blocker. A linked worktree still needs the native removal workflow and explicit scope for its administrative metadata; raw tree deletion is not equivalent.
6. Pair every retired checkout with all launcher symlinks that resolve inside it. Freeze the tree as `delete_tree` and each launcher as a separate `delete_symlink`; otherwise cleanup leaves misleading dangling rollback commands.
7. Keep the canonical source clone used for fetch/update, the active checkout, the immediate rollback, and their patch/activation receipts outside the target set. Classify all other clean, unreferenced siblings as one cumulative optional-cleanup lot and compute inode-aware recovery before confirmation.

Do not call the lot already deleted merely because a previous cleanup closed successfully. Only exact target absence proves that a sibling checkout was covered.

- **Review required:** second-newest validated backups, closed repair rollback sets, local media/evidence mirrored remotely, update/build dependencies, old reports, old operation backups, package caches, and package-manager autoremove candidates.
- **Protected:** active runtime, minimum rollback, live profile state, institutional Git, current browser revisions, local models, latest validated archives, and unique secure backups.

Do not sum overlapping review roots into one reclaim figure. When a parent root and child candidates are both reported, label the aggregate as non-additive.

For old temporary material, list top-level entries individually, apply an explicit age threshold, exclude current lock files, and require zero process references. Temporary media may still carry evidence value, so keep it separate from purely rebuildable caches.

### 5.1 PostgreSQL test-cluster manifest checks

When freezing generated PostgreSQL data directories for deletion:

- Identify a cluster root by `PG_VERSION` **plus sibling `base/` and `global/` directories**, and do not count descendants again. PostgreSQL also writes `PG_VERSION` inside `base/<database_oid>/`; those are database subdirectories, not independent clusters. Compare complete cluster trees for redundancy: identical template databases or individual files do not establish that two complete test clusters are interchangeable.

1. Prune every directory containing `PG_VERSION` from external-reference content scans, then search code, tests, reports, retained evidence, service definitions, crons, scripts and checkpoints for each candidate's exact absolute path or basename. Reading cluster binaries wastes time and can create meaningless matches; the cluster itself is not evidence of an outside consumer.
2. Treat `postmaster.pid` as a signal to inspect, not proof of a live server. Parse its first line and block only when a positive PID exists in `/proc` and its command line resolves to the candidate; record negative sentinels and stale PID files in the manifest without calling them active use. Still scan `/proc` `cmdline`, `cwd`, `exe` and file descriptors independently.
3. Store nanosecond mtimes directly in new manifests. When an older audit stored floating-point epoch seconds, compare the converted value with a small precision tolerance instead of exact integer equality; binary-float conversion can otherwise report every unchanged target as drift. The freshly computed metadata fingerprint remains the deletion-time authority.
4. Keep evidence-linked clusters and the required compatible family source in the explicit retained set. Freeze only the exact unreferenced remainder, and fail closed if target count, retained count or any dependency gate differs from the reviewed classification.

### Bounded reference census for generated test state

- Persist the discovery index before reading a large reference corpus; use compressed indexes, positive-hit records and compact covered-index intervals instead of a large empty completion record for every source. Count every analysis-created intermediate, including failed-pass residue, in the net storage budget and keep its later compact/disposal gate explicit.
- Bound each foreground scan batch by an internal deadline shorter than tool transport, resume only its persisted uncovered suffix and verify the final covered index set programmatically. For many path tokens, factor a single matcher by shared prefixes and test it against real positive sources plus directory-boundary negatives: `stage-db` must not match `stage-db-v7`. Never silently reuse an incomplete timed-out pass as a full negative-reference proof.
- Resolve module-relative selectors in the owning run directory as well as global literals: `new URL('./stage-db-v7', import.meta.url)` need not repeat the run ID anywhere in its body. Pair source location with the exact leaf and directory boundaries; never let `stage-db` match `stage-db-v7`, and do not call a file globally unreferenced until this owner-local pass is complete. Distinguish immutable filesystem inventory mentions from an actual consumer or a named QA evidence provider.
- Separate exact paths/unique leaves from weaker owning-run-ID plus basename/context hits; inspect the actual code before calling either an active consumer. A default data path or an existing-directory reopening helper is a dependency; a test factory using a fresh UUID does not reopen every historical member of that family. Check retained `.log`/stdout/stderr evidence separately when the main text whitelist omits them, and never scan PostgreSQL pages as reference text.
- Scope the immutable code census to actual application sources, possible DB readers and relevant individual job definitions, while scanning all current executable/config surfaces for new exact target selectors. A byte-for-byte lock over every other agent's changing helper couples an unrelated operation to this local gate and can never converge. Test unrelated code/job changes as non-blocking, but relevant source changes, new DB readers and exact target selectors as blocking; ignore execution counters only. Once a verifier is frozen, do not edit it to force a pass: preserve its failed/unexecuted receipt, derive an explicitly new verifier/manifest, prove all selected readers match the already reviewed baseline and rerun all gates before presenting the new Critical confirmation.
- Reconcile disappeared cron outputs as declared transient/unavailable sources, not accessible-file read success or an automatically attributed anomaly. Preserve the original failure and current absence, pin the readable executable/configuration census, and distinguish scheduler definitions from advancing execution counters.
- For a nested completed candidate, preserve the evidence-linked compatible member of each consumed family and every prior explicit hold before selecting only the independently unreferenced remainder. Report this as retirement of saved test state when exact byte recovery is not retained; new factory runs are not proof of restoring that historical state. A mock-only deletion-order test must label all destructive OS calls as mocked and never be reported as real deletion.

### 5.2 Persistent browser sessions are not browser caches

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

### 5.3 Drive-backed local media must close by lineage

For creative/media staging, prove remote existence through the active approved storage backend and the canonical Service Account—not filename coincidence, an old success message or a permanently assumed Shared-Drive location.

1. Read the live storage binding and resolve the exact logical source ID, provider binary ID, stock/shortcut ID and approved archive root. For Shared-Drive storage, validate the expected `driveId`; for an approved owner-account archive, validate the pinned owner, root ancestry and logical/provider/stock contract instead of rejecting a valid My Drive object for lacking `driveId`.
2. Require a live non-trashed provider ID, exact size/MD5 and recorded SHA-256 parity. Exercise the existing native media resolver with its mapping, ACK, stock, access and ancestry guards intact; stream and hash the full provider binary when proving owner-archive recovery. Keep this audit GET-only; do not move media, alter permissions, regenerate creative jobs or change campaign eligibility to make a read pass.
3. Join each local raw/readback copy to a verified remote record by exact bytes and lineage, then deduplicate and count native IDs separately from local paths. Before approved deletion, refresh the native resolver/metadata and compare with the already-preserved full-stream proof; afterward, independently read back representative retained providers without reusing the pre-action metadata cache. Empty abandoned execution directories may be classified separately as stale temporary material.
4. Derived frames/contact sheets may be deleted with their local batch only when their parent media has exact remote closure and no independent evidentiary retention applies.
5. If legacy IDs are missing after a migration, exclude that local root from the destructive manifest. Do not infer a replacement by name alone.
6. A future upload workflow may remove transient local media immediately after this readback, but must preserve a compact provenance manifest containing source ID, destination ID, filename, size, checksum, and status.

#### Historical inventories are not automatically live media consumers

Classify references by behavior before declaring a duplicate local binary protected. A retained JSON inventory, upload receipt or comparison record mentioning a filename is evidence, not proof that a current executable opens that local path. Preserve those original records unchanged, create a compact exact local-path → logical-ID/provider-ID/stock-ID/hash recovery index outside every target, and exercise the real native archive resolver, ACK/ancestry/access guards and full provider stream. Count every unique remote ID programmatically and retain unmatched files or unfinished owning tasks. Disclose that physical local pathnames disappear while the material and provenance remain remotely recoverable; never equate this with deleting conversations, browser state or the historical records themselves. If a live executable, rendered local report or active task still depends on the physical path, preserve it until that consumer is migrated.

For large read-only archive audits, append bounded batches to a durable ledger, cache only identical GET/metadata/ACK observations in process memory, and keep the native resolver authoritative. Treat helper status `0` as a transport exception family, not an HTTP rejection or absent object. Retry the exact non-mutating native read with bounded backoff, preserve the initial failure separately and aggregate the latest independently validated result per native ID; never silently double-count the retry or bypass credential/trust gates.

## 6. Housekeeping dry-run pitfalls

`npm cache verify` is **not** a read-only verification command: npm may garbage-collect stale cache objects while validating the cache. During discovery, size npm caches with metadata-only filesystem reads and use non-mutating listings where needed. Run `npm cache verify` only inside an authorized cache-cleanup scope, capture its reported garbage-collected bytes, and verify the post-command cache size and filesystem delta before reporting the effect.

With `set -Eeuo pipefail`:

- `producer | head -N` can fail when `head` closes early and the producer receives SIGPIPE. Bound output inside the producer instead, e.g. `awk 'condition && shown < N { print; shown++ }'`.
- `find /optional/root ... 2>/dev/null` still returns nonzero when the root is absent. Guard optional roots with `[[ -d "$root" ]]` in both dry-run and live paths.

A dry-run is accepted only when it exits zero, prints its final summary, and a mutation check proves every named candidate still exists.

## 7. Authorization boundary

A user's confirmation applies only to the frozen target-set hash they were shown. Approval given before a new exact manifest exists authorizes classification and manifest preparation only; show the frozen hash and irreversible current→new state, then obtain the Critical Subset confirmation before deleting. A later whole-VPS scan creates a new scope. Do not remove newly discovered items—even obvious caches—until a new exact manifest and Critical Subset confirmation are obtained.
