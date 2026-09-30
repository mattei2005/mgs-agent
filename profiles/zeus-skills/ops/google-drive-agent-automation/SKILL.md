---
name: google-drive-agent-automation
description: "Operate MGS Google Drive and Sheets automation exclusively through the canonical mgs-core-prod Service Account and Shared Drive architecture."
tags: [google-drive, google-sheets, service-account, shared-drive, quota, ares, automation, ops]
related_skills: [discord-ops, hermes-agent-operations]
---

# Google Drive Agent Automation

## Scope

Use this skill for MGS Google Workspace and Search Console automation, diagnostics, inventory, batch operations, canaries and access repair across Zeus, Atena and Ares. Drive/Sheets remain its primary surface; Search Console uses the same canonical Service Account and fail-closed identity rules.

## Canonical production identity

```text
Google Cloud project       mgs-core-prod
Service Account            mgsagent@mgs-core-prod.iam.gserviceaccount.com
1Password item             Google Service Account - MGS Agent
Canonical Shared Drive     MGS-AGENTS / 0AEwt4Ye690ocUk9PVA
Runtime auth mode          service_account
Personal user auth         permanently retired; never a fallback
Shared helper              /root/mgs-agent/scripts/mgs_google_workspace_auth.py
Watchdog                   /root/mgs-agent/scripts/monitor-drive-auth-unified.py
```

MGS production must fail closed if the Service Account is unavailable. Never create, restore, reauthorize or select a personal Google token, local client-secret file, refresh-token file, browser session, or alternate 1Password item as a compatibility path. A future architecture change requires Rodolfo's explicit Critical Subset authorization and a new isolated design; it must not revive retired artifacts.

## Destination rules

```text
Use case                                      Required destination
--------------------------------------------  ---------------------------------------------
New automated file upload                     MGS-AGENTS Shared Drive
Existing operational Sheet in My Drive        Keep ID; share current file with canonical SA
Sheet with Forms/IMPORTRANGE/ID dependencies   Keep location unless migration is proven safe
Ares creative upload                           Shared Drive root with driveId and write caps
Service Account cannot access existing Sheet   Add canonical SA as Editor; do not change auth
```

A Service Account may edit an existing My Drive Sheet that was explicitly shared with it, but new binary/file uploads belong in the Shared Drive because Service Accounts do not have personal storage quota.

## Required preflight

1. Load `/root/mgs-agent/.env` without printing values.
2. Require these selectors:
   - `ARES_DRIVE_AUTH_MODE=service_account`
   - `MGS_DRIVE_AUTH_PRIMARY=service_account`
   - `MGS_GOOGLE_SHEETS_AUTH_MODE=service_account`
   - `MGS_META_APP_ROLES_GOOGLE_AUTH_MODE=service_account`
3. Resolve the 1Password item and validate only non-secret metadata:
   - project ID is `mgs-core-prod`;
   - client email is the canonical Service Account;
   - private key exists;
   - required APIs are enabled.
4. Validate the target on both surfaces:
   - Drive `files.get(...supportsAllDrives=true)`;
   - Sheets `spreadsheets.get` for spreadsheets.
5. For Shared Drive writes, verify the Shared Drive identity with `drives.get`; `files.get` on the root ID may legitimately return a generic folder name such as `Drive`. Use `files.get(...supportsAllDrives=true)` for the root `driveId` and capabilities, then require the relevant `canAddChildren`, `canEdit`, and `canModifyContent` gates on the exact target.
6. For a My Drive Sheet, require exact file-level `canEdit=true`; do not attempt file upload to a My Drive folder.
7. Before a batch, run one bounded canary and restore/clear it.

## Canonical health check

```bash
python3 /root/mgs-agent/scripts/monitor-drive-auth-unified.py --dry-run --force-sa
```

Expected:

```text
drive_auth status=ok primary=service_account sa=root_access_ok guard=legacy_runtime_clean guard_hits=0 sa_checked=1 dry_run=1
```

A generic watchdog pass does not prove a specific consumer. After this check, run the exact blocked consumer or probe its exact Sheet/file ID.

For Search Console API enablement, Service Usage IAM, property access and read-only inspection, use `references/search-console-service-account-access.md`. Treat API enablement and property membership as separate gates; neither proves the other.

## Sheets verification

