---
name: monthly-finance-sheet-fill
description: Use when filling or auditing MGS monthly finance Google Sheets, including approved Long revenue/spend data, recurring company-expense checks, site/currency mapping, backups, and cell-level validation.
version: 1.0.25
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, finance, google-sheets, revenue, spend, reconciliation, audit]
    related_skills: [revenue-spend-reporting-pipeline]
---

# Monthly Finance Sheet Fill

## Purpose

Use this skill when Rodolfo asks to fill or audit an operational monthly finance sheet, including a cross-month check of a recurring company expense, or to populate a monthly tab from an approved `Long` table or Excel report.

This is not the same as generating the `Long` report. The job here is to inspect or write the existing operator-facing monthly sheet structure without damaging formulas, dates, currencies, totals, or manual exception blocks.

## Non-negotiable rules

1. **Backup before writing.** Save the touched range or full sheet snapshot with formulas and formatted values before any update.
2. **Map by real date, not row arithmetic alone.** Verify the month length. For June, never write to a day-31 row. If a template has formulas beyond the month, treat them as out-of-scope unless Rodolfo explicitly asks.
3. **Preflight all target columns.** Confirm every source site/account maps to a destination cell before writing. If anything is unmapped, stop before partial write.
4. **Respect revenue currency.** Some sites take raw `GROSS_USD_*`; some take raw `GROSS_CAD_*` and compute USD next to it.
5. **Respect spend currency.** Meta/Business Manager spend usually goes to `BM - $`; Google Ads BRL goes to `Google Ads - R$`.
6. **Audit after writing.** Compare expected source values to sheet cells cell-by-cell, not only by totals. Check formula errors and out-of-period rows.
7. **Do not call success until verified.** Report mismatches honestly and fix if safe.
8. **Use the canonical Service Account exclusively.** Load short-lived Sheets tokens through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`, require `mgsagent@mgs-core-prod.iam.gserviceaccount.com` in `mgs-core-prod`, send the Service Account quota project, and require Sheets HTTP 200 plus destination writer access before any authorized write. This supersedes the historical personal-OAuth rollback exception: personal tokens, client secrets and alternate identities are permanently retired, including as rollback/fallback. Fail closed if the canonical Service Account is unavailable; credential changes still require their separate Critical Subset confirmation.

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

## Cross-month recurring company-expense audit

Use this read-only path when Rodolfo points to one amount in `Despesas da Empresa` / `Despesas Gerais` and asks which months list the charge.

1. Validate the exact workbook through Drive and Sheets with the canonical Service Account, then resolve any supplied `gid` to its live tab title. Never infer the tab from the URL or workbook name.
2. Read the smallest expense block that contains the selected row with `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE`. Identify the charge by **normalized label + manual origin amount + origin currency/formula chain**; an amount such as `97` alone can match unrelated cells or a converted result.
3. Retrieve and report only the label and the input cells required to prove amount/currency. Read a units/CAD helper cell only when its formula chain makes it the origin, and never dump neighboring notes or unrelated columns because finance rows can contain banking or access-sensitive text.
4. Enumerate every monthly tab in the exact principal workbook and scan each one for the normalized label and matching origin amount. Re-discover the live row/columns per tab because layouts drift; order the result chronologically and state `matched months / monthly tabs scanned`.
5. If the requested period predates the principal workbook's tabs, do not report those months as absent. Inspect accessible manager-tab formulas for literal `IMPORTRANGE` spreadsheet IDs to locate the historical principal, then validate that exact file on both Drive and Sheets surfaces with the canonical Service Account. Manager tabs establish lineage only: their totals and site imports do not prove whether a detailed company-expense row existed.
6. If the historical principal is not accessible, fail closed: do not use personal OAuth, browser identity, public CSV or `gviz` as a fallback. Report the months confirmed in the accessible workbook, the missing historical scope, and the exact canonical Service Account that must receive file access.
7. Finish with the charge label/value, explicit month list, count, source scope, and whether any write occurred. Never imply a full multi-year result when only the current workbook was readable.

## Retrospective reclassification of a prepaid cost as direct site consumption

Use this path when a payment/recharge was historically recorded in `Despesas Gerais`, but the consumed cost belongs directly to one site or manager operation.

1. Work one month at a time, principal workbook first. Freeze `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for the expense row, rateable-expense totals, target site summary, manager remuneration rows, and every linked manager summary before proposing an edit.
2. Separate cash evidence from accounting consumption. A recharge/payment proves cash movement; the vendor's authenticated consumed quantity and unit cost prove the period expense. Use consumption in the monthly result and keep the recharge/payment in the cash trail. Reconcile a cumulative scope as `opening vendor credit + recharges or credits advanced − closing vendor credit = consumption`; when exact opening/closing credit is unavailable, preserve the difference explicitly as timing, prepaid balance or payable instead of forcing equality. A later payment clears that balance and is not a second expense in the payment month.
3. Preserve the historical recharge row visibly for partner review. Relabel it as payment/recharge and explicitly mark it non-rateable; exclude that row from the formulas that total the common expense pool instead of deleting or zeroing the evidence.
4. Recalculate the common pool with every other General Expense unchanged and Creditoparaveiculo preserved as one active site unit. Do not multiply its ordinary one-site share by the number of G codes.
5. Add consumed SMS as a direct Creditoparaveiculo expense using actual G001–G006 attribution. Record the consumed total exactly once in the top CPV/company summary; the six G blocks are attribution-only and must not feed the company total a second time. G002 is MGS: its consumption reduces the CPV/MGS site result only, never enters the common manager rateio and never creates external commission. **If the owner/company close is a component-based synthetic summary instead of a sum of final site profits, updating the CPV site profit alone does not propagate the direct cost:** add a separate visible direct-SMS component to that summary and include it exactly once in the final-profit formula, while keeping it out of the rateable General Expenses component. When a direct cost is appended to a manager block's monthly expense total instead of its daily rows, also recompute monthly profit as `monthly net + monthly tax + monthly spend`; leaving profit as an unchanged sum of daily profit omits the direct cost. Keep any unresolved consumption explicitly unallocated rather than distributing it.
6. Trace the direct cost through every downstream company close before accepting the month. A component-based synthetic summary may recompute profit from revenue, tax, media, common expenses and payroll instead of summing site profits; adding the cost only to the site's result then leaves the company close overstated after the recharge is removed from the common pool. Add a separately labeled direct-cost component to that summary and include it exactly once in company profit. Reconcile the bridge explicitly: the company result should move by `consumption − recharge` plus remuneration deltas and independently verified source drift—not by nearly the full recharge amount.
7. Let the principal-sheet correction propagate through `IMPORTRANGE`; read the manager workbook first, then reread the principal payroll row after cache propagation before declaring the commission. The first principal read can still hold the prior imported value and is not authority to hardcode a result. Reconcile three distinct figures before naming a commission: the live formula result, the frozen paid/due baseline, and any case-specific waiver already approved. A manager tab may project the month from elapsed/filled days, so derive the displayed impact from its formula or live readback rather than subtracting raw cost from the displayed estimate. If the three bases disagree, stop at that manager and ask which basis controls; never revoke a waiver, restore an old payment, or hardcode a manager result merely to make the visible total match.
8. If Rodolfo requires explicit partner-facing disclosure, first prove the target cells are blank, unmerged and outside every sum/import range. Add a text-only disclosure showing `retirada do rateio`, `consumo direto`, `efeito no resultado` and the governing commission basis; do not enter a second numeric adjustment when the financial effect already propagated through `IMPORTRANGE`. When only these texts remain across the five manager workbooks, Rodolfo permits Zeus to batch-write them: back up all targets, run one blank-cell write/read/clear/restore canary, use `RAW`, reread every target, require the formula scope-diff to contain only the intended text cells, and scan all five tabs for displayed formula errors.
9. For manual guidance, provide the exact workbook/tab, cell or bounded range, current value/formula, replacement, reason and expected dependent total. Present one logical correction at a time. Recompute each expected dependent total from the live post-step state: removing a charge from the common pool also refunds the target site's own ordinary rateio share, so a pre-rateio subtotal is stale. Freeze an expected-cell manifest containing **every** named label, amount, formula, status and annotation cell from the instruction. Treat **“feito, confere”** as the standing trigger to read back that full manifest in `FORMULA`, `UNFORMATTED_VALUE` and `FORMATTED_VALUE`, plus the smallest dependent range; a trailing cell omitted by the Sheets Values API is blank and therefore a mismatch, never implicit success. Report `PASS` only when every manifest cell matches, otherwise report the exact missing/wrong cell, and immediately give the next confirmed step without asking permission again.
10. Close the month only after principal totals, site result, synthetic/company summary, all manager summaries, remuneration and the principal→manager→principal payroll feedback chain reconcile. For a multi-month SMS correction, keep actual historical payments immutable and carry monthly commission deltas into the September payment as a separately labeled `Ajuste SMS Funnel — maio a setembro`; show September's own commission, the consolidated adjustment and the final payment separately, and include September's delta exactly once. When the live Sheet formula differs from what was actually paid, disclose both; use the actual paid baseline for settlement without forcing the live formula to match. Move to the next month only after that month's delta is sealed. Reconcile the dashboard afterward as a separate phase; Sheet authorization does not authorize a dashboard write.

