---
name: monthly-finance-sheet-fill
description: Use when filling or auditing MGS monthly finance Google Sheets from approved Long revenue/spend data, including site block mapping, GROSS_USD vs GROSS_CAD, USD vs BRL spend, manager mini-tables, backups, and cell-level validation.
version: 1.0.5
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, finance, google-sheets, revenue, spend, reconciliation, audit]
    related_skills: [revenue-spend-reporting-pipeline]
---

# Monthly Finance Sheet Fill

## Purpose

Use this skill when Rodolfo asks to fill an operational monthly finance sheet such as `MGS - Receita dos Sites 2026` / `Junho 2026` from an approved `Long` table or Excel report.

This is not the same as generating the `Long` report. The job here is to write values into the existing operator-facing monthly sheet structure without damaging formulas, dates, currencies, totals, or manual exception blocks.

## Non-negotiable rules

1. **Backup before writing.** Save the touched range or full sheet snapshot with formulas and formatted values before any update.
2. **Map by real date, not row arithmetic alone.** Verify the month length. For June, never write to a day-31 row. If a template has formulas beyond the month, treat them as out-of-scope unless Rodolfo explicitly asks.
3. **Preflight all target columns.** Confirm every source site/account maps to a destination cell before writing. If anything is unmapped, stop before partial write.
4. **Respect revenue currency.** Some sites take raw `GROSS_USD_*`; some take raw `GROSS_CAD_*` and compute USD next to it.
5. **Respect spend currency.** Meta/Business Manager spend usually goes to `BM - $`; Google Ads BRL goes to `Google Ads - R$`.
6. **Audit after writing.** Compare expected source values to sheet cells cell-by-cell, not only by totals. Check formula errors and out-of-period rows.
7. **Do not call success until verified.** Report mismatches honestly and fix if safe.
8. **Use Service Account auth by default.** Load short-lived Sheets tokens through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`, send the Service Account quota project, and require Sheets HTTP 200 plus destination writer access. User OAuth is rollback-only and must not be revoked/deleted without the separate credential-critical confirmation.

## Canonical workflow

1. Load/confirm the approved source `Long` data:
   - Required columns: `Data`, `Site`, `Vertical`, `Gestor`, `Conta_FB`, `Gasto`, `Receita`.
   - Confirm row count and totals against the approved report.

2. Read the target monthly sheet structure:
   - Header rows for site blocks.
   - Revenue headers: `GROSS_USD_*`, `GROSS_CAD_*`.
   - Spend labels around account rows, usually rows 41–45 in the June template.
   - Any special lower blocks such as `NF100` / `ICARO - G001-D` or Fincgriffin manager table.

3. Build an explicit mapping table:
   - `(site, country/vertical, revenue_currency) -> gross revenue cell column`.
   - `(ad account or aggregate rule) -> spend cell column`.
   - Special blocks and aggregate rules.

4. Preflight for blockers:
   - Any source revenue with no revenue target.
   - Any source spend account with no spend target.
   - Any target row outside the source date range or outside the month.
   - Any existing formula errors.

5. Write only the intended cells:
   - Source period only.
   - Target monthly tab only, unless Rodolfo asked otherwise.
   - No broad clears except deliberate cleanup of an out-of-scope contaminated row.

6. Post-write audit:
   - Expected cell count vs actual updated cell count.
   - Cell-by-cell mismatch list.
   - Formula errors count.
   - Row outside month/date range check.
   - Special block validation.

## Incremental multi-day updates

When earlier days of the month are already filled and Rodolfo supplies a later period:

1. Reconcile the new workbook independently and write top daily cells only for its date range.
2. Load the previously approved `Long.csv` outputs for earlier days of the same month.
3. Combine prior + new Long sources only for cumulative lower tables such as Fincgriffin and Creditoparaveiculo; never reconstruct gestor detail from displayed Sheet totals.
4. Route spend by normalized `Conta_FB`, not only by site, whenever a site block has multiple manual `BM - $` slots.
5. Preserve the slot already used by that account earlier in the same month. If the account is genuinely new, preflight a free manual slot and record the mapping in the audit; do not silently collapse it into another account.
6. After normal readback, run an independent scope-diff: compare broad pre-write and post-write `FORMULA` snapshots and fail if any changed cell is outside the approved daily bands or explicitly rebuilt lower tables.

See `references/july-2026-8-12-incremental-fill-audit.md` for the validated incremental pattern, account-routing lesson, and independent scope-diff audit.

## Durable MGS mapping rules learned from June 2026

Revenue `GROSS_CAD_*` sites:

- `financeadx.com`
- `helixenit.com`
- `infinitynexx.com`
- `marevelx.com`
- `vizioid.com`
- `xyvlov.com`

Revenue `GROSS_USD_*` sites:

- `cliquet.com`
- `conectageral.com`
- `creditoparaveiculo.com`
- `de.newsoun.com`
- `ducapes.com`
- `eggbev.com`
- `finance.ducapes.com`
- `finance.topfeed.fun`
- `finance.wantabrand.com`
- `finanzas.cliquet.com`
- `finanzas.eggbev.com`
- `finanzas.lyzmo.com`
- `finanzas.newsoun.com`
- `finanzas.openzed.com`
- `finanzas.topfeed.fun`
- `finanzas.zuout.com`
- `finanzas.zytiva.com`
- `fincgriffin.com`
- `gamezonead.com`
- `gamingadx.com` when revenue exists; in June 16–29 it had no revenue.
- `lyzmo.com`
- `newsoun.com`
- `openzed.com`
- `portalrelevante.com`
- `seuprimeiroempregoam.com`
- `wantabrand.com`
- `zuout.com`
- `zytiva.com`

Spend in BRL / Google Ads R$:

- `gamezonead.com` → account `Mattei 1` / source `Mattei 1 (Google Ads - BRL)`.
- `gamingadx.com` → account `Gamingadx-US-01` / source `Gamingadx-US-01 (Google Ads - BRL)`.

Spend in USD / BM `$`:

- All other confirmed June 2026 spend sites unless Rodolfo updates the mapping.

Special handling:

- `creditoparaveiculo.com`: sum all related FB accounts for the top aggregate, but route each account to the live manager-specific spend slot. The old July-style lower mini-table at fixed `ABL...ABQ` coordinates is historical only. The live June redesign uses six independent daily blocks (`G001`–`G006`) with direct spend, revenue, tax, profit, and ROI columns; discover their current coordinates from headers before writing.
- `fincgriffin.com`: preserve the top aggregate while routing manager/account spend to the live dedicated slots. The old consolidated `Data | Gestor | Gasto | Receita | Lucro | Margem` mini-table is historical only. The live June redesign uses six independent daily blocks (`G001`–`G006`) and includes a complete US revenue/spend segment; discover current columns and total rows from the live tab before writing.
- `openzed.com`: split principal block from `NF100` / `ICARO - G001-D`; do not collapse Ícaro into the principal block.
- `finanzas.openzed.com`: keep US and ES blocks separate.
- `gamezonead.com` / `gamingadx.com`: fill only the `Google Ads -R$` input column for BRL spend and preserve the neighboring USD conversion formula column (for example `AAG46 = SUM(AAH46/$E$1)`, `AAV46 = SUM(AAW46/$E$1)`). Broad clears must not blank those formulas.

## Monthly tab rollover rules

Use this when Rodolfo asks to duplicate a monthly finance tab such as `Junho 2026` into the next month such as `Julho 2026`.

Non-negotiable rollover checks learned from July 2026 prep:

1. Main sheet monthly tab cell `A3` stores the numeric month used by `Despesas Totais` formulas. When rolling `Junho 2026` to `Julho 2026`, update `A3` from `6` to `7` before validating totals.
2. Main sheet column `B` stores repeated daily date blocks, not just the first visible month block. Rebuild every repeated date/month block through the active monthly area (observed through row ~180 in July 2026 prep): month labels `Junho` → `Julho`, and each 30-day June run becomes a 31-day July run including the previously blank day-31 row. Preserve the visual number format used by the source tab, e.g. `dddd, d` showing `Monday, 1` — do not leave raw `dd/mm/yyyy` if the source month displays weekday/day text.
3. Main sheet top exchange/cash cell `E1` must move to the target month column in `CAIXA SINTETICO`: June used `H2`, July uses `I2`. Manager sheet `H1` must be updated the same way.
4. Preserve the `Despesas da Empresa` block around `L101:N120` from the source month unless Rodolfo explicitly asks to clear it; he manually checks those expenses through the month.
5. Preserve special lower table structure such as `NF100` / `ICARO - G001-D` / Openzed, but clear the monthly revenue and spend input cells. For July 2026 this meant clearing `NF105:NF135`, `NM105:NM135`, and spend input columns `NF/NH/NJ/NL/NN/NP/NR/NT/NV` rows `146:176`, while keeping formulas/headers intact.
6. Manager sheets: update the top exchange-rate source formula in `H1` from `CAIXA SINTETICO!H2` (June) to the new month column, e.g. `CAIXA SINTETICO!I2` for July. Do not rely on tab duplication to adjust this.
6. Audit formulas that reference `$A$3`, `DATE($B$4,$A$3,...)`, `EOMONTH(DATE($B$4,$A$3,1),0)`, or the daily row number. These control per-day expense distribution and can look visually correct while calculating the wrong month if `A3` is stale.
7. Manager sheets depend heavily on exact tab-name parity via `SHEETNAME()`. The main sheet and all manager sheets must have the exact same target tab name, e.g. `Julho 2026`; validate imported labels such as manager `A21` after fixing the main sheet date/month labels.
8. Do a formula inventory before mutating: count formulas, classify `IMPORTRANGE`, `CAIXA SINTETICO`, `$A$3`, hardcoded month literals, and formula errors. Save the audit locally before writing.
9. **Rebaseline from the live source tab before every rollover.** Historical backups and rollover scripts are evidence, not templates, when Rodolfo has modified the source month. Compare live used row/column extent with the prior baseline, locate site blocks by header text instead of fixed coordinates, and inventory repeated manager/account blocks before duplicating. A structurally stale duplicate must be discarded and recreated from the live source rather than patched piecemeal.
10. For Fincgriffin and CreditoParaVeiculo, explicitly validate both the top revenue/spend layout and every lower manager block. The June 2026 redesign introduced a complete Fincgriffin US segment, direct manager-specific spend slots, ten direct CreditoParaVeiculo `BM - $` slots, and six independent `G001`–`G006` daily blocks for both sites through row 338. Re-read live positions; do not reuse the old consolidated Fincgriffin table or historical Credit fixed columns.
11. If the target tab was deleted and is being recreated with the same name, **rebind every `CAIXA SINTETICO` formula that points to that tab**, even when `valueRenderOption=FORMULA` shows apparently correct text. Google Sheets can retain the deleted sheet's internal reference and continue returning `#REF!`. Re-write every external target-month formula from the live previous-month formula with only the tab name changed, then require zero formatted errors.
12. A clean target month can expose aggregate formulas that only worked because the source month had data. After clearing inputs, scan the full target range for errors. For empty-set `AVERAGEIF` totals such as July 2026 `AHB36`/`AHC36`, use an empty-safe equivalent (`IFERROR(..., "")`) in the target and include those cells in the authorized scope diff.

