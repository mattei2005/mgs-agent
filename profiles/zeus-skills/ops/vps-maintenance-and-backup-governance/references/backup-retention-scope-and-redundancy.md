# Backup Retention Scope and Redundancy Audit

## Goal

Find all material backup/archive storage, explain what existing automation actually governs, and produce deletion candidates that are safe at an exact operational-set boundary.

## 1. Map storage classes without opening secret content

Inventory at first-level set granularity rather than dumping every child path. For each set capture:

- absolute path and type;
- file count and total bytes;
- oldest/newest mtime;
- symlink count and read/stat errors.

Include, when present:

- canonical backup roots and hidden secure backup roots;
- application update reports and profile tarballs;
- staging clones such as `repo`, `verify-repo`, `port`, clean-apply, and smoke checkouts;
- workdir backup folders and curator snapshots;
- report baseline/JSON backups;
- `/var/backups` as a separately protected OS-managed class;
- retired-agent or deactivated archives outside normal backup roots;
- offsite backup state separately from local disk usage.

Avoid double counting nested sets: either total a root or its children, not both in the grand total.

### Deep classification and bounded duplicate proof

Use this branch when substantial usage remains after a narrow cleanup or when directory totals mix test databases, dumps, inputs and evidence.

1. Refresh `df` block/inode usage and mount-bounded `du` for the largest roots. Descend into the dominant producer before recommending cache deletion or more storage; a completed cleanup receipt describes its exact lot, not the necessity of everything left.
2. Classify files without opening application data. Identify a complete PostgreSQL cluster only by `PG_VERSION` together with sibling `base/` and `global/`; prune nested database directories from cluster discovery so one cluster is not counted repeatedly. Separate cluster trees, database dumps/SQL, compressed and uncompressed archives, JSON/source material, dependencies and compact receipts. Resolve the production host independently before labeling local copies as tests; do not start old databases merely to classify disk usage.
3. Sum mutually exclusive classes with an inode-aware walk and retain per-set counts, allocated bytes, newest descendant time and errors. Keep a parent workflow's total as context only: its dumps and clusters are components, not extra savings to add to the parent.
4. Find exact duplicates cheaply: select large regular files, group by logical size, and run external `sha256sum` only for size groups with multiple candidates. Group matching digests by distinct `(st_dev, st_ino)` so existing hardlinks are not mistaken for separate physical copies. Save detailed mappings in evidence and return only file/group counts and bytes.
5. Retain at least one eligible copy per digest group when estimating duplicate potential. Exclude blocks still held by external hardlinks; a conservative early estimate may credit only single-link candidate files. Split the potential by file class and state that it is already contained in the corresponding root/class totals. Recheck metadata stability and hashes when freezing the actual lot because an observation-time digest is not deletion-time validation.
6. Check process `cmdline`, `cwd`, `exe` and open descriptors against exact candidate roots. Distinguish a worker using an operational parent directory from a process consuming an isolated child database. Preserve parent state and live workers; absence of child references does not settle family/latest selectors, source inputs, immutable evidence coupling or recovery dependencies.
7. Treat byte identity as evidence of content duplication, not permission to remove a pathname. Choose retained copies by recovery and consumer requirements, not newest mtime alone; verify every proposed removal's references and evidence contract before an exact destructive manifest. For unique old test state, separate an explicit retirement decision from a claim of proven deduplication and disclose what historical recovery is lost.
8. Inspect the actual producers and cleanup policy alongside the dry-run. Verify whether name patterns and roots cover the dominant dumps, JSON, test clusters and archives. Distinguish installed prevention of recursive source copying from retirement of existing test state and recurring pre-import backups: one does not establish the other. Close with separate outcomes for classification, approved disposal and future accumulation prevention.

### Repeated pre-import database dumps

Use this bounded path when scheduled retries leave separate local copies of the same pre-import database backup:

1. Resolve the actual producer, its interpreter and remote backup helper from the live scheduler before importing its code; reuse that execution environment rather than guessing a Python environment or installing packages for the audit. Inspect the helper for side effects and invoke only its read-only transport operation.
2. Group regular dump files by size, then compare SHA-256 within repeated-size groups. Deduplicate inode identities and select a retained representative per digest according to recovery consumers. Record excess copies as duplicate potential, not approved reclaim.
3. Read the completed operation receipts to join each proposed local removal to its exact retained local file and remote backup path, size and digest. Through the canonical transport, recheck remote `sha256sum`/size and use the producer's `pg_restore --list` command to prove catalogue readability. Do not describe catalogue listing as a materialized restore.
4. Preserve source attachments, import/idempotency state and compact immutable receipts. Confirm that future runs create new execution directories and do not reopen a selected historical local dump; check pending recovery jobs, exact executable references, processes and checksum-coupled evidence. A receipt's historical `local_copy` field is not a sufficient recovery route after removal: retain an explicit mapping to the surviving local or remote copy without rewriting the original receipt.
5. Freeze only the individual excess dump files, never their parent run directories. Apply the exact-manifest/validator/confirmation workflow; revalidate retained hashes and remote recovery before execution, then verify target absence and measure the actual `df` delta.
6. Keep this one-time duplicate-copy removal separate from changing future import backup behavior or retention. Identical backups already present at the remote producer can still be copied repeatedly by the local consumer; producer reuse alone does not prove that local accumulation is prevented.

## 2. Prove the policy scope

Read the housekeeping and safety scripts before interpreting their output. Record:

- scan roots;
- filename regex/glob;
- retention period;
- preserve-latest logic;
- special archive handling;
- empty-directory behavior;
- notification/reporting behavior.

Then run dry-run with a temporary log. A no-op means only that no object matched the implemented rules. Explicitly search for coverage gaps:

- legacy archive names not matching the current glob;
- whole backup directories rather than marked files;
- transaction backups without a retention rule;
- report/staging clones;
- safety archives governed by a different retention policy;
- system backups and protected archives.

Do not say “housekeeping is healthy” from cron presence or a successful no-op alone.

### 2.1 Dry-run confiável sob `set -euo pipefail`

O dry-run é um gate operacional e precisa terminar `rc=0` sem mutação. Dois padrões comuns produzem falso erro mesmo quando a classificação está correta:

- `producer | head -N | consumer` sob `pipefail`: `head` fecha cedo, o produtor recebe SIGPIPE e o script sai não-zero. Limite no próprio produtor (por exemplo, contador no `awk`) para que ele consuma a entrada inteira e encerre normalmente.
- `find "$OPTIONAL_ROOT" ... | wc -l` quando a raiz opcional não existe: com `pipefail`, o `find` retorna erro e aborta o wrapper. Teste `[[ -d "$OPTIONAL_ROOT" ]]` antes de contar ou remover.

Depois de corrigir, valide `bash -n`, execute com log temporário, confirme o resumo esperado e faça readback de que cada candidato ainda existe. Um wrapper mutante que retorna não-zero sempre exige readback antes de repetir, pois a falha pode ter ocorrido depois de algum efeito.

## 3. Use three deletion queues

### A. Eligible under current policy

Requirements:

- exact path or operational set identified;
- current policy clearly covers it, or it is a redundant legacy equivalent of a covered class;
- retained recovery artifacts validated;
- no active registered worktree/dependency;
- exact bytes calculated immediately before execution.

### B. Eligible only after policy change

Examples: shortening safety retention, changing keep-latest count, or introducing retention for DTR/report transaction directories. Keep these bytes out of the “safe now” total. A retention change is a separate script/config decision with its own authorization, fixtures, inventory, audit, and reporting.

#### Interpreting “keep only the latest backup”

Treat “latest” per independent recovery class unless the owner explicitly says otherwise. A profile/update archive and an operational safety snapshot protect different failure modes; one does not replace the other.

For a latest-one local policy:

1. Retain the newest validated profile/update archive and the newest validated safety archive—one per class.
2. Keep the active runtime rollback and offsite disaster-recovery retention separate; do not silently reduce either.
3. Resolve the retained recovery set from the latest validated activation receipt rather than selecting the newest directory by mtime. If it combines a control-plane tar archive with native per-profile snapshots, verify the archive's historical checksum and full listing, each snapshot manifest's recorded checksum and file sizes, and read-only SQLite integrity for every retained database. State exactly what this set covers; do not claim it preserves every file from an older full-profile archive. Validate a safety archive against its own manifest format: some manifests store `sha256=` and `size_bytes=` metadata plus an archive listing rather than `sha256sum -c` rows.
4. When a recurring retention change is explicitly in scope, change every producer and its operational description together. A common split is a housekeeping script for update archives and a separate safety-backup script for safety snapshots; updating only one leaves policy drift. For a one-time deletion request, freeze only the existing targets and report the remaining producer gap without silently installing future deletion behavior.
5. Put older archives and companion manifests in the same exact destructive manifest, with no parent/report-root overlap.
6. Report large `reports/` totals carefully: profile tarballs may dominate the root, so explain that deleting an old archive is not equivalent to deleting operational reports or logs.

The policy change and the immediate deletion remain Critical Subset operations and must be double-confirmed as one frozen operation set or as separately hashed sets.

### C. Protected or unique

Includes:

- latest/canonical archives;
- objects still inside rollback windows;
- singletons protected by preserve-latest rules;
- OS-managed backups;
- archives the user explicitly retained for future reference;
- snapshots containing unique databases, logs, state, or credentials metadata.

### 3.1 Freeze a destructive manifest for whole-VPS sweeps

A request to “scan the whole VPS and remove old/unimportant files” may include backups, caches, temporary test trees, staging clones, state snapshots, and package archives. Discovery authorization is not deletion authorization. Before the Critical Subset double-confirmation:

1. Scan metadata only across the whole filesystem while excluding virtual filesystems; do not open secret content. Classify backup-like objects separately from rebuildable caches, active runtime data, OS-managed state, and operational rollback sets.
2. Build an exact target list with no globs, broad name searches, parent/child overlap, symlink traversal, or mount crossing. Record each target's type, file count, logical bytes, allocated bytes, oldest/newest mtime, and any stat errors.
3. Use allocated bytes for the projected free-space result. Preserve logical bytes too, because sparse files, directory overhead, and concurrent writes can make the two figures differ.
4. Record a protected/retained set explicitly: active runtime, frozen target, current rollback runtime, fresh activation backup, latest validated archives, audit/log/report evidence, Git repositories, live profile state, operational browser/model assets, and recent owner-domain backups outside the requested retention change.
5. Validate every archive that will remain and bind the offsite replacement proof to the exact retained remote generation: record its remote file ID, size and hashes, then require an isolated restore of that same object (or a later object that fully supersedes it). A healthy backup uploaded after the most recent restore test is not restore-proven merely because the older test remains inside SLA; keep the last local full archive protected until the exact replacement has passed restore.
6. Add execution preconditions: primary maintenance has already reached `activated_validated`; final REPORT-INFRA GET readback passed; no process uses a target path; all targets still match the confirmed set immediately before deletion; rollback artifacts named as retained still exist.
7. Canonicalize the exact path/action list and hash it. The confirmation must cite this target-set hash, entry/file counts, allocated bytes, current→projected disk use, retained set, and irreversible effect. Any path, size, or scope change— including a reduction—requires a newly frozen manifest and fresh confirmation.

A housekeeping dry-run that returns no candidates proves only that current filename/retention rules found nothing. It does not authorize an owner override such as “keep only the latest two” or deletion of unique snapshots; those remain Queue B/C until the exact manifest is double-confirmed.

If cleanup is sequenced after an update or cutover, do not delete first. Complete and independently validate the primary maintenance, preserve its minimum rollback route, and only then execute the already confirmed manifest.

### 3.2 Preflight the closure validator before deletion

Freeze and exercise the **same** validator that will close the cleanup before crossing the destructive boundary:

1. Give it a read-only/preflight mode that verifies current JSON keys, status enums, command syntax, service names, launcher/profile scope, retained paths, and evidence locations while skipping only the future `target absent` assertion.
2. Derive keys and accepted status values from the current canonical schema or a live bounded readback; never hardcode names or success literals from memory. A guessed schema can leave a correctly executed deletion stuck behind a validator that was never runnable.
3. Hash the validator beside the destructive manifest before confirmation. At execution, verify both hashes, run preflight again, write the audit-start boundary, delete each exact target once, and run the already-proven post-action mode.
4. Keep irreversible acceptance independent from ancillary governance parsing: first prove exact target absence, retained recovery paths, observed `df` delta, runtime/services and real profile smokes; then update inventory/checkpoints/reporting. If an ancillary parser fails after deletion, preserve the deletion result and classify **governance closure** as blocked—never retry `rm` or describe the filesystem action as uncertain.
5. Make profile scope explicit in smokes. A default/root probe and named production profiles are separate checks; environment inheritance must not let one profile masquerade as another.

## 4. Validate what remains

### Interrupted encrypted restore: verified input reuse and isolated replay

Use this sequence for a large remote encrypted backup whose isolated drill is interrupted by transport or execution limits. Treat recovery of the drill and eventual disposal of its workspace as separate outcomes.

1. **Bind the exact remote generation.** Freeze its file ID, size, native hashes and managed metadata. For an ownership/location migration, also capture the first independently verified post-move timestamp, owner/ACL, destination ancestry and preserved source staging. Check the current parser before invocation: `python3 scripts/mgs-offsite-backup.py restore-test --help`; the basic drill is `python3 scripts/mgs-offsite-backup.py restore-test --remote-id EXACT_ID`. Do not add flags copied from another CLI.
2. **Budget the complete workspace lifecycle.** Measure free space and use manifests/archive headers to estimate ciphertext, decrypted outer container, extracted component archives, profile/application imports and database work separately. Include retained interrupted trees and any new replay destination. If expansion is unknown, inspect the decrypted archive headers before extraction rather than assuming its compressed size bounds the restore. Keep the work under the active profile scratch with private permissions; plaintext recovery data and imported keyrings are sensitive even when the remote backup is encrypted.
3. **Select execution before the long stage.** Compare previous drill duration with the actual transport window. When the drill can outlive it, use a silent tracked process, keep output in a bounded/private log and consume its final result manually before delivery. A larger requested timeout is not evidence that the surrounding transport will honor it. A wait-window expiry while the process remains running is not a restore failure and must not trigger a second writer.
4. **Reconcile interruption before retry.** Inspect the exact process tree, restore-state timestamps, workspace contents, import markers and current free space. Do not promote the previous PASS, assume the process died, or start another complete download. Preserve partially completed outputs and distinguish the stages proven by control flow from checks that still need a new result.
5. **Prove that preserved inputs are reusable.** Recompute the ciphertext's full size/MD5/SHA-256 against the frozen remote object. To reuse a decrypted bundle without replacing it, decrypt the same ciphertext to a hash stream through the existing protected test keyring and compare that digest with the preserved bundle's SHA-256; require successful decryption as well as digest equality. For example, use a pipeline with `set -o pipefail`, `gpg --homedir "$TEST_GNUPGHOME" --batch --decrypt "$CIPHER"` and `sha256sum`, keeping diagnostics private. Compare every preserved extracted component to its corresponding archive member, then apply the canonical component size/hash checks. File presence or archive listing alone is not content equivalence.
6. **Reuse validators, not an invented success receipt.** Keep the canonical restore checks as the source of acceptance. A bounded resume adapter may replace only proven-complete acquisition/extraction steps; bind it to the current script hash, require each replacement anchor to match exactly once, preserve both versions and fail closed on code drift. Do not patch production code merely to skip failed checks. If completed import results were lost, run fresh isolated imports into a separately budgeted destination rather than fabricating their results from marker presence or overwriting the failed evidence. Set each child import's isolated `HERMES_HOME` and remove conflicting inherited profile selection only in that child execution environment.
7. **Read back a new acceptance result.** Require all canonical checks to return actual results, verify the exact remote ID/hash again, and record the resume mode and reused-input evidence. For a move pilot, require the new PASS to be later than its first post-move verification. Separate PostgreSQL dump listing from actual database materialization; an unrequested materialized database or production restore is not part of the drill. Retain the compact receipt outside the temporary workspace.
8. **Close execution, then classify disposal.** Consume the process exit and ensure no restore writer remains. Stop only the test-owned helper daemon after its final use. Account for original and replay workspaces together, label them as artifacts created by the operation, and apply the existing exact-target cleanup/confirmation workflow rather than deleting preserved failure evidence implicitly. Keep encrypted originals, production profiles, source staging and compact validation evidence outside the deletion scope. A recovered drill does not itself prove automatic archive recurrence or authorize retention changes.