Pitfall: do not zero the old recharge row merely to stop rateio, because that erases the cash trail and makes partner review ambiguous. Preserve the row and remove only its participation in the common-pool total.

Pitfall: do not use a disclosure row as a balancing entry. The disclosure explains a correction already carried by formulas; a second numeric value silently double-counts it.

Pitfall: do not expect recharge totals and consumed cost to match month by month. Vendor credit can cross month boundaries; validate cumulative consumption and preserve the prepaid/payable bridge instead of moving usage into the recharge month.

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
2. Main sheet column `B` stores repeated daily date blocks, not just the first visible month block. Scan the **full live used range** for every month label and date run before rebuilding; lower operational blocks can extend beyond row 200, so a historical row limit is not a closure bound. Update every repeated month label and date sequence, but populate a day-31 row only when the target month actually has 31 days. Preserve the source visual number format, e.g. `dddd, d` showing `Monday, 1`, rather than leaving raw `dd/mm/yyyy`.
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
12. A clean target month can expose aggregate formulas that only worked because the source month had data. After clearing inputs, scan the full target range for errors. For empty-set `AVERAGEIF` totals such as `AHB36`/`AHC36`, use an empty-safe equivalent (`IFERROR(..., "")`) in the target and include those cells in the authorized scope diff.
13. Audit every copied month literal, prior-month tab reference and explicit day divisor across the full used range. A carry-forward balance must point to the immediately preceding monthly tab and that tab's live subtotal cell; copied labels such as `MES <mês anterior>`, lower-block month labels, `/31`, or a hardcoded elapsed-day projection must be reconciled to the target month. If the source data is not materially populated through the claimed day, keep the month provisional and report the incomplete scope instead of relabeling it as closed. When an authorized repair mixes deterministic rollover fixes with a projection whose divisor depends on business completeness, apply only the deterministic cells in the bounded transaction, leave the projection formula unchanged, and ask the exact close-versus-estimate decision afterward; do not let the ambiguous projection block safe corrections or silently convert an estimate into a close.

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