See `references/june-2026-live-structure-rebaseline.md` for the live-vs-backup structural delta, deleted-tab rebind pitfall, and required discovery checklist before recreating July 2026 or any later month.

## Caixa Sintetico monthly column fill

Use this when Rodolfo asks to fill the `CAIXA SINTETICO` column for a new month based on the previous month.

Workflow:

1. Identify the target month column by header row 8 (`Jan`...`Dez`). In June 2026, `Jun` is column `H` and `Mai` is column `G`.
2. Read the previous month formulas and formatted values for the full sheet before writing.
3. Backup `CAIXA SINTETICO` formulas and formatted values locally before any update.
4. For every row where the previous month column has a formula referencing the previous monthly tab and the target month cell is blank, copy the formula and replace the tab name only, e.g. `'Maio 2026'` → `'Junho 2026'`.
5. Do not overwrite formulas that already exist in the target month unless Rodolfo explicitly asks for repair.
6. Leave intra-summary formulas (`SUB-TOTAL`, `TOTAL`, rev share, imposto, net, ROI, 50% USD/BRL) in the target month if they already exist; otherwise copy the adjacent month formula by relative month column.
7. Validate by readback: all intended formulas present, formula error count = 0, and key rows populated (`SUB-TOTAL`, `TOTAL`, `Despesas Empresa`, `Despesas Funcionarios`, `MM Social Media Costs`, `MM Total NET`, `ROI LIQUIDO`, `50% em USD`, `50% em REAIS`).