For large cleanup inventories, build the detailed per-file ledger outside the auto-versioned tree first. Keep a compact canonical index with target/counts/allocated bytes, semantic target fingerprint, compressed-ledger path and both compressed/expanded content hashes. Verify decompression reproduces the exact original ledger before superseding a bulky JSON representation; compression must not change the target set or discard rollback evidence.

### Bounded application-test trees: code recovery is not database recovery

For a fixed list of application test/staging directories, use one result row per exact target and finish with the same target count as the input manifest:

1. Collect metadata without following symlinks or crossing devices. Classify database clusters and dumps separately from source clones, reports and configuration; extension counts alone miss PostgreSQL cluster files with numeric names.
2. Resolve the review-window start from the validated release/task closure in audit or inventory, using the target's own authority/release identity. Never use a loose substring match against another release or substitute descendant mtime for closure; otherwise a newer related release can reset the wrong target's age.
3. Check process `cwd`/`exe`/`fd`, resolved service commands, schedulers, active control-plane sources and inbound symlinks. Report zero matches as `no references detected in the checked sources`, not as proof that the tree contains no unique state.
4. Verify retained code versions against the publication manifest with shell-generated `sha256sum`. Search current canonical files, then `git log --format=%H -- <path>` and `git show <commit>:<path>`, then retained release-journal backups outside the target. Match the journal's recorded hash and hash the actual backup; a retained `.before` file from a later release can preserve the exact earlier published version missing from the current checkout. Record source path/commit and unmatched versions without emitting financial values.
5. Verify that original inputs, schema, stage driver and compact test/publication evidence remain outside the deletion target. Keep this as **code/input recovery evidence** only: matching source hashes and retained input files do not certify the full state of an old test database.
6. Establish database-state redundancy separately through existing exact restore/reconstruction or comparison evidence. If further isolated validation is needed and authorized, validate the exact retained inputs and version in isolation; never boot the old cluster against production or expose financial rows merely to justify cleanup. If that proof is outside the approved review scope or remains absent, preserve the database tree and state the unproven predicate explicitly.
7. Aggregate classification and bytes programmatically. If the approved review permits preservation and no target passes every disposal predicate, close with all targets preserved, zero eligible reclaim, zero deletion and no destructive confirmation pending. Update checkpoints and the active result pointer so earlier metadata-only manifests remain historical rather than an apparently open cleanup request.

### Conditional dashboard-safe cleanup: tests and imported-report material

Use this sequence when the owner permits local cleanup provided the live dashboard and its saved data remain intact:

1. Resolve the live application, database host, data directory, service commands and scheduler consumers before bulk hashing. Capture read-only service health and deterministic aggregate fingerprints of the protected financial tables; keep row contents and credentials out of output. A different host is strong isolation evidence, but still check whether local inputs or recovery paths are consumed by production jobs.
2. Split each large `candidate/private` or `stage/private` tree into complete test clusters, test recovery archives, source/fixture JSON, code, and compact release evidence. Prefer exact disposable cluster/archive children over the entire parent so retained inputs and provenance are not removed merely to reclaim database blocks. Reconcile current task closure and keep any still-consumed compatible test family outside the lot.
3. Record file-comparison results as identical to the checked source, different, or missing at the checked source. A missing source path is not proof of globally unique content; identical template files are not proof of whole-cluster redundancy. Do not spend a full-tree content comparison on every copy when the decision instead requires explicit retirement of old test state plus proof that production and retained recovery are independent.
4. Treat permission to discard imported e-mail material as permission for the named local source attachments and pre-import dumps, not SQL deletion of already imported facts or mailbox deletion. Preserve compact result/provenance receipts and durable import/idempotency state; check unresolved recovery jobs before selecting raw files. Explain that subsequent imports may generate new copies unless producer changes are separately authorized.
5. If the owner elects to abandon historical test state rather than prove exact reconstruction, describe that as an irreversible retirement decision, not deduplication. Show the exact classes and bytes lost, protected production/source/recovery set, and remaining uncertainty before Critical confirmation; otherwise retain unique or unproven state under the existing review policy.
6. Freeze one non-overlapping manifest with per-class totals, inode-aware reclaim, retained recovery and the tested verifier hash. Present projected disk use separately from observed savings and keep the task at `awaiting_critical_confirmation` until the exact lot is confirmed. After authorized deletion, compare protected production fingerprints, validate exact absence and retained recovery, and measure the real `df` delta before closing.

