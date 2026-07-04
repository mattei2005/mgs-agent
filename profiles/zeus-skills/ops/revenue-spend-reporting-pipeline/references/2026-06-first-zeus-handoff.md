# First Zeus Handoff — Revenue × Spend Pipeline (2026-06)

## Context

Rodolfo handed Zeus an instruction file for the weekly MGS revenue/spend processing pipeline and then provided an Excel report plus a destination Google Sheet. The first attempted run produced an invalid operator-facing Sheet because the agent wrote before a full preflight and created many internal diagnostic tabs.

## User Correction

Rodolfo objected that the tabs created did not make sense. Durable lesson: for this class of task, the destination Google Sheet is not a debug surface. The agent must preflight input structure and mappings first, then write only the requested business tabs.

## What Went Wrong

- The first Excel file had `Gastos FB`, `Gastos Google`, and `MonetizeMore` effectively empty.
- The agent still uploaded a revenue-only output with `Gasto = 0`.
- The sheet received many diagnostic tabs (`Flags`, `Redirects_AV`, `Sites_desconhecidos`, etc.) instead of the intended clean operator-facing output.
- The agent should have stopped after detecting missing spend data and asked for the corrected workbook.

## Corrected Preflight Pattern

Before writing to Google Sheets:

1. Inspect workbook tabs, row counts, columns, and date ranges.
2. Compute raw totals by source.
3. Report blockers and ask for missing mappings.
4. Do not mutate the destination Sheet until blockers are resolved.

Example preflight summary from corrected workbook:

```text
Aba             Linhas   Datas
report SB-1      2.428   16/06–29/06
report SB-2     11.042   16/06–29/06
report AV       23.473   16/06–29/06
MonetizeMore        28   16/06–29/06
Gastos FB          244   16/06–29/06
Gastos Google       28   16/06–29/06
```

Detected raw totals in that workbook:

```text
Receita SB-1        33.354,207660
Receita SB-2        12.581,204809
Receita AV         100.447,412088
Receita Monetize     1.957,980000
Receita total      148.340,804557

Gasto FB            71.679,980000
Gasto Google        66.224,120000
Gasto total        137.904,100000
```

## Mapping Blockers Found

`Gastos Google` contained account names not covered by the original instruction:

- `Mattei 1`
- `Gamingadx-US-01`

The correct behavior is to stop and ask Rodolfo for site/vertical/gestor mapping before processing/uploading.

Also confirm the weekly handling of `fincgriffin _gb` before reassigning to `us-car-en / g006-d`.

## Output Shape Discipline

Default user-facing tabs should be minimal:

- `Long`
- `Resumo_dia`
- Specific site consolidation tabs only if asked, e.g. `Fincgriffin_dia`, `Fincgriffin_gestor_dia`, `Fincgriffin_resumo_gestor`

Diagnostics should remain local unless requested:

- classification layer totals
- ambiguous pages
- redirects
- unknown sites/accounts
- raw audit JSON/CSV

If a validation tab is useful, make it concise and operator-readable.