June 2026 validated pattern:

- Copied/adapted 48 formulas from `Mai` to `Jun`.
- Replaced only `Maio 2026` with `Junho 2026` in source-tab formulas.
- Formula errors after write: 0.

## Shared Drive migration gate for finance workbooks

Do not move the principal finance workbook or a user-named subset of manager workbooks until the **live cross-spreadsheet dependency closure** is known.

Required preflight:

1. Batch-read formulas from the principal, every manager workbook, and historical finance workbooks.
2. Recursively resolve literal `IMPORTRANGE` IDs. Include old/ignored managers and auxiliary spreadsheets if formulas still reference them.
3. Separate the current principal workbook from historical storage; do not assume one file contains every year merely because manager workbooks have old monthly tabs.
4. Record formula counts, current-period error baseline, historical error baseline, tabs, permissions, and the exact dependency graph.
5. Treat bidirectional principal↔manager references as one transactional cluster. Do not move only six visible files if the graph contains historical or auxiliary sources.

Conservative MGS default: when the goal is to remove personal OAuth, leave the formula-heavy cluster in My Drive, share the complete dependency closure with the approved Service Account, enable Sheets API, and switch only runtime authentication. This avoids formula and `IMPORTRANGE` topology changes.

If Rodolfo later requests organizational ownership in Shared Drive, require a synthetic linked-Sheet move canary and the full transactional cutover procedure in `google-drive-agent-automation/references/shared-drive-google-sheets-cluster-cutover.md`. A move should preserve the same file ID, but completion still requires no new formula/value/error delta, preserved permissions/triggers, current-period parity, and rollback. Never promise absolute zero risk before the canary.

