# July 2026 day 1–6 master fill audit

## Context

Rodolfo provided workbook `report_1_de_julho_ate_6_de_julho.xlsx` and asked Zeus to update the live master sheet `MGS - Receita dos Sites 2026`, tab `Julho 2026`, for `2026-07-01..2026-07-06`.

The workbook contained:

- `report SB-1`
- `report SB-2`
- `report AV`
- `MonetizeMore`
- `Gastos FB`
- `Gastos Google`

The existing `process-revenue-spend-report.py` pipeline generated reconciled `Long.csv` successfully.

## Reconciliation facts

Validated totals from the source workbook and mapped sheet writes:

- Receita fonte: `34,115.27`
- Receita lançada: `34,115.27`
- Gasto fonte: `45,900.80`
- Gasto lançado: `45,900.80`
- Expected mapped cells: `282`
- Fincgriffin detail rows: `29`
- Formula errors after final validation: `0`
- Cell mismatches after final validation: `0`

Local audit path used in session:

- Backup: `/root/mgs-agent/work/july-2026-fill-1-6/backup-before-master-fill-20260707-121130.json`
- Final validation: `/root/mgs-agent/work/july-2026-fill-1-6/final-validation-after-restore.json`

## Mapping and special handling confirmed by execution

- `Openzed / ICARO - G001-D`: `openzed.com` + `g001-d` revenue is written to the lower Ícaro block, not the principal Openzed block.
- `Fincgriffin`: populate the lower detail table by `date + gestor`, then the top summary formulas pick it up.
- `Creditoparaveiculo`: aggregate FB spend variants into the single `Creditoparaveiculo BR-CAR-BR` block.
- `Gamezonead` / `Gamingadx`: Google Ads BRL spend goes into `Google Ads -R$` columns.
- CAD sites use CAD manual gross columns (`financeadx`, `helixenit`, `infinitynexx`, `marevelx`, `vizioid`, `xyvlov`).

## Operational pitfall discovered

A broad clear strategy can accidentally wipe formulas in columns that are manual input in one band but formula-derived in another band.

In this July fill, formula columns touched by broad clear/write logic included examples such as:

- `AAH`
- `AAW`
- `VM`
- `NI`
- `NP`

Corrective pattern:

1. Backup formulas and formatted values before writing.
2. Build the write/clear set from confirmed manual input cells only.
3. After batch update, validate both expected value cells and formula parity for any column that might have formulas.
4. If formulas were touched, restore them from the backup with `valueInputOption=USER_ENTERED`.
5. Re-run final validation before reporting success.

## Fincgriffin date validation pitfall

Sheets API `UNFORMATTED_VALUE` returns date cells as serial numbers. During Fincgriffin detail-table validation, values such as `46204` were correct serial dates for `2026-07-01`, not mismatches. Convert using epoch `1899-12-30` before comparing.

## Final validation standard used

A fill is complete only when all of these are true:

- raw source revenue equals mapped revenue;
- raw source spend equals mapped spend;
- every expected target cell matches by readback;
- Fincgriffin detail rows match after date-serial conversion;
- formula error count is zero;
- any formula columns touched during the batch match the pre-write backup formulas.