For DigitalTRChat portfolio page-count refreshes, use `references/dtr-page-count-reconciliation.md`: it defines row-occurrence scope, duplicate switcher-name resolution, immutable backup, numeric-string canary readback, narrow writes and monitor pause/resume closure.

For every cutover or permission change:

1. `spreadsheets.get` must return HTTP 200.
2. Drive metadata must return HTTP 200 and `canEdit=true`.
3. Select a currently blank, unmerged and unprotected cell.
4. Write a unique sentinel with the canonical Service Account.
5. Read it back exactly.
6. Clear/restore the cell in `finally`.
7. Read back the original blank/value.
8. Validate formula/error parity for any affected operational range.

For rolling-window source data joined into an append-only operational Sheet, never use all historical destination names as the sole match-ratio denominator. A legitimate source contraction can make that ratio fall while every live source profile still maps. Keep independent live-source scope bounds (row count, publisher/entity scope and date window), require an absolute matched-row floor, gate primarily on the share of live source identities mapped to the Sheet, and retain historical Sheet density only as telemetry. Read back the exact written range after apply.

Never declare success from Drive visibility alone. Sheets API enablement, file permission and quota-project attribution are separate gates.

### Group-separated inventory Sheets

When building an inventory for Rodolfo whose records belong to named groups, organize the review surface by group instead of stopping at one long flat tab:

1. Keep an overview tab with every record and a summary tab with one row per group unless Rodolfo explicitly asks to replace them.
2. Create one tab per group, containing only that group's records and the safe identifiers needed to reconcile them. Never copy AdsPower remarks, proxy credentials, passwords, tokens, cookies or login material into the Sheet.
3. Derive tab titles deterministically from the group name: replace Google Sheets-forbidden characters `: \\ / ? * [ ]`, collapse line breaks/whitespace, trim to 100 characters, and append a stable numeric suffix after truncation if sanitized names collide. Preserve the exact original group name and ID in the summary, plus the actual tab title used.
4. Add the tabs in source-sorted order with bounded `gridProperties`, a frozen header row and only the required columns; avoid the default 1,000-row × 26-column allocation for a large tab fan-out because unused cells consume the workbook's cell limit.
5. Write values with `RAW` in bounded `values:batchUpdate` batches, then apply filters, readable column widths, wrapping and banding in separate bounded formatting batches. If formatting fails, read back values first and retry only the missing layer.
6. Validate with `values:batchGet` across every group tab, not a sample: require exact rows, unique record IDs, the sum of group counts to equal the source total, summary-to-tab-title parity, and structural readback showing every tab has its filter, banding and frozen header. Sample effective formatting only after all structural gates pass.

### Executive summary, detail parity and next-case handoff

When a cleanup/audit is tracked by visible finding rows or an executive summary, treat that surface as an acceptance criterion rather than an optional presentation layer. Update the detailed evidence tabs **and** the corresponding finding/status/decision/evidence rows in the same operation. Read back both surfaces after the final write; adding technical tabs while leaving the visible summary stale is an incomplete Sheet update even when every underlying cell write succeeded.

When Rodolfo asks for the next case in a Sheet-backed queue:

1. Read the canonical priority and pending tabs live through the Sheets API; do not answer from session history or an earlier exported snapshot.
2. Reconcile the case just completed before selecting the next one. If runtime receipts/checkpoints prove closure but the visible row still says open, update every summary/detail/cleanup/final surface under the existing authorization, then read back exact values and effective colors.
3. Keep the completed row green. Move any vendor-blocked, destructive, legal-review, or otherwise out-of-scope residue to a distinct yellow row with its own decision gate; do not leave the completed case red merely to preserve that residue.
4. Select the next actionable case from the reconciled live state and stated priority/order, excluding resolved rows, validated false positives, and blockers that cannot currently be acted on. Report the exact case ID, label, source tab/row, present evidence counts, and the first safe review step.

### Visual state semantics for resolved findings

Treat labels, colors and tab cues as part of the operational result, not decoration. A closed finding must not remain visually red or appear currently critical merely because its historical severity was P0/P1.