## Dashboard-to-Sheet closing alignment

**Owner visual fidelity — Rodolfo1555301641287114806:** a financial fill is not permission to replace the owner's workbook design. Use the approved prior-month tab as the live visual reference: colors by metric, fonts, accounting formats, zebra, total bands, borders, widths/heights, gutters, country order and block placement. Extend missing blocks in that same pattern. Financial parity alone does not finish the task. Compare actual target renders with the reference before closure; never declare a generic dark-header replacement visually complete from API structure counts alone. See the visual-safety section in `references/dashboard-to-sheets-native-export.md`.

For a native application → principal/manager/Caixa export, load `references/dashboard-to-sheets-native-export.md`: immutable source revision, native+legacy facts, original currencies/account spend, complete per-manager attribution, same-month provisional FX, locale-safe formulas, cross-workbook propagation and exhaustive independent readback. Never use stale legacy cash rows as the native application total.

For a reverse export requested as “analyze before applying”, capture all exact target gids and the live monthly dashboard revision read-only; do not run even a Sheet write canary before approval. Inventory missing site/country blocks and manager-summary coverage before estimating the write. Native revenue and shared-site attribution may have no legacy Sheet coordinates: preserve manager/site/country/date/currency grain instead of copying whole-site totals to every manager. Compare expense origin amount/currency and active/archive state, not only converted totals; an archived row's retained edit amount is not an active charge. Check manager FX month references and the monthly Caixa column separately. Quantify IMPORTRANGE cache/volatile-rate deltas under a common FX snapshot before diagnosing formula corruption. Keep the application, prior months, payment ledger and automatic-sync configuration outside a one-time Sheet export unless explicitly authorized.

