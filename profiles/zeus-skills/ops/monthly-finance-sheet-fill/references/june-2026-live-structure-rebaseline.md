# June 2026 live-structure rebaseline before future rollovers

## Why this reference exists

On 2026-07-14, Rodolfo deleted the previously generated `Julho 2026` tab because `Junho 2026` had since been structurally redesigned. The old rollover backup ended at `AGX275`; the live June tab had active content through `AHF338`. A future rollover must therefore use the live source tab as its structural baseline, not the earlier July scripts/backups.

## Confirmed structural changes

### Fincgriffin top block

- Added a complete US segment: `GROSS`, `NET`, `Imposto`, `Gastos`, `Lucro Líquido`, `ROI Gross`, `ROI Net`.
- This widened the sheet by eight columns overall (seven data columns plus structural spacing/shift).
- Fincgriffin spend rows now have dedicated direct-USD manager/account slots for `G001`–`G006` before the remaining GB/TR/ES slots.
- Do not restore the old generic alternating `BM - $ | R$` layout over these manager-specific US slots.

### CreditoParaVeiculo top spend block

- The site block shifted from the old `ABK...` area to the live `ABS...` area because of the Fincgriffin insertion.
- The old layout had five generic `BM - $` slots interleaved with five `R$` conversion columns.
- The live layout has ten direct `BM - $` slots, with account/manager labels mapped across `G001`–`G006`.
- Treat current labels and positions as source-of-truth; do not use old fixed addresses.

### Lower daily blocks, rows 100–338

The old Fincgriffin lower area had one consolidated monthly summary plus a flat detail table (`Data | Gestor | Gasto | Receita | Lucro | Margem`). CreditoParaVeiculo had no parallel daily structure.

The live June structure instead has six independent 40-row manager blocks for **both** sites:

- `G001`: manager label row 101; header row 103; total row 136.
- `G002`: label 141; header 143; total 176.
- `G003`: label 181; header 183; total 216.
- `G004`: label 221; header 223; total 256.
- `G005`: label 261; header 263; total 296.
- `G006`: label 301; header 303; total 336.

Each block contains month/year, daily rows, `Gross`, `Net`, `Imposto`, `Gastos`, `Lucro Líquido`, `ROI Gross`, `ROI Net`, and its own total. Formulas extend through row 338.

## Required rollover preflight

1. Read live sheet metadata and live formulas before duplication.
2. Compare live used row/column extent with the most recent backup/script assumptions.
3. Locate site blocks by header text, not historical fixed columns.
4. Inventory manager blocks and total rows in the source tab.
5. Duplicate the live structure first; only then adapt month/date/cash references and clear target-month manual inputs.
6. Validate formula errors across the full live used range and verify all six manager blocks for both sites.
7. Treat any old July rollover script or backup as historical evidence only until revalidated against the live source.

## Read-only validation result from the discovery session

- Live grid: 352 rows × 890 columns; active returned content through row 338.
- Prior backup range: `'Junho 2026'!A1:AGX275`.
- Live active range observed: through `AHF338`.
- Formula errors in live `A1:AHF338`: zero at inspection time.

These counts document the detected redesign; future execution must re-read live state rather than assume they remain unchanged.
