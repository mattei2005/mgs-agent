# Monthly Rollover Formula Audit Notes

## Context

Use these notes when preparing a month rollover in MGS finance sheets, especially duplicating `Junho 2026` into `Julho 2026` across the main sheet and manager sheets.

## Sheets involved in the July 2026 prep

Main sheet:

- `MGS - Receita dos Sites 2026`
- Spreadsheet ID: `16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak`

Manager sheets reviewed:

- Kelly — `1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs`
- Isliago — `1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c`
- George — `1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU`
- Nicolas — `128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU`
- Joe — `1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ`

## Formula inventory result

Initial read-only scan classified formulas and dependencies:

| Sheet | Formulas | IMPORTRANGE | CAIXA | Uses A3 |
|---|---:|---:|---:|---:|
| Principal 2026 | 48,182 | 25 | 6 | 1,230 |
| Kelly | 387 | 99 | 4 | 0 |
| Isliago | 12,564 | 240 | 4 | 0 |
| George | 196 | 76 | 4 | 0 |
| Nicolas | 761 | 239 | 4 | 0 |
| Joe | 787 | 236 | 4 | 0 |

Local audit output path from the session:

- `/root/mgs-agent/work/finance-month-rollover-audit/formula-audit-20260703-164123.json`

Do not assume this file still exists forever; regenerate if needed before writing.

## Durable lessons

1. The main monthly tab `A3` is not decorative. It stores the numeric month and is consumed by many formulas in the `Despesas Totais` / daily expense distribution path.
2. July rollover requires `A3 = 7`. If it remains `6`, formulas can calculate as June even if the tab is named `Julho 2026`.
3. Main sheet column `B` must be rebuilt to the target month dates. For July 2026, use 1–31 July; do not blindly copy June's 30-day structure.
4. The main formula pattern to audit is:
   - `DATE($B$4,$A$3,ROW()-4)`
   - `EOMONTH(DATE($B$4,$A$3,1),0)`
   - formulas dividing totals by `DAY(EOMONTH(...))`
5. Manager sheets rely heavily on `SHEETNAME()` plus `IMPORTRANGE`, so exact tab-name parity matters: the main sheet and every manager sheet must use exactly `Julho 2026`.
6. `CAIXA SINTETICO` month-column references are separate from tab-name parity. For June the summary column was `H`; for July it should move to the next month column (`I`) where applicable.

## Recommended audit before any write

1. Read all formulas with `valueRenderOption=FORMULA` via Sheets API.
2. Batch requests with `values:batchGet` instead of per-tab calls to avoid Google Sheets read quota errors.
3. Classify formulas by:
   - `IMPORTRANGE`
   - `SHEETNAME()`
   - `CAIXA SINTETICO`
   - `$A$3` / month-number dependency
   - hardcoded month literals (`Junho 2026`, `Julho 2026`)
   - formula errors (`#REF!`, `#N/A`, `#VALUE!`, `#ERROR!`)
4. Save the pre-write audit locally.
5. Only after the audit is clean: duplicate/rename tabs, update `A3`, rebuild dates, clear inputs, adjust summary references, and read back formulas/errors.

## Quota pitfall

A per-tab formula scan across all manager sheets can hit Sheets API read quota (`429 RESOURCE_EXHAUSTED`). Use `spreadsheets.values.batchGet` with multiple ranges per spreadsheet and retry/backoff only if needed. The durable lesson is batching, not that Sheets API is unavailable.