- Apply confirmed rate values and repair the full source-network formula closure, including lower manager blocks and the monthly payout parameter. Do not fix only visible top daily rows; an unchanged lower invalid reference can leave manager commissions on the old network.
- After a principal write, verify the principal→manager IMPORTRANGE→principal payroll chain before diagnosing a mismatch. Read each affected manager's actual summary, then reread the principal; cached old payroll in the first response is not permission to hardcode salaries or rewrite unchanged formulas.
- Compare the displayed closing balance, company profit, partner share and each remuneration separately. A matching final balance does not prove all intermediate displays match: raw Sheet sums and a cent-based payment ledger can round differently near a half-cent boundary. Preserve the exact residual and its source; never use ROUNDUP, a hidden balancing constant, a fabricated ledger item or changed gross merely to force visual parity.
- If the owner subsequently authorizes the exact residual cent adjustment, distinguish it from a hidden balancing change: retain the base formula, record the bounded adjustment and authority in the cell note, preserve the old formula in the backup, and read back every dependent displayed receipt and balance. Treat it as that closing's explicit exception, never as a new revenue fact, a global rounding policy or a adjustment to copy into a later month.
- Restrict logged evidence to explicit financial cells. Full private formula backups can include sensitive notes; never print neighboring note columns while diagnosing expenses or payroll.

## Manual close versus synthetic-summary reconciliation

Use this path when an operational closing cell must match a far-right or dashboard summary derived from header-driven aggregates:

1. Resolve the supplied `gid` to the live tab and discover both comparison cells from labels, units, and formula semantics. The operational USD close is the cell that sums site closing profits plus approved company/payroll adjustments; a neighboring `Total` cell may only convert that value to BRL. Discover the synthetic total from the `LUCRO LIQUIDO TOTAL` header whose machine-header cell is blank, rather than assuming fixed coordinates across months.
2. Read both target cells with `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE`; calculate the exact raw delta before inspecting broad ranges. Treat floating residues below display precision as parity only after every underlying contribution also reconciles.
3. Decompose both sides to the same grain. Enumerate every site-profit reference and non-site adjustment in the operational formula. On the synthetic side, enumerate every live `LUCRO_LIQUIDO_TOTAL` block, including lower blocks, and separately read the final component totals for revenue, tax, company expense, payroll, invalid traffic, and spend.
4. Pair site blocks by live header semantics and block order, not historical coordinates. Compare every site contribution programmatically and require equal paired counts with no unpaired cells. Reconcile the headline delta as an explicit identity: `site-profit deltas + synthetic invalid adjustment + non-site adjustment difference + synthetic daily-vs-component anomaly`.
5. Independently compare the synthetic profit total with the sum of its own component totals and compare each component total with the sum of its daily band. This catches a missing daily formula, an out-of-month allocation, or a row-36 formula that counts a different number of days even when the headline difference can otherwise be explained.
6. For each mismatched site, trace the manual chain from gross revenue through invalid traffic, rev share/discount, tax, campaigns, and additional expense. Inventory every active regional group from live `GROSS_*`, `NET_*`, `IMPOSTO_*`, and `GASTOS_*` headers. Flag asymmetric coverage when revenue omits a region but `GASTOS_TOTAL` still includes its costs; compute the omitted region's full net-plus-tax impact, not just gross.
7. Validate formula meaning, not only references. A tax column must be a negative function of the corresponding net column; reject a copied positive net formula even if the range is syntactically valid. Compare hardcoded monthly totals with the daily cells that feed downstream net formulas, because a manual override can make the closing block and daily summary use different gross bases.
8. Treat percentage drift as a business-rule conflict. When a manual close uses a site-specific parameter but daily formulas use the global parameter, report both exact cells, labels, values, and impacts; do not silently choose one merely to force parity. Likewise, distinguish these two invalid-traffic models: subtract invalid before discount/tax versus calculate discount/tax first and subtract invalid later as a separate expense. They are not arithmetically equivalent.
9. Distinguish authority from arithmetic. A summary-only area is not automatically the source of truth, but it can expose an upstream omission in the operational close. Report PASS months first, then for each failed month give the operational cell/value, synthetic cell/value, signed delta, exact formula families responsible, and whether a business decision remains.
10. Before a repair sequence that can change manager remuneration, freeze a pre-repair commission baseline across every requested month. Discover rows from live labels matching `*- Gestor:`, capture the signed USD and BRL cells plus formulas and coordinates, preserve blank versus formula-derived zero, exclude neighboring banking/payment notes, require the same manager count per month, and seal the snapshot with a verified SHA-256. Re-read the identical keys after all repairs and report manager/month deltas; never reconstruct the baseline from post-repair totals.
11. Reconcile invalid traffic by payment semantics, not by a balancing residual. When invalid traffic reduces the payable base before rev share and tax, its synthetic-summary effect is `invalid_amount × (1 − rev_share_rate) × (1 − tax_rate)`. Group invalid cells by their live rev-share parameter, include every active network/category, keep raw-invalid category totals intact, and feed a separate adjusted-invalid total into the synthetic expense column. Prove that the derived adjusted total equals the exact amount required for operational-summary parity; never insert a constant chosen only to make the totals match.
12. Respect the real month length on both sides of the reconciliation. Compare each synthetic component's daily-band sum with its row-total formula, then scan **all** out-of-month daily cells: site `DESPESA_TOTAL`, synthetic payroll, invalid-traffic allocation, profit and other non-site components. In a 30-day month, a day-31 formula can lower either the operational close or only the synthetic summary even when all site pairs match. Clear or guard only the out-of-month cells, disclose which side changes, and revalidate both totals. When paired site counts are equal with zero site deltas but the headline still differs, inspect non-site daily allocations first rather than reopening every site.
13. Detect combined-gross double counting before changing totals. If a daily gross column contains combined regions while a second regional gross column is also populated, downstream NET must use `(combined_gross − regional_gross)` for the first region before the regional NET is added separately. Replace a hardcoded compensating total with a formula over the same daily sources, and require every tax column to reference its corresponding NET with a negative tax formula.
14. Do not write during a diagnosis-only request. If repair is authorized, freeze `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for every target and dependent receipt, exercise one blank-cell canary with write/read/clear/restore, and use one atomic `updateCells` transaction for the pending cells. Immediately before writing, classify each target as **diagnosed old value**, **already equal to the authorized target**, or **unexpected third value**: skip already-correct cells without replay, stop on any third value, and never overwrite a concurrent authorized correction. Make the post-write formula-scope diff equal exactly the cells that were still pending, retain the frozen pre-write mapping for rollback, then read back every row in any fill-down range plus dependent site profit, component totals, operational close, synthetic summary, and any preserved commission baseline. Require exact raw-value parity, zero displayed errors, equal site-pair counts, and a restored blank canary before reporting success.
15. Recompute the expected close after every repair batch instead of reusing the pre-repair target. A principal formula correction can flow through a manager workbook by `IMPORTRANGE`, cross a minimum-versus-percentage commission threshold, change that manager's USD/BRL remuneration, and flow back into the principal payroll total. When operational close and synthetic summary match but both moved, compare the live manager cells against the sealed baseline, identify the exact manager/month/currency delta and threshold drivers, and classify the movement as a legitimate feedback-chain change rather than a forgotten formula. Require all unaffected managers to remain unchanged. For the final settlement comparison, read every frozen manager key twice and require cent-stable BRL results; treat BRL as the payment source and USD as analytical evidence that can move with exchange-rate formulas. Because commission expense cells are normally negative, normalize `payable = -signed_cell` and calculate `settlement_due_to_manager = current_payable - baseline_payable`: positive means MGS must pay more, negative means MGS has a credit or the manager owes MGS **only when the baseline amount was already paid**. Report current values by month, changed records, totals by manager and month, gross additional payments, gross credits and the reconciled net; never offset people automatically or execute a payment from this audit, because payment actions require their separate authorization gate. Seal the comparison artifact with SHA-256 and prove manager-sum, month-sum and grand-total parity.
16. When Rodolfo explicitly waives the resulting differences as immaterial, close the case without changing commission cells, formulas, payments, credits, or balances. Preserve the waiver as a **case-specific disposition**, never infer a reusable materiality threshold or future commission policy. Seal a closure receipt that links the authority, baseline and final comparison hashes; record gross waived additions, gross waived credits, the reconciled net, and `financial_transactions_executed = 0`; then mark the initiative checkpoint final with no next step unless Rodolfo explicitly reopens it.

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
- **Google Sheets bar-chart axis:** In `spreadsheets.batchUpdate`, a `BAR` basic-chart series must target `BOTTOM_AXIS`; targeting `LEFT_AXIS` returns `INVALID_ARGUMENT`. If a structural build fails, delete only the newly created sheet IDs, verify the target titles are absent, revalidate frozen source hashes, then retry the corrected build.

## Dashboard preflight and recursive formula audit

Before creating a finance dashboard or treating an existing ROI summary as authoritative:

1. Bind the dashboard to explicit source tabs. Existing summary/dashboard tabs are only hints until their coordinates and headers are reconciled against the live monthly structure.
2. Snapshot `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for every in-scope tab; hash the snapshots before any write.
3. Inventory every formula cell and every referenced range. Resolve `IMPORTRANGE` recursively until every external spreadsheet ID, tab, target range, and callback dependency is known. An unresolved external source blocks the dashboard.
4. For satellite manager workbooks, validate the exact file ID and `gid`, compare every imported spill cell against the principal source, verify the manager summary mappings, and independently recompute commission/estimate outputs.
5. Apply the MGS exchange-rate lifecycle instead of treating a live rate after calendar month-end as a defect:
   - `F1` follows the same provisional-to-actual lifecycle as the other active exchange rates. The live formula belongs to the matching month cell in `CAIXA SINTETICO` (`J2` for August 2026), while `F1` only references that cell.
   - `H1` is the provisional USD/CAD conversion for Rede1 sites whose GAM settlement currency is CAD but whose payout is received in USD.
   - `I1` historically represented the GBP lifecycle for YMonetize, but YMonetize is retired. Keep the current fixed compatibility value while its blocks are zero/inactive; do not restore a live GBP formula. The affected sites are planned for migration to Rede1.
   - These cells intentionally remain estimated/dynamic until the partner payment, normally between days 21–25 of the following month.
   - When the payment proof arrives, Rodolfo manually replaces the estimate/formula with the actual settlement rate including the spread shown in the proof. Only then is the month financially closed.
   - Never freeze these rates merely because the traffic month ended, and never classify the intentional pre-payment formulas as formula drift.