### Live-profile rollback archive before a runtime cutover

Do not blindly compress every live profile subtree when the runtime update changes only the Hermes code and control plane. Browser profiles, work/artifact trees, state-snapshot stores, caches, LSP environments and open sockets can turn a small rollback archive into a multi-gigabyte moving target; interruption may leave a large file that exists but ends in gzip/tar EOF.

1. Place the archive under the protected backup root with directory mode `0700` and archive/manifest mode `0600`; never print `.env`, auth or credential content.
2. Build an explicit control-plane allowlist for each active profile: `.env`, `auth.json`, `config.yaml`, `SOUL.md`, profile/Honcho/channel metadata, `cron`, `skills`, `memories`, `state`, `gateway`, `platforms`, `scripts`, `hooks` and profile plugins when present. Preserve bulky browser/model/work/session assets in place or through their own recovery class unless the planned mutation touches them.
3. Enumerate SQLite files recursively inside the control-plane allowlist before archiving, not only top-level `state.db`: cron execution/delivery/notepad ledgers can be nested. Snapshot each live database through SQLite's backup API, require snapshot `PRAGMA integrity_check=ok`, exclude live WAL/SHM companions from tar, and record preserved zero-byte noncanonical files separately. If a valid first archive omitted a nested ledger, preserve it and create a separately validated supplemental archive; freeze both as one recovery set rather than silently claiming complete coverage or rewriting historical checksum evidence.
4. Use `tar --warning=no-file-changed --ignore-failed-read` over the explicit existing paths so live socket entries are skipped without widening the archive; a warning is not success by itself.
5. Require all four gates before cutover: `gzip -t`, a full `tar -tzf`, shell-generated `sha256sum`, and `sha256sum -c` readback. Archive presence or a plausible byte size proves nothing.
6. If any integrity gate reports truncated gzip or tar EOF, classify the object as an invalid partial, preserve it until a separately confirmed exact deletion manifest, and create a new validated successor. Never use the partial as rollback evidence and never delete it incidentally while retrying the backup.

Before deleting an old tar archive, validate every archive that will remain:

```bash
tar -tzf /exact/retained/archive.tar.gz >/dev/null
```

Match the validation criterion to the retained artifact's purpose. A **pre-repair rollback snapshot may intentionally preserve the defect being repaired**; do not require it to pass the post-repair integrity gate. Instead:

1. read its manifest/purpose and expected pre-repair signature;
2. verify every recorded file hash and byte count;
3. verify unaffected invariants such as foreign keys or schema readability;
4. confirm that the known defect signature is exactly the expected one, with no additional corruption;
5. validate the repaired live database separately with the full post-repair integrity gate.

If an over-strict precondition aborts before deletion, confirm from audit and filesystem readback that no side effect occurred, correct only the validation model, then rerun the exact frozen target. Never interpret an expected pre-repair defect as evidence that the rollback artifact is unusable, and never retry a destructive wrapper without first checking whether the target already changed.

Preserve compact evidence—patches, hashes, manifests, final reports, and logs—when only bulky source clones or node_modules-like staging are redundant.

For update evidence directories that contain nested `verify-checkout*` trees, target only those nested trees rather than the parent evidence directory. Before classifying them as removable:

1. prove no process, service, cron or script resolves into the tree;
2. prove the tree is not a registered worktree;
3. hash the patch/result reproduced there and require an identical canonical copy outside the target;
4. retain the parent verification text, patch checksum, logs and final result;
5. compute inode-aware reclaim for the exact nested trees, not the apparent size of the parent.

