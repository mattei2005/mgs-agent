---
name: productivity-workspace-apis
description: "Use when operating productivity SaaS/workspace tools through CLIs or APIs: Airtable, Google Workspace, Notion, Obsidian, Himalaya email, and Teams meeting pipeline operations."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [productivity, api, workspace, google, notion, airtable, obsidian, email, teams]
    related_skills: [documents-and-presentations]
---

# Productivity Workspace APIs

## Overview

Umbrella for workspace/productivity systems where the agent reads, writes, searches, or operates user data through APIs, CLIs, or filesystem-backed vaults. Use this as the router instead of scattering one-tool micro-skills.

## MGS Google production override

For every MGS Drive or Sheets operation, use only the canonical Service Account `mgsagent@mgs-core-prod.iam.gserviceaccount.com` through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`. Personal Google token files, client-secret files, browser consent and refresh-token setup are permanently retired and are not fallback paths. The bundled `scripts/google-workspace/` personal-auth helpers are disabled in MGS profiles and must fail closed. Gmail, Calendar, Contacts or other user-scoped Workspace operations remain blocked until Rodolfo approves a separate corporate identity architecture; do not improvise one.

## When to Use

- Airtable bases/tables/records CRUD or upsert work.
- Google Workspace tasks: Gmail, Calendar, Drive, Docs, Sheets, Contacts.
- Notion pages/databases/blocks/files via official API or CLI.
- Obsidian vault reading/searching/editing.
- Terminal email operations through Himalaya.
- Microsoft Teams meeting summary pipeline operations.

## Tool Router

| Workspace | Detailed reference/support |
|---|---|
| Airtable | `references/absorbed-skill-md/airtable.md` |
| Google Workspace | MGS Drive/Sheets: canonical `mgs-core-prod` Service Account via `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`; the bundled personal-auth reference/scripts are not operational routes. Data-shape references for Sheets remain valid. |
| Notion | `references/absorbed-skill-md/notion.md`; block reference in `references/notion/` |
| Obsidian | `references/absorbed-skill-md/obsidian.md` |
| Himalaya email CLI | `references/absorbed-skill-md/himalaya.md`; details in `references/himalaya/` |
| Teams meeting pipeline | `references/absorbed-skill-md/teams-meeting-pipeline.md` |

## Operating Principles

1. **Resolve credentials and concrete paths first.** Do not pass unresolved env vars or vague vault paths to tools.
2. **Prefer official/established APIs.** Use curl/CLI helpers encoded in the references rather than inventing endpoints.
3. **Read back after writes.** For user data systems, verify the created/updated record/page/file/message.
4. **Separate automation from content.** Preserve IDs, URLs, and file paths for later audit.
5. **For Google Sheets, presentation matters.** When delivering operational analysis to Rodolfo in a sheet tab, do not paste raw CSV-looking output and stop. Use readable blocks: title, metadata, summary table, distribution table, detailed table, clear headers, and remove scratch/audit columns that confuse operators.
6. **Preflight before mutating shared Sheets.** When the user provides a destination Google Sheet for processed business data, inspect and validate the input structure first, then report blockers before writing. Do not overwrite/populate the sheet if required source tabs are empty, if mapping rules are ambiguous, or if the intended output shape is unclear. Create only the tabs the user asked for; diagnostic/audit tabs belong in local files or a concise validation tab unless explicitly requested.
7. **Backup before destructive Sheet overwrites.** Before clearing, replacing, or rebuilding existing Google Sheet tabs, create a recoverable backup: either duplicate each tab in the same spreadsheet with `BKP`/timestamp suffix or export/read and save exact TSV/CSV locally with tab name + gid. This is mandatory when the tab contains user-facing operational notes/decisions, not just generated scratch output. Never assume a local regenerated report is enough if the Sheet may contain manual edits.
8. **For Sheets comparisons/writes, map live headers before trusting column letters.** If the user names columns by letter (for example “B and D”), re-read the current tab and map the business fields by headers (`User`/`LOGIN`/`email`, `Segurador`/`name`, `PG`/`PAGES`) before computing or writing. Google Sheets table conversion, inserted columns, and backup tabs can shift the exported/API columns. For details, see `references/google-sheets-column-letter-and-header-safety.md`.
9. **Preserve the requested analytical unit.** For event/submission/message audits, one source occurrence must remain one Sheet row, including repeated names or phones. Normalization used for matching must not silently deduplicate. Build differences as multisets by consuming one counterpart per occurrence. Do not omit rows because a later business action might create duplicates: analysis and execution authorization are separate, and Rodolfo/MGS decides whether to resend. See `references/google-sheets-occurrence-level-comparisons.md`.
10. **Keep the canonical MGS Google identity.** MGS Drive and Sheets use only the `mgs-core-prod` Service Account. Diagnose Drive permission, Sheets API activation, Service Usage/IAM and quota attribution as separate gates. Never redirect a task to personal user authentication or local token files.

### Google Sheets API enablement

When Drive access works but Sheets API reports that `sheets.googleapis.com` is disabled, keep the same canonical Service Account and enable the API in `mgs-core-prod` through an approved administrator path. Treat API activation, Service Usage Consumer, file permission and quota-project attribution as separate gates. Retry Sheets metadata and then a bounded write/readback/restore canary. Never solve API activation by creating a personal token or switching identities.

### Google Sheets fallback pattern

If the Sheets API path is blocked by permissions/API-disabled state but the sheet is editable in browser, use a browser paste fallback:

```text
1. Generate TSV for data shape.
2. Generate optional HTML table with inline styles for readable formatting.
3. Open the exact target sheet/tab by `gid`.
4. Clear the target tab/range.
5. If reusing an old formatted report tab, unmerge cells and/or clear formatting before paste; merged title/metadata cells can collapse the first TSV rows into a single exported row.
6. Write both `text/html` and `text/plain` to clipboard, or TSV as `text/plain` when raw tabular structure is the priority.
7. Paste into A1.
8. Validate by CSV export/readback for every target tab: non-empty row count, max column count, first header row, last row, and sentinel IDs.
```

Do not hard-code a lasting claim that the API is unavailable; treat this as a fallback for the current permission state. If readback shows merged/collapsed header rows, fix the tab formatting and paste again before declaring completion.

## Verification Checklist

- [ ] Required env vars/credential files checked.
- [ ] Target workspace/base/vault/mailbox/channel identified.
- [ ] Mutating operations scoped and verified by read-back.
- [ ] Final answer includes IDs/URLs/paths for created or modified artifacts.

## Google Sheets fallback pattern

When direct Google Sheets API write fails because the available service account lacks Sheets API enablement or project permissions, do not stop if the sheet is editable in browser. Use the browser UI as a fallback: prepare TSV locally, open the target worksheet, select/clear the target area, paste TSV via clipboard, then verify with a visual/snapshot/read-back check. See `references/google-sheets-browser-paste-fallback.md`.

For browser-only Sheets where the canonical API route is temporarily blocked, a browser paste may be used only as an explicitly authorized UI fallback with export/readback validation. It does not change the canonical identity and must not create local Google credentials. See `references/google-sheets-browser-paste-fallback.md` and `references/google-sheets-public-edit-fallback.md` for data-shape and readback mechanics only.