6. Never roll a summary forward by replacing only the month name when the monthly sheet width or block order changed. Re-map by live site/header semantics and validate each metric header against its source cell.
7. Audit daily formula continuity, missing day formulas, one-cell pattern outliers, total formulas, and semantic identities: invalid traffic, net revenue, tax, spend, profit, ROI Gross, and ROI Net. A zero formula-error count does not prove semantic correctness.
8. For `ROI_GROSS_TOTAL`, require every USD-normalized gross component intended by the block; for `RECEITA_NET_TOTAL`, require net components rather than gross components. Report omissions with cell-level impact before proposing repair.
9. Formula scanners must normalize A1 column letters to uppercase before converting them to numeric indices; lowercase ranges in live `IMPORTRANGE` formulas otherwise create false parity failures.
10. Build the normalized dashboard base only after external-source closure, current spill parity, zero formula errors, and disposition of every confirmed semantic divergence. Keep source tabs untouched unless a separately reported repair is authorized.
11. When one normalized base mixes monthly site facts, monthly country facts, daily global facts, and an authoritative monthly closure, add an explicit grain discriminator such as `Nível`. Executive totals must select only the intended grain; never sum site and country rows together.
12. Do not duplicate one site's financial metrics once per manager. For multi-manager sites, keep one financial row, classify ownership as shared, and retain the validated manager list in a separate dimension. Leave unknown ownership explicit rather than guessing.
13. Treat dashboard creation as a reversible structural transaction: freeze source formula hashes, back up workbook metadata and source renders, exercise an add/read/delete sheet canary, create only the new dashboard tabs, and retain their returned sheet IDs for exact rollback.
14. Validate the finished dashboard independently: source hashes unchanged, normalized totals recomputed against source totals, KPI parity, zero displayed errors, exact chart/filter counts, one live filter probe, and restoration of that filter's original value.