### Reconstruct modified code copies before retiring them

Use this branch for obsolete nested code reproductions inside an update-evidence root, not for live runtimes or historical profile databases. A dirty checkout need not be discarded blindly or preserved in full when its exact code can be recovered compactly.

1. Inventory each copy with `git rev-parse HEAD`, `git diff --name-only HEAD -z`, `git ls-files --others --exclude-standard -z` and `git ls-files --others --ignored --exclude-standard -z`. Count modified, untracked and ignored files separately; porcelain status-line count is not the modified-file count. Inspect ignored paths by class because ignored test measurements or fingerprints can carry evidence even when bytecode/cache files are reproducible.
2. Preserve `git diff --binary HEAD` outside every deletion target. Archive every non-ignored untracked file with relative paths and no symlink traversal; preserve meaningful ignored evidence separately. Record the base commit and externally computed SHA-256 values for the patch, archive and preserved evidence. Keep parent reports and activation/checksum evidence outside the lot.
3. Prove Git recovery from repositories that will remain. Enumerate `git for-each-ref --format=%(objectname)` plus detached HEAD, verify required commits in retained repositories, and exercise `git -C RETAINED archive --format=tar BASE_COMMIT` with output discarded and exit status checked. `git cat-file -e COMMIT^{commit}` alone proves only the commit object, not readable trees and file blobs.
4. Reconstruct the changed paths in a capacity-gated scratch tree from the base commit. Run `git apply --check`, apply the saved binary patch, restore the untracked archive and compare every reconstructed file with the candidate using external SHA-256. Record checked counts and mismatches without printing source contents. Do not label code replay as database-state recovery.
5. Complete process, service, scheduler, executable-consumer, inbound-alternate and worktree checks before freezing the lot. Preserve any ambiguous dependency. Run all Git probes before the final metadata freeze because status/worktree inspection can refresh Git metadata.
6. Freeze the exact nested trees in two sorted, relative-path-keyed metadata passes. Compute reclaim across the complete lot with inode-aware hardlink closure, seal the replay proofs and the same non-mutating verifier used for execution, and request the existing Critical confirmation for that exact lot. Stop before deletion if reconstruction, dependency or fingerprint checks fail.
7. Store full ref maps, file hashes, schemas and per-path comparisons in evidence artifacts. Return only per-copy counts, preservation booleans, unmatched counts, bytes and the next gate; hundreds of ref-to-repository mappings or repeated full SQLite schemas obscure the disposal decision.

For Git staging paths:

```bash
git -C /path/to/repo worktree list --porcelain
git -C /path/to/repo worktree prune --dry-run --verbose
```

A registered worktree must be removed through `git worktree remove`; stale metadata may be pruned; an unregistered directory still requires explicit deletion scope. Treat quarantined virtualenvs separately from ordinary archives: package managers may hardlink most files to a shared cache, so a gigabyte-looking tree can release only a small fraction. Group files by `(st_dev, st_ino)` and credit blocks only when every `st_nlink` entry is inside the confirmed target set.

## 5. Retired-agent archives: integrity is not redundancy

First validate the canonical archive manifest from the archive root:

```bash
sha256sum -c manifests/final-files.sha256
```

Reduce output to counts: expected lines, `OK`, failures, and return code. Do not publish filenames containing sensitive context unless needed.

Then compare the candidate snapshot's file-content hashes against the canonical manifest hash set. Report:

- matched files and bytes;
- unmatched files and bytes;
- high-level unmatched classes such as state DB, logs, config, or manifests.

If unmatched content exists, do not call the snapshot fully redundant. Either preserve it, or—under separate authorization—promote required unique content into the frozen archive, regenerate the manifest, verify every entry, and only then delete the old snapshot.

### 5.1 Explicit retirement override

The owner may explicitly decide that a retired agent's unique state is no longer required. Treat that as an override of the protection classification, not as proof of redundancy:

1. disclose unmatched content by high-level class and exact bytes;
2. define the deletion scope at dedicated archive/backup-root boundaries;
3. explicitly state that mixed/shared backups, Git history, audit logs, and shared references remain outside scope;
4. request the Critical Subset double-confirmation with exact roots, target/file counts, bytes, expected disk result, and irreversible loss;
5. immediately before execution, verify all targets still exist under allowed roots, are not symlinks or mounts, and still match the confirmed totals;
6. use an exact target list—never a broad name search or wildcard—and write an audit start boundary before the first removal plus a completion/partial-failure boundary afterward.

Do not surgically remove retired-agent filenames from mixed backup sets merely because their names match the agent. That can corrupt backup-set consistency and silently widen the user's scope.

## 6. Calculate and verify disk impact

Before action:

- sum only Queue A for the immediate reclaim number;
- calculate projected filesystem usage from exact byte totals;
- show Queue B separately as optional policy savings.

After authorized action:

- verify every target is absent;
- verify retained archives still exist and re-run their integrity checks;
- verify the successor service/agent is active, failed units are zero, and no new critical log boundary appeared;
- re-run disk measurement;
- report logical file bytes removed separately from the filesystem free-space delta, because allocation overhead and concurrent writes can make them differ;
- update the infrastructure inventory with authorization IDs, exact scope, validation readback, and status;
- append audit closure and publish one canonical REPORT-INFRA embed;
- report any partial failure.

## 7. Forecast capacity from real growth, not free space alone

A whole-VPS audit must prove its coverage before saying “the VPS inteira was scanned”:

1. Enumerate mounts with `findmnt`/`df` and scan each persistent filesystem separately. Use same-device traversal for `/`; scan `/boot` and EFI independently when mounted; exclude `/proc`, `/sys`, `/dev`, `/run`, tmpfs, sockets, and foreign mounts by design. Report file/directory counts, stat errors, and every technical exclusion.
2. Count archive-like extensions across the filesystem, but split system/runtime compressed dependencies from actual backup/evidence sets. A large filename count is meaningless unless allocated bytes and the largest operational archives are reported separately.
3. Check suspected temporary environments or staging trees against live process `cwd`/`exe`/open-file references and exact script, cron, and systemd references. “Old mtime” alone does not prove unused.

For disk-life estimates:

1. Recover historical free/used observations from the live monitor’s durable source. If the state file overwrites its previous sample, use retained monitor reports/Discord embeds or audit evidence; do not derive a growth rate from the current `df` alone.
2. Prefer two rates:
   - **raw upper bound** between comparable post-clean baselines;
   - **adjusted recurring rate** after subtracting named one-time artifacts such as a new runtime checkout or full recovery archive.
3. Inspect the producer policy itself. Compute the future retention plateau as roughly `retention window / creation interval × current snapshot size`; a cleanup that leaves two backups can still recreate the disk problem when the policy allows ten.
4. Report days to the warning threshold, critical threshold, and full disk as ranges, not false precision. Show the result both under current retention and under the proposed policy. If there is no real historical series, use explicit rate scenarios and label them as scenarios.
5. Separate **immediate reclaim**, **reclaim after burn-in/retention**, and **future accumulation prevented**. Prevented future bytes are not bytes already freed.

## 8. Reporting format

Select the report by the current question, not by the breadth of the investigation:

- **What can be deleted now:** name only the validated lot, file class/count, approximate reclaim, retained recovery and exact pending confirmation. If other categories are unproven, say that once without presenting their occupied totals as removable space.
- **Requested full audit:** show root/set occupancy, independently validated Queue A reclaim, Queue B policy-dependent potential, Queue C preservation reasons and the producer coverage gap. Keep these quantities distinct and non-additive when roots overlap.
- **Requested plan:** number the actual disposal steps and clearly separate ready lots from further investigation, archiving prerequisites and future retention. Do not bury the immediately actionable answer in a general roadmap.
- **Completed deletion:** lead with verified files removed and observed `df` savings, then current disk/free space and retained-recovery/service checks. State unchanged or unexecuted scope briefly; a completed lot does not close a broader reorganization.

Keep the complete exact path/action list and hashes in the frozen manifest. Present individual paths inline only when needed to identify the user's decision, not thousands of child names. Preserve the exact approval binding and Critical gates without making technical metadata dominate the executive explanation. Never attach a filename dump unless Rodolfo explicitly requests an artifact.
