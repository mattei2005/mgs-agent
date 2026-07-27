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
5. Validate every archive that will remain and confirm a current offsite backup plus an isolated restore test before proposing deletion of local state snapshots. Integrity of the replacement must be proven, not assumed from job success.
6. Add execution preconditions: primary maintenance has already reached `activated_validated`; final REPORT-INFRA GET readback passed; no process uses a target path; all targets still match the confirmed set immediately before deletion; rollback artifacts named as retained still exist.
7. Canonicalize the exact path/action list and hash it. The confirmation must cite this target-set hash, entry/file counts, allocated bytes, current→projected disk use, retained set, and irreversible effect. Any path, size, or scope change— including a reduction—requires a newly frozen manifest and fresh confirmation.

A housekeeping dry-run that returns no candidates proves only that current filename/retention rules found nothing. It does not authorize an owner override such as “keep only the latest two” or deletion of unique snapshots; those remain Queue B/C until the exact manifest is double-confirmed.

If cleanup is sequenced after an update or cutover, do not delete first. Complete and independently validate the primary maintenance, preserve its minimum rollback route, and only then execute the already confirmed manifest.

## 4. Validate what remains

Before deleting an old tar archive, validate every archive that will remain:

```bash
tar -tzf /exact/retained/archive.tar.gz >/dev/null
```

Preserve compact evidence—patches, hashes, manifests, final reports, and logs—when only bulky source clones or node_modules-like staging are redundant.

For Git staging paths:

```bash
git -C /path/to/repo worktree list --porcelain
git -C /path/to/repo worktree prune --dry-run --verbose
```

A registered worktree must be removed through `git worktree remove`; stale metadata may be pruned; an unregistered directory still requires explicit deletion scope.

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

Use root/set totals for the complete inventory, then list every deletion target exactly. This keeps Discord readable while preserving complete accounting.

Report:

1. total explicit backup/evidence bytes;
2. separately protected archives and remote backups;
3. Queue A exact paths and reclaim total;
4. projected disk percentage;
5. Queue B policy proposal and additional potential savings;
6. Queue C protected reasons;
7. the automation coverage gap that allowed accumulation.

Never attach a huge filename dump unless Rodolfo explicitly asks for an artifact.
