# Google Sheets Finance Dashboard Build

Use this reference after the monthly tab, summary tab, external dependencies, and semantic formula audit all pass. It describes the reusable build transaction; month-specific coordinates remain in the relevant audit ledger.

## 1. Freeze and backup

1. Read workbook metadata and require the intended dashboard tab names to be absent.
2. Snapshot every source tab in `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` modes.
3. Hash the `FORMULA` render. Because constants also appear in this render, the hash detects both formula edits and manual input changes while ignoring recalculation of volatile formulas.
4. Record the original sheet-title set and a rollback contract that deletes only sheet IDs created by this run.
5. Immediately before creating tabs, re-read the source formula renders and require exact hash parity.

## 2. Structural canary

Before the real tabs:

1. Add a uniquely named temporary sheet.
2. Read metadata and verify its exact title and returned sheet ID.
3. Delete that exact sheet ID.
4. Read metadata again and require the title to be absent.

A successful value-cell canary does not prove permission to add/delete sheets; use a structural canary for a structural build.

## 3. Normalize without double counting

A single base can safely mix several fact grains only when every row carries a discriminator such as `Nível`:

- `SITE` — one monthly row per site/segment; use for site and partner totals.
- `PAÍS` — one monthly row per site/country; use only for country analysis.
- `GERAL` — one row per day from validated global helper totals; use for daily charts.
- `GERAL_MÊS` — one authoritative monthly closure row bound to the approved summary cells; use for executive closure KPIs.

Never sum `SITE` and `PAÍS` together. Never use an average of daily ROI values as a substitute for the authoritative monthly ROI unless the business definition explicitly says to.

For multi-manager sites, store one financial row with a shared ownership label and a separate validated manager-list field. Duplicating the same financial values once per manager inflates revenue, spend, and profit. Unknown ownership stays explicit. Classify dimensions such as vertical only from supported source evidence; otherwise use a neutral unclassified value.

## 4. Bind facts to the right source

- Executive month-closure KPIs come from the approved summary/closure cells.
- Site and country rankings come from the audited monthly blocks.
- Daily evolution comes from validated global helper rows or an independently recomputed equivalent.
- Special lower blocks remain separate segments in the base, then aggregate by site only in analytical queries.
- Keep sensitive or unrelated tabs out of the dashboard even if they are present in the workbook.

## 5. Create and format

1. Create the normalized-base and executive-dashboard sheets in one bounded request and store their returned sheet IDs.
2. Write values and formulas with explicit ranges and `USER_ENTERED` only where formula parsing is intended.
3. Add header formatting, number formats, conditional rules, a basic filter on the base, and strict dropdown validation on dashboard filter cells.
4. Build analytical tables from formulas that select one fact grain at a time.
5. Add charts from those table ranges.

Google Sheets API constraint: for a `BAR` basic chart, each series must target `BOTTOM_AXIS`. `LEFT_AXIS` is valid for many column/line charts but causes `INVALID_ARGUMENT` for bar-series requests.

## 6. Independent verification

Require all of the following before success:

- Target sheet titles and IDs exist exactly once; the original title set gained only the intended tabs.
- Base row/column counts and every written anchor formula match the candidate.
- No displayed error exists in the base or dashboard.
- Source `FORMULA` hashes are unchanged.
- Site-grain totals reconcile independently with source totals.
- Daily-grain totals reconcile with monthly global totals.
- The monthly-closure row and executive KPI cards match the approved summary cells.
- Basic filter, dropdown validations, and chart count read back from Sheets metadata.
- Change one safe dashboard filter, verify the analytical result reacts, restore the exact original value in `finally`, and confirm the restored result.

## 7. Failure and rollback

If any build or verification step fails after tab creation:

1. Delete only the sheet IDs returned by this run.
2. Read metadata and require both target titles to be absent.
3. Confirm source formula hashes still match the frozen backup.
4. Correct the deterministic defect.
5. Re-run the full preflight before retrying; do not reuse an assumption that the workbook remained unchanged.

Record both the failed attempt and successful rollback. A corrected retry is valid only after absence and source-preservation checks pass.