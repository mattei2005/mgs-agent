# Google Sheets category-tab delivery via Drive import/update — 2026-07-06

## Context

Rodolfo asked for an operational Excel/report to be placed into an existing Google Sheet as separate tabs, one category per tab. The available Google service account could edit Drive files, but direct Sheets API calls failed because `sheets.googleapis.com` was disabled for the project and the service account lacked permission to enable it.

## Durable pattern

When direct Sheets API is unavailable but Drive API has `canEdit` / `canModifyContent` on the target spreadsheet:

1. Build a local `.xlsx` with exactly the requested tabs.
2. Keep tab names concise and operator-readable.
3. Apply basic formatting locally with `openpyxl`: bold/fill headers, freeze panes, filters, column widths.
4. Use Drive API `files().update(fileId=<spreadsheet_id>, media_body=<xlsx MediaFileUpload>)` to replace/import the spreadsheet content while preserving the same Google Sheet file ID/link.
5. Validate in two ways:
   - Browser snapshot/UI shows expected tab names and a known header/cell.
   - Public/readable CSV export per `gid` returns the expected row counts and headers.

This is useful for Rodolfo-facing operational review sheets when a one-time conversion/import is enough and preserving the existing URL matters.

## Important caveats

- Direct `sheets.spreadsheets().get/update` may fail with `SERVICE_DISABLED`; do not treat that as the whole workflow being blocked if Drive API can edit the file.
- `serviceusage.services.enable` may fail with `AUTH_PERMISSION_DENIED`; record it as API enablement lacking permission, then use Drive import or browser fallback.
- After Drive `files().update` import, an immediate Drive export to `.xlsx` may not be a reliable content verification in some cases; in this session it returned the new tab names but empty workbook content. Validate instead via Google Sheets UI and per-tab CSV export/readback.
- Replacing a Google Sheet via Drive upload overwrites the workbook/tabs. Use this only when the user asked to create/populate the target structure or when the target is empty/throwaway. For existing business sheets with valuable tabs/formulas, prefer Sheets API or browser paste into specific tabs.
- If Drive create/upload fails with storage quota on a separate test file, do not infer update of the existing file is impossible. Updating an existing shared file may still work.

## Verification example

After import, collect current `gid`s from the UI/location or sheet HTML, then read:

```text
https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}
```

Expected validation shape:

```text
Tab                         Rows  Cols  First header
Sem campanha enviada        1724  11    link da pagina
Sent OK                     323   11    link da pagina
Paginas com erro real       425   11    link da pagina
Sem match no SB             189   11    link da pagina
Acoes dry-run               231   11    link da pagina
```

## Operator-facing format lesson

When Rodolfo says a report is confusing, do not force him to interpret raw internal labels. Create/readable tabs or sections matching his mental buckets and use simple Portuguese labels. Put raw/internal fields in columns, not in the first explanation.