## Pitfalls

- **Date serial false positives:** Sheets API returns dates as serial numbers in `UNFORMATTED_VALUE` mode. Convert with epoch `1899-12-30` before declaring a mismatch. This applies especially to lower detail tables such as Fincgriffin `Data | Gestor | Gasto | Receita | Lucro | Margem`; numeric serials like `46204` may correctly mean `2026-07-01`.
- **Formula-column contamination during clears:** When clearing/filling monthly input bands, never blindly clear every mapped revenue/spend column across both top rows and spend rows. Some columns are manual input on one band but formula-derived on another band, e.g. `AAH`, `AAW`, `VM`, `NI`, `NP` in July 2026. Build the clear/write set from confirmed manual input cells only. If a batch accidentally touches formula columns, restore those formulas from the pre-write backup and re-validate formula parity before reporting success.
- **Out-of-month rows:** A template may contain formulas on a row that effectively evaluates as the next month. Do not fill or rely on it for the current month.
- **One-day reports can contain `Total` rows or omit spend dates.** Some daily exports include a final `Total` row in date-based revenue tabs and some one-day `Gastos FB` exports contain only `Account name | Amount spent` with no `Day` column. Parser rule: ignore rows whose date cannot be parsed; for FB spend with no date column, infer the date only when all other dated tabs in the workbook have exactly one same date. If the workbook has multiple dates or no dated tabs, stop instead of guessing.
- **MonetizeMore dates may be real Excel datetimes/serials, not ISO strings.** Parse the first column through the same date normalizer used for other tabs; do not require a literal `YYYY-MM-DD` string or MonetizeMore revenue will be silently skipped.
- **One-day reports can contain `Total` rows.** Some daily exports include a final `Total` row in date-based sheets. Remove/ignore those rows before processing, otherwise date parsing fails or totals get double-counted.
- **MonetizeMore block sheets can be skipped by generic runners.** If the runner output lacks MonetizeMore revenue, parse the block sheet manually (`domain` row followed by `Date | Gross Revenue`) and merge those rows before filling.
- **Mini tables may exceed the current grid.** Before appending Fincgriffin detail rows, check the tab row count. Use `appendDimension` to add rows if the target range exceeds grid limits.
- **Header label drift:** Some columns may be unlabeled or updated manually by Rodolfo. Re-read the live sheet immediately before writing.
- **Formula reference mistakes:** When writing formulas in mini tables, validate formulas by readback. In June 2026, a wrong column reference created `#REF!`; the fix was to compute `Lucro = Receita - Gasto` and `Margem = Lucro / Gasto` with the actual summary columns.

## Dashboard preflight and recursive formula audit

Before creating a finance dashboard or treating an existing ROI summary as authoritative:

1. Bind the dashboard to explicit source tabs. Existing summary/dashboard tabs are only hints until their coordinates and headers are reconciled against the live monthly structure.
2. Snapshot `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for every in-scope tab; hash the snapshots before any write.
3. Inventory every formula cell and every referenced range. Resolve `IMPORTRANGE` recursively until every external spreadsheet ID, tab, target range, and callback dependency is known. An unresolved external source blocks the dashboard.
4. For satellite manager workbooks, validate the exact file ID and `gid`, compare every imported spill cell against the principal source, verify the manager summary mappings, and independently recompute commission/estimate outputs.
5. Treat `GOOGLEFINANCE` in a finished month as an open close, not a stable historical value. Quantify downstream dependents and obtain the owner-approved closing rate before freezing or reporting final figures.
6. Never roll a summary forward by replacing only the month name when the monthly sheet width or block order changed. Re-map by live site/header semantics and validate each metric header against its source cell.
7. Audit daily formula continuity, missing day formulas, one-cell pattern outliers, total formulas, and semantic identities: invalid traffic, net revenue, tax, spend, profit, ROI Gross, and ROI Net. A zero formula-error count does not prove semantic correctness.
8. For `ROI_GROSS_TOTAL`, require every USD-normalized gross component intended by the block; for `RECEITA_NET_TOTAL`, require net components rather than gross components. Report omissions with cell-level impact before proposing repair.
9. Formula scanners must normalize A1 column letters to uppercase before converting them to numeric indices; lowercase ranges in live `IMPORTRANGE` formulas otherwise create false parity failures.
10. Build the normalized dashboard base only after external-source closure, current spill parity, zero formula errors, and disposition of every confirmed semantic divergence. Keep source tabs untouched unless a separately reported repair is authorized.

## Stepwise manual formula repair with Rodolfo

When Rodolfo asks to proceed “por partes”, treat that sequence as an execution boundary, not a presentation preference:

1. Freeze the current tab/order exactly as stated. If `CAIXA SINTETICO` was deferred until last, do not discuss, inspect for action, or request decisions about it while repairing the monthly tab.
2. Present exactly one confirmed problem at a time: cell/range, current formula or state, why it is wrong, and the exact smallest edit. Do not bundle later findings or repeat the full audit.
3. Rodolfo performs the manual edit unless he explicitly delegates the write. Never broaden a one-cell correction into fill-down or neighboring changes.
4. After he says the edit is complete, read back `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for the target plus the smallest dependent range. Compare the formula to adjacent-row/column semantics and require no displayed error.
5. Report only `PASS` or the exact remaining mismatch. Once Rodolfo has authorized the stepwise correction sequence, a successful readback must be followed immediately by the next confirmed problem in the same response; do not ask “posso passar ao próximo?”. Pause only when validation fails or a genuine business decision is required.
6. Keep a compact correction ledger so the later scope-diff can prove that every changed cell was intentional and no deferred tab was touched.

## Verification checklist

- [ ] Backup path recorded.
- [ ] All source revenue rows mapped or intentionally skipped with reason.
- [ ] All source spend rows mapped or intentionally skipped with reason.
- [ ] No writes outside requested date range.
- [ ] No writes to nonexistent days of month.
- [ ] Cell-by-cell audit returns zero mismatches.
- [ ] Formula error count is zero.
- [ ] Special blocks verified: CAD sites, BRL Google Ads, Fincgriffin, Creditoparaveiculo, Openzed Ícaro.

## Reference files

- `references/august-2026-dashboard-formula-audit.md` — dependency closure, confirmed semantic defects, staged repair order, and first validated one-cell correction for the August dashboard preflight.
- `references/june-2026-fill-audit.md` — June 16–29, 2026 live fill lessons, mappings, correction of row 35, and audit results.
- `references/monthly-rollover-formula-audit.md` — July 2026 rollover prep notes: formula inventory across main + manager sheets, `A3` month-number dependency, column `B` date rebuild, `CAIXA SINTETICO` month-column shift, and Sheets API batching pitfall.
- `references/july-2026-1-6-fill-audit.md` — July 1–6, 2026 live fill lessons: reconciled totals, formula-column restore pitfall, Fincgriffin date-serial validation, and final validation standard.
- `references/june-2026-live-structure-rebaseline.md` — live June redesign versus the prior rollover baseline: Fincgriffin US columns, manager-specific spend slots, CreditoParaVeiculo slot expansion, six `G001`–`G006` daily blocks, and mandatory live rebaseline before rollover.
