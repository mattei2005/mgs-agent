# July 2026 incremental fill, 8–12 — account routing and scope audit

## Context

Rodolfo supplied a five-day workbook for `2026-07-08..2026-07-12` and asked Zeus to update the existing `Julho 2026` tab in the master finance Sheet. Days 1–7 had already been filled from two earlier reports.

## Validated reconciliation

- Source and mapped revenue: `24,283.56`
- Source and mapped spend: `19,423.75`
- Revenue cells: `219`
- Spend cells: `88`
- Independent expected-cell readback: `307` cells, zero mismatches
- Formula errors: `0`
- Changes outside approved bands: `0`
- Fincgriffin detail rows through day 12: `60`
- Creditoparaveiculo detail rows through day 12: `62`

## Incremental-period pattern

1. Process and reconcile only the newly supplied period.
2. Load previously approved `Long.csv` outputs for earlier days of the same month.
3. Use only the new period for top daily revenue/spend writes.
4. Use the combined month-to-date Long sources to rebuild cumulative lower manager tables such as Fincgriffin and Creditoparaveiculo.
5. Never reconstruct prior manager splits from displayed Sheet totals; the approved Long sources preserve gestor attribution.

## Account-slot routing lesson

A site-level spend map is insufficient when a report contains multiple ad accounts for the same site. Route by normalized `Conta_FB` whenever the monthly Sheet has separate manual `BM - $` slots.

Rules:

- Preserve an account's slot already used earlier in the same monthly tab, even if an older month used a different slot. Splitting one account across columns inside the same month makes review harder.
- When an exact account header exists, use its corresponding manual `BM - $` column.
- For a genuinely new account, preflight a free manual slot in that site's block and record the mapping in the local audit. Do not silently collapse it into another account's slot.
- Creditoparaveiculo remains the explicit aggregation exception: all related FB account variants sum into the top `Creditoparaveiculo BR-CAR-BR` spend input while the lower mini-table preserves gestor detail.
- Google Ads BRL remains separate: write only the `Google Ads -R$` input and verify the neighboring USD formula for every touched day.

July-specific assignments used for continuity in this period included earlier-month-established slots for Topfeed BR, Helixenit MX, Infinitynexx MX and Eggbev US. New accounts such as Openzed BR-CAR, Eggbev BR-CAR, Wantabrand BR-CAR, Newsoun BR-CAR and Cliquet BR-CAR were mapped to separate manual slots during preflight. Treat these as July 2026 operational detail, not universal cross-month mappings.

## Independent scope-diff verification

The post-write audit was supplemented with a second checker:

1. Save a broad pre-write `FORMULA` render snapshot.
2. Read the same ranges after the write.
3. Compare cell-by-cell.
4. Permit differences only in:
   - top daily revenue rows for days 8–12;
   - top spend rows for days 8–12;
   - Openzed Ícaro daily bands for days 8–12;
   - cumulative Fincgriffin detail table;
   - cumulative Creditoparaveiculo detail table.
5. Fail if any changed cell falls outside those bands.
6. Independently read every expected revenue/spend cell and verify conversion, summary, and detail-margin formulas.

This catches accidental out-of-period writes that a same-script expected-value audit can miss.