For the reusable Google Sheets dashboard build transaction, data-grain model, chart-axis rule, rollback, and independent verification pattern, see `references/google-sheets-finance-dashboard-build.md`.

## Stepwise manual formula repair with Rodolfo

When Rodolfo asks to proceed “por partes”, treat that sequence as an execution boundary, not a presentation preference:

1. Freeze the current tab/order exactly as stated. If `CAIXA SINTETICO` was deferred until last, do not discuss, inspect for action, or request decisions about it while repairing the monthly tab.
2. Present exactly one confirmed problem at a time: cell/range, current formula or state, why it is wrong, and the exact smallest edit. Do not bundle later findings or repeat the full audit.
3. Rodolfo performs the manual edit unless he explicitly delegates the write. Never broaden a one-cell correction into fill-down or neighboring changes.
4. Before giving a formula for manual entry, read the target spreadsheet locale and render decimal literals with that locale's separator (`pt_BR` requires decimal comma; `en_US` uses decimal point). If Sheets reports a parse error, read the target's `effectiveValue.errorValue`, correct only that formula, and validate every dependent cell that inherited the error before continuing.
5. After he says the edit is complete — especially with the standing phrase **“feito, confere”** — read back `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE` for the target plus the smallest dependent range. Compare the formula to adjacent-row/column semantics and require no displayed error.
6. Report only `PASS` or the exact remaining mismatch. Once Rodolfo has authorized the stepwise correction sequence, a successful readback must be followed immediately by the next confirmed problem in the same response; do not ask “posso passar ao próximo?”. Pause only when validation fails or a genuine business decision is required, and state the conflicting live/historical bases before asking the exact question.
7. Keep a compact correction ledger so the later scope-diff can prove that every changed cell was intentional and no deferred tab was touched.
8. For a fill-down repair, prove the whole target range shares one semantic formula family before instructing it. On readback, verify every row (`N/N`) contains the expected row-matched references; checking only the first and last cells is insufficient.
9. Read KPI driver cells as exact individual ranges in one `batchGet` before calculating impact. Do not infer positions from a wide sparse response, and do not quote a cached impact when `GOOGLEFINANCE` or another volatile dependency can change it.
10. Even when several sites share the same defect class, preserve the one-problem cadence. Validate the completed site, report its final KPI, and then present exactly one next site/range.
11. If Rodolfo explicitly switches from “por partes” to “lista todos”, stop the one-problem cadence and give one complete audit in repeated `Site` / `Problema` / `Solução` bullets. Separate true site-local defects from global summary defects so he does not edit dozens of sites to repair one aggregate rule; include exact ranges and the smallest safe formula family for each local defect.

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
- `references/google-sheets-finance-dashboard-build.md` — reversible dashboard-tab creation, normalized mixed-grain modeling, non-duplicating manager dimensions, chart-axis constraints, filter probe/restore, and source-preservation verification.
