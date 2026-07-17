# Cross-agent Google Sheets inventory and Shared Drive cutover

Use when Rodolfo wants to eliminate personal Google dependencies by regularizing only MGS operational spreadsheets used by agents under the canonical Service Account and enterprise Shared Drive architecture.

## Scope boundary

The scope is **not the user's whole My Drive**. Include only spreadsheets with evidence that Zeus, Atena, Ares, or another named MGS agent currently uses them:

- live root/Hermes cron dependency;
- active script/config/data reference;
- current skill/reference used as an operational source;
- validated on-demand workflow such as monthly finance;
- explicit current instruction from Rodolfo.

Treat session imports, backups, one-off work directories, retired staff sheets, and deleted/404 IDs as evidence to classify—not proof of active use.

## Read-only inventory sequence

1. Read the MGS agent/route maps so ownership is not inferred from filenames.
2. Capture live root crontab and Hermes cron jobs for the relevant profiles.
3. Scan active scripts, configs, data, and agent skills for:
   - `docs.google.com/spreadsheets/d/<ID>`;
   - `SHEET_ID`, `SPREADSHEET_ID`, `SID`, and equivalent constants;
   - Sheets API endpoints;
   - dynamic IDs loaded from approved config/1Password without exposing values.
4. Run a broader secondary scan over work/history and classify those hits separately.
5. For every candidate ID, query Drive `files.get` and Sheets `spreadsheets.get` with the canonical Service Account using `supportsAllDrives=true`. Record only non-secret metadata:
   - name and MIME type;
   - `driveId` present/absent;
   - trashed/404 state;
   - user and Service Account HTTP status;
   - capabilities and parent IDs when useful.
6. Enumerate all spreadsheets in the target Shared Drive with `corpora=drive`, `driveId=<target>`, `includeItemsFromAllDrives=true`, and `supportsAllDrives=true`. This catches dynamically created Sheets with no hardcoded ID.
7. Classify into four groups:
   - active/on-demand in personal My Drive;
   - already in the canonical Shared Drive;
   - historical/retired/needs owner decision;
   - stale, deleted, inaccessible, or non-Sheet references.
8. Report by agent and workflow. If an agent has no direct active Google Sheet route, say that precisely; do not assign a Sheet from its title alone.

## Migration design

Do not migrate during the inventory turn when Rodolfo asked to review the list first.

For the approved cutover:

1. Inventory formulas, `IMPORTRANGE`, Apps Script, protected ranges, named ranges, charts, external links, sharing, and cron/script consumers before moving anything.
2. Prefer adding technical identities as least-privilege members of the Shared Drive rather than sharing each spreadsheet separately.
3. Verify the Service Account project has both Drive API and Sheets API enabled. Drive metadata HTTP 200 does not prove Sheets API access.
4. Prefer an in-place move when Google permits it and the file ID remains stable. Validate ID and formulas after the move.
5. If ownership/domain restrictions require a copy, treat it as an ID-changing migration: backup/export first, copy one canary, update every route, and retain rollback mapping `old_id -> new_id`.
6. Migrate one workflow/agent block at a time. Start with a low-risk canary, then run the exact consumer: token/JWT probe -> bounded dry-run -> apply -> Sheet/state readback.
7. For finance sheets, validate all `IMPORTRANGE` relationships and cross-sheet tab-name parity; a visually intact sheet is not enough.
8. Keep the previous file IDs and formulas as rollback evidence, not a previous authentication route. Every affected script, cron, on-demand procedure and external report must pass on the canonical Service Account before closure.
9. Update canonical context, IDs/configs, inventory, checkpoint, audit, and REPORT-INFRA after each authorized block.

## Executive reporting pattern

Report concise grouped counts, followed by clickable names:

- `My Drive — operational migration candidates`
- `Already in enterprise Shared Drive`
- `Historical/retired — owner decision`
- `Stale/inaccessible`

State explicitly: files moved, files not moved, Service Account coverage, confirmation that no alternate authentication route remains, and any file-permission follow-up.
