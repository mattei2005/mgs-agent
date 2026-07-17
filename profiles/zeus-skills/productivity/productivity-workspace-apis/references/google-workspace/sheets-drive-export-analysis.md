# Google Sheets via Drive export when Sheets API is unavailable

Use this when a Google Spreadsheet is readable in Drive but `sheets.googleapis.com` returns `403 SERVICE_DISABLED` or direct public CSV export returns `401`.

## Pattern

1. Authenticate with the available Google OAuth/Service Account credential.
2. Verify Drive can read the spreadsheet metadata via Drive API `files.get`.
3. Export the spreadsheet through Drive API instead of Sheets API:
   - Endpoint: `GET https://www.googleapis.com/drive/v3/files/{spreadsheet_id}/export?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - Header: `Authorization: Bearer <access_token>`
4. Save the result as `.xlsx` and analyze locally.
5. If `openpyxl`/spreadsheet libraries are unavailable, parse the XLSX directly as a zip:
   - `xl/workbook.xml` + `xl/_rels/workbook.xml.rels` map sheet names to `xl/worksheets/sheetN.xml`.
   - `xl/sharedStrings.xml` resolves shared string cell values.
   - Sheet cells are XML nodes `c r="A1"` with `v` values and optional `t="s"` shared-string indexes.

## MGS revenue spreadsheet note

For `MGS - Receita dos Sites 2026`, monthly sheets can contain two regions:

- Top consolidated area: row 3 headers, row 36 totals, row 2 metric names.
- Lower operational summary area: row 82 labels like `Receita <site> $:` and row 83 values.

When Rodolfo asks for site revenue/day in a month, prefer the explicit lower summary labels (`Receita <site> $:` on row 82 and USD value beside `Receita:` on row 83) because they represent site-level revenue blocks cleanly across all sites. Determine denominator from days with actual data in that month, not calendar days, unless Rodolfo explicitly asks for calendar-month average.

## Pitfalls

- Do not conclude the file is inaccessible just because CSV export requires sign-in; OAuth Drive export may still work.
- Do not store or print OAuth secrets/tokens. Report only credential item names or non-secret metadata.
- Do not require Sheets API if Drive export is enough for read-only analysis.
