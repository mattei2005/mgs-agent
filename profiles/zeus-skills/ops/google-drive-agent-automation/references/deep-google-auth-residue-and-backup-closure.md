# Deep Google authentication residue closure

Use this after an MGS Google identity cutover when Rodolfo asks whether anything was left behind. A clean runtime scan is necessary but not sufficient.

## Two closure levels

1. **Operational closure:** no active process, open FD, cron, Hermes job, systemd unit, environment selector, script, config or live skill can select the retired identity.
2. **Retention closure:** one-off work files, temporary controllers, artifacts, archived skills, curator snapshots, local backups and encrypted off-site backups are classified and cannot silently restore the retired method.

Never answer “nothing remains” after scanning only production roots. State whether the claim means operationally clean or literally no retained copy.

## Required audit sequence

1. Scan active runtime first:
   - `/root/mgs-agent/scripts` and `config`;
   - live Zeus/Atena/Ares skill scripts;
   - root crontab, all three Hermes `jobs.json` files, systemd units/timers and `at` queue;
   - `/proc/*/cmdline`, open FDs and relevant process environment selectors.
2. Validate selectors are exactly `service_account`:
   - `ARES_DRIVE_AUTH_MODE`;
   - `MGS_DRIVE_AUTH_PRIMARY`;
   - `MGS_GOOGLE_SHEETS_AUTH_MODE`;
   - `MGS_META_APP_ROLES_GOOGLE_AUTH_MODE`.
3. Scan non-runtime but execution-capable locations:
   - `work/`, `tmp/`, `/tmp`;
   - agent artifacts;
   - `.archive` and `.curator_backups`;
   - local `backups/` trees.
4. Search for actual credential material separately from code references. A strong local credential test is a parsed JSON object containing Google `token_uri`, `refresh_token` and `client_secret`; code fixtures or test strings are not credentials.
5. Query 1Password by exact old title and title-like variants; validate the canonical item is uniquely readable without printing fields.
6. Inspect the disaster-recovery backup include list. If full backups include `.secrets`, every retained full backup created while the old credential file existed must be treated as containing it, even when encrypted.
7. Query retained remote backups by metadata and creation time. Classify quick versus full from `appProperties.mode` when present, but do not rely on it: older objects may have no app properties. Fall back to the canonical tiered name (`mgs-dr-daily-*`, `mgs-dr-weekly-*`, `mgs-dr-monthly-*`) and the backup state/bundle metadata.

## Neutralization rules

- Active consumers: migrate to `/root/mgs-agent/scripts/mgs_google_workspace_auth.py` and reject every alternate selector.
- Dated one-off Python utilities whose business logic is no longer canonical: preserve content but add an early `MGS_GOOGLE_AUTH_RETIRED_GUARD` that exits before side effects. Compile and smoke representative files.
- Reusable shell controllers: replace the selector with `service_account` and run `bash -n`.
- Artifact-local scripts: fail closed before imports or network calls; preserve generated assets/inventories as evidence.
- Archived personal-auth skills: replace operational setup/API entry points with canonical readiness or exit-64 tombstones so restoration cannot revive consent/token setup.
- Historical Git, audit logs and imported threads remain read-only evidence. Do not rewrite history merely to remove words.
- Pre-change backup snapshots may remain immutable evidence, but add an explicit no-restore marker and require migration before reuse.
- Remove bytecode only for affected source files/directories after validation. Do not recursively purge every `__pycache__` below `/tmp`, because temporary virtual environments and unrelated test trees are outside the credential-cleanup scope.

## Off-site backup closure

If encrypted full backups contain the retired credential snapshot:

1. Create a new full backup from the cleaned filesystem.
2. Run an isolated restore test on that exact new remote object.
3. Preserve the clean replacement before proposing deletion of old archives.
4. Permanent deletion of remote backup files is Critical Subset: show names/count, current state, clean replacement and post-delete validation, then obtain Rodolfo’s additional confirmation.
5. After confirmation:
   - re-list and require exactly one live object for each approved target name;
   - separately require exactly one clean replacement object in the canonical Shared Drive;
   - permanently delete only those resolved target IDs and record each HTTP result (Drive normally returns `204`);
   - re-list by exact target names and require count `0` for every deleted object;
   - list all retained full backups and require `precleanup_full_count=0` while the clean replacement count remains `1`;
   - run backup status plus the Drive auth/residue watchdog;
   - update inventory/checkpoint/audit and send REPORT-INFRA.

## Continuous regression guard

The canonical Drive watchdog should also scan active executable/config roots for retired selectors and credential paths. Exclude its own source plus historical/archive/reference trees to avoid self-matches and audit-text false positives. Health is true only when both Service Account access and the residue guard pass.

Expected healthy output includes:

```text
guard=legacy_runtime_clean guard_hits=0
```

## Final reporting contract

Report separately:

- active runtime findings;
- local credential findings;
- neutralized manual/restorable code;
- historical evidence intentionally preserved;
- retained encrypted backups;
- any Critical Subset action still awaiting confirmation.

A task is not fully closed while inventory says complete but a credential-bearing backup deletion is still pending; reopen the checkpoint and status honestly.
