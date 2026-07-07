# June 2026 finance sheet fill audit

## Context

Rodolfo provided an approved `Long` workbook for 2026-06-16 through 2026-06-29 and asked Zeus to fill the live Google Sheet `MGS - Receita dos Sites 2026`, tab `Junho 2026`.

The task exposed a distinct class of work: converting approved Long data into a complex operational monthly sheet with many site blocks, currencies, spend-account labels, manager sub-tables, and formulas.

## User corrections and expectations

- Rodolfo expects slow, careful, detailed validation for finance sheets. Speed is less important than not corrupting the sheet.
- A backup tab/copy may exist, but that is not permission to be careless.
- The agent must map dates by real calendar day and month length. For June, line/day 31 is out of scope.
- If a row outside the period changes, the correct diagnosis should start from the agent’s write/mapping logic, not blaming the template.

## Key mapping confirmed by Rodolfo

### Revenue CAD gross

Fill raw `GROSS_CAD_*` for:

- `financeadx.com`
- `helixenit.com`
- `infinitynexx.com`
- `marevelx.com`
- `vizioid.com`
- `xyvlov.com`

### Revenue USD gross

Fill raw `GROSS_USD_*` for all other confirmed sites in this cycle, including:

- `openzed.com`
- `finanzas.openzed.com`
- `gamezonead.com`
- `fincgriffin.com`
- `creditoparaveiculo.com`
- normal MGS credit/job/finance sites

`gamingadx.com` had no revenue in this cycle; Rodolfo said he would ask SB.

### Spend BRL

- `gamezonead.com`: Google Ads account `Mattei 1`; fill `Google Ads - R$`.
- `gamingadx.com`: Google Ads account `Gamingadx-US-01`; fill `Google Ads - R$`.

### Spend USD

All other confirmed spend sites go to `BM - $` unless Rodolfo changes the account/currency mapping.

## Special blocks

### Openzed Ícaro

`NF100` is a separate `Openzed` block:

- `NF100`: `ICARO - G001-D`
- `NF102`: `GROSS_USD_US`
- `NM102`: `GROSS_USD_GB`

Openzed `g001-d` revenue belongs in this lower Ícaro block, not collapsed into the main Openzed block.

### Fincgriffin

Rodolfo uses a lower mini-table around `TQ100:TV185`:

- Summary rows by gestor.
- Detail rows: `Data | Gestor | Gasto | Receita | Lucro | Margem`.
- Continue the detail table for the new period, then aggregate to the top `Fincgriffin US-CAR-EN` column.

Formula correction learned: summary `Lucro` should be `Receita - Gasto` using the actual summary columns; wrong column references can create `#REF!`.

### Creditoparaveiculo

Sum all related FB accounts and write to `Creditoparaveiculo BR-CAR-BR`:

- `Creditoparaveiculo-BR-CAR-BR-01`
- `Creditoparaveiculo-BR-CAR-BR-01-G003`
- `Creditoparaveiculo-BR-CAR-BR-01-G005`
- `Creditoparaveiculo-BR-CAR-BR-02-G002`

July 2026 correction: also maintain a lower gestor mini-table for Creditoparaveiculo starting at `ABL100`, mirroring the Fincgriffin pattern:

- Summary rows: `ABL102:ABP108` with `Gestor | Gasto | Receita | Lucro | Margem`.
- Detail rows: `ABL111:ABQ180` with `Data | Gestor | Gasto | Receita | Lucro | Margem`.
- Summary formulas: `Gasto` and `Receita` via `SUMIF` over detail `Gestor`; `Lucro = Receita - Gasto`; `Margem = IFERROR(Lucro/Gasto, "")`.
- Top `Creditoparaveiculo BR-CAR-BR` daily block remains aggregated; lower table exposes gestor split.

### Google Ads BRL spend formula preservation

For `gamezonead.com` and `gamingadx.com`, the `Google Ads -R$` input column has a neighboring USD formula column that converts BRL using `$E$1` (examples: `AAG46 = SUM(AAH46/$E$1)`, `AAV46 = SUM(AAW46/$E$1)`). Never clear or overwrite the USD formula column when filling BRL spend; only write into the BRL input column. If a broad clear touches the formula column, restore formulas from the pre-write backup before validation.

### Zero-looking cells in future dates

Some duplicated month tabs already contain literal `0` values in future-date revenue input cells (observed July 2026: Lyzmo `HF11`, FinanceAdx AR `RN29:RN32`, Ducapes `SL32`, Ducapes Finance `TA30`). Before attributing a `$ -`/`0.00` display to the current fill, compare against the pre-write backup/formula render. Report whether the value was pre-existing versus created by the fill.

### Mini-table ROI/margin formulas

When writing lower detail tables such as Fincgriffin `TQ111:TV...` or Creditoparaveiculo `ABL111:ABQ...`, the margin/ROI detail column should be a formula, not a static blank/value: `=IFERROR(Lucro/Gasto, "")` using that row's detail columns. Validate the formula exists after writing, especially when `Gasto = 0` causes the displayed margin to be blank.

## Error encountered and permanent lesson

A row-35 issue occurred. June has only 30 days, so row 35 must not be written or treated as part of June’s daily data. The agent initially framed it as a “day 31 phantom formula” issue, but Rodolfo corrected the reasoning: the operational error was the agent allowing out-of-period contamination. Future fills must explicitly validate:

- source date range,
- target month length,
- destination rows,
- and post-write non-empty cells outside the allowed date range.

## Audit pattern used successfully

Post-write audit should compute expected values from the source `Long` and compare to live sheet cells:

- Build expected revenue cells by `(Data, Site, Vertical/Gestor exception)`.
- Build expected spend cells by `(Data, Conta_FB)` or aggregate rule.
- Compare rounded values cell-by-cell.
- Check unmapped source rows.
- Check unexpected non-zero target cells in mapped ranges.
- Check row outside period/month.
- Check formula errors in full sheet.
- For Sheets date cells read with `UNFORMATTED_VALUE`, convert serial numbers using epoch `1899-12-30` before declaring mismatch.

Final corrected audit for June 16–29 returned:

- Expected cells: 853.
- Cell mismatches: 0.
- Unmapped revenue rows: 0.
- Unmapped spend rows: 0.
- Row 35 non-empty cells: 0.
- Formula errors: 0.
- Fincgriffin mini-table mismatches after date-serial conversion: 0.