1. Before changing status presentation, read the status values, `effectiveFormat`, `userEnteredFormat` and the sheet's `conditionalFormats`. A conditional rule can override a green user-entered background, so validating only the written format produces a false success.
2. Preserve audit history while making the current state unambiguous: use a current-state-first label such as `RESOLVIDA — histórico crítico`, and rename an ambiguous `Prioridade` header to distinguish current state from historical severity when both share a column.
3. Keep red/yellow conditional rules available for genuinely open P0/P1 rows. For resolved rows, avoid the literal trigger token in the display label or narrow the rule to open-state rows; do not delete a reusable severity rule merely to recolor a closed batch.
4. Apply one representative row as a canary, then read back the cell's **effective** background, foreground, bold state and label before formatting the full bounded range.
5. Use green consistently across the executive summary, finding rows, cleanup/final tabs and any closed-review status columns. Preserve factual/evidence text and historical severity in prose rather than turning the whole report into an undifferentiated success screen.
6. After the batch, read back every changed status label, the effective color of each styled range, the expected row counts and tab colors. A values-only readback is insufficient for a visual-status correction.
7. When closing one authorized finding reveals a separate out-of-scope risk, keep the closed row green and create a distinct yellow/open row for the new risk with its own scope and gate. Do not leave the completed item visually critical or silently absorb the new risk into its authorization.

### Replay-safe report publication

1. Freeze the planned dataset and preserve the original values and tab metadata in an immutable pre-write snapshot; save subsequent attempt snapshots separately so retrying cannot destroy the rollback baseline.
2. Before resuming, read the exact target ranges with `values:batchGet`. Skip cells already equal to this operation's expected output, write only still-authorized missing cells, and stop on unexpected nonblank values rather than overwrite another editor's work. Use `RAW` for audit text so source strings cannot become formulas.
3. Reconcile formatting as well as values. Read existing `conditionalFormats` before adding rules; compare target ranges, conditions and intended formats so a successful retry does not duplicate rules. Remove only duplicates attributable to this operation, in descending rule-index order, preserving user-authored rules.
4. After the last factual qualification and formatting change, read every published range again with `valueRenderOption=UNFORMATTED_VALUE`. Normalize planned `None` to a blank cell and pad only API-omitted trailing empty cells to the planned dimensions; do not coerce identifiers or other string values to make a mismatch disappear. Treat `totalUpdatedCells` only as coarse transport evidence because blank-filled rectangular ranges can make it differ from logical nonblank counts. Require exact full-range values and dimensions, then regenerate the final dataset hashes and verification receipt.
5. Seal the evidence manifest only after the final dataset and receipt are stable. An earlier successful readback does not validate a later correction.

## Shared Drive verification

For the canonical root, validate:

- HTTP 200;
- `driveId` present;
- not trashed;
- `canAddChildren=true`;
- `canEdit=true`;
- `canModifyContent=true`;
- membership role sufficient for the requested operation.

For Ares, preserve raw assets in the canonical Drive lineage, upload only cleaned/final copies, and record source ID, destination ID, filename and operation status. Never use the same lineage twice as independent candidates.

Local creative media is transient after successful upload. Remove the VPS copy only after a live `files.get(...supportsAllDrives=true)` confirms the destination is non-trashed in `MGS-AGENTS`, the expected `driveId` matches, size matches exactly, Drive MD5 matches the local file, and any recorded SHA-256/readback also matches. Preserve a compact provenance manifest with source/destination IDs, filename, size, checksums and status. A missing legacy ID, name-only match, stale success report, partial batch, or failed readback must fail closed and retain the local file.

For residual media that may have been renamed, inventory the full bounded local media scope and the canonical Shared Drive, then join by **exact size + Drive MD5**, never by filename. This proves byte identity despite renaming. Revalidate every proposed remote ID with individual `files.get` readback immediately before freezing the deletion manifest; include local path, size, MD5, SHA-256, remote ID, `driveId`, and readback status. Preserve every unmatched, derived, frame-extracted, metadata-changed, or recompressed file: similarity is not identity. Before Critical Subset confirmation, verify the exact local targets have no process, literal script/cron/systemd, symlink, or mount references, bind authorization to a target-set hash, and never include parent directories merely to remove matched children.

This local-media rule never authorizes deletion of persistent browser authentication state. Ares browser profiles, cookies/storage, collector locks, collector runtime, and the Playwright browser revision required by that collector are a separate protected class.

## Consumer contract

Active MGS consumers must either import `mgs_google_workspace_auth.py` or implement the same Service Account JWT contract against the same 1Password item. They must reject every auth mode other than `service_account`.

Current critical consumers include:

- `monitor-drive-auth-unified.py`
- `dtr-sb-page-health-sync.py`
- `sb-restricted-transition-monitor.py`
- `process-revenue-spend-report.py`
- `ares-drive-thumbnail-sampler.py`
- `ares-drive-upload-manual-inventory.py`
- `ares-execute-creative-copy-clean.py`
- `meta-app-roles-watch.sh`
- `b011-dtr-link-watch.sh`
- `mgs-offsite-backup.py`
- REC/P1 Gemini image generation through its separate canonical API-key item

Generic Google Workspace helper scripts that expect a personal token or local client-secret file are not valid MGS routes and must fail closed in MGS profiles.

For operational Sheet datasets, do not use public `gviz` or CSV export URLs as the source of truth. Those exports can honor an active basic filter and silently return only visible rows while still returning HTTP 200 and valid headers. Read the named canonical tab through Sheets API `spreadsheets.values.get` with the canonical Service Account, validate required headers, require a non-empty operational scope, and then validate the exact consumer. A filtered export is not a safe fallback.

## Google Sheets API batchUpdate pitfall

For `spreadsheets.batchUpdate`, do not add a top-level `fields` property inside an `addBanding` request. The `addBanding` schema accepts `bandedRange` only; an extra `fields` key makes the entire batch fail atomically with `INVALID_ARGUMENT`. If a mixed values-and-formatting workflow reports this error, first read back the exact value ranges to reconcile whether data already landed, then retry only the still-missing formatting batch without replaying the values write.

## Failure handling

```text
Failure                                       Required action
--------------------------------------------  ---------------------------------------------
Canonical item unreadable                     stop; report infrastructure failure
Project/client identity mismatch              stop; do not mint token
Drive 404 / Sheets 403 for known Sheet         share exact file with canonical SA; retry
Sheets API disabled                            enable in mgs-core-prod; retry same identity
My Drive upload quota failure                  use MGS-AGENTS; do not change identity
Shared Drive capability missing                correct membership/role with authorization
Canary write succeeds, restore fails           stop and restore before further writes
Any non-service-account selector               stop as configuration conflict
```

## Residue audit after cutover

Scan live scripts, profile skills, `.env` key names, Hermes jobs, root crontab, systemd units, `.secrets` and operational state files. Do not print values.

When Rodolfo asks whether **anything** was left behind, do not stop at active production roots. Perform both operational closure and retention closure across `work/`, `tmp/`, agent artifacts, archived skills, curator snapshots, local backups and encrypted off-site backups. If full disaster-recovery archives included `.secrets` while the retired credential existed, classify those archives as credential-bearing even though encrypted. Create and restore-test a clean replacement before requesting the Critical Subset confirmation needed to delete old remote backups.

Use `references/deep-google-auth-residue-and-backup-closure.md` for the full filesystem/process/backup sequence, neutralization patterns, continuous guard and final reporting contract.

The final state requires:

- no credential-bearing personal Google files;
- no active wrapper selecting a retired mode;
- no active skill instructing personal token setup;
- no cron/job/systemd consumer of retired utilities;
- historical Git/audit/backups clearly outside runtime;
- canonical selectors present and read back;
- exact consumers tested.

## Service Account replacement closure

When a project or Service Account identity changes, do not stop after validating the Shared Drive root. Permissions on individually shared My Drive Sheets belong to the exact old principal and do not transfer to a same-named identity in a new project. Rebuild the active file closure, probe every file with the new identity on Drive and Sheets, repair exact file permissions, run a reversible canary, and only then remove the old credential path.

Use `references/service-account-identity-replacement-permission-closure.md` for the complete cross-agent permission, residue-scan, fail-closed compatibility and evidence checklist.

## Verification checklist

- [ ] Canonical project and client email match.
- [ ] 1Password item read succeeds without exposing values.
- [ ] Shared Drive root and capabilities pass.
- [ ] Every active Sheet returns Drive + Sheets HTTP 200.
- [ ] One write/readback/restore canary passes after permission changes.
- [ ] All production selectors are `service_account`.
- [ ] Generic personal-auth helpers fail closed in every MGS profile.
- [ ] No active legacy credential file, job, cron, service or fallback remains.
- [ ] Work/tmp/artifact/archive residues are migrated or explicitly fail closed.
- [ ] Full off-site backups created during the retired credential lifetime are classified; a clean replacement is restore-tested before any Critical Subset deletion.
- [ ] Inventory, checkpoint, audit and REPORT-INFRA are updated.
