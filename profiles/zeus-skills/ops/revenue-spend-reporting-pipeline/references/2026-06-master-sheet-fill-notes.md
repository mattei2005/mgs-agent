# 2026-06 Master Sheet Fill Notes

Session context: Rodolfo asked Zeus to validate and test-fill the Google Sheet `MGS - Receita dos Sites 2026`, tab `Junho 2026`, from Cláudio's approved Long report for 2026-06-16..2026-06-29.

## Source / reconciliation facts

- Cláudio workbook tab `Long`: 723 rows.
- Zeus corrected Long: 723 rows.
- Totals matched exactly at aggregate level:
  - Receita: `148,340.804557`
  - Gasto: `137,904.10`
  - Site × vertical × gestor groups: no divergences.
- Minor row-placement difference: for `finanzas.openzed.com / es-cc-es / g003-d`, the revenue may sit on `OpenzedFinanzas-ES-CC-ES-01` vs `...-03` depending on first spend row. Aggregates are unchanged; for the master sheet, fill by site/vertical/day, not by the arbitrary first revenue-carrying account row.

## Receita currency rules for the master month tab

Rodolfo confirmed:

### Fill revenue into `GROSS_USD_*`

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
- `gamingadx.com` (currently no revenue in the 16–29 Jun file; wait for SB if missing)
- `lyzmo.com`
- `newsoun.com`
- `openzed.com`
- `portalrelevante.com`
- `seuprimeiroempregoam.com`
- `wantabrand.com`
- `zuout.com`
- `zytiva.com`

### Fill revenue into `GROSS_CAD_*` (not the adjacent USD-calculated column)

- `financeadx.com`
- `helixenit.com`
- `infinitynexx.com`
- `marevelx.com`
- `vizioid.com`
- `xyvlov.com`

The month tab has CAD manual columns plus adjacent USD calculated columns for these JBF-style sites. Enter the source amount in the CAD gross column.

## Spend currency rules

### Fill spend in USD (`BM - $`)

- `cliquet.com`
- `conectageral.com`
- `creditoparaveiculo.com`
- `de.newsoun.com`
- `ducapes.com`
- `eggbev.com`
- `finance.ducapes.com`
- `finance.topfeed.fun`
- `finance.wantabrand.com`
- `financeadx.com`
- `finanzas.cliquet.com`
- `finanzas.eggbev.com`
- `finanzas.lyzmo.com`
- `finanzas.newsoun.com`
- `finanzas.openzed.com`
- `finanzas.topfeed.fun`
- `finanzas.zuout.com`
- `finanzas.zytiva.com`
- `fincgriffin.com`
- `helixenit.com`
- `infinitynexx.com`
- `lyzmo.com`
- `marevelx.com`
- `newsoun.com`
- `openzed.com`
- `portalrelevante.com`
- `seuprimeiroempregoam.com`
- `vizioid.com`
- `wantabrand.com`
- `xyvlov.com`
- `zuout.com`
- `zytiva.com`

### Fill spend in BRL (`Google Ads -R$`)

- `gamezonead.com` → account `Mattei 1` corresponds to `Mattei 1 (Google Ads - BRL)`.
- `gamingadx.com` → account `Gamingadx-US-01` corresponds to `Gamingadx-US-01 (Google Ads - BRL)`.

## Account mapping notes from June tab

- `wantabrand.com`: use `Wantabrand US-CC-ES-01`; Rodolfo added the missing account header in the sheet.
- `creditoparaveiculo.com`: sum all spend account variants into the single sheet column `Creditoparaveiculo BR-CAR-BR`:
  - `Creditoparaveiculo-BR-CAR-BR-01`
  - `Creditoparaveiculo-BR-CAR-BR-01-G003`
  - `Creditoparaveiculo-BR-CAR-BR-01-G005`
  - `Creditoparaveiculo-BR-CAR-BR-02-G002`
- `fincgriffin.com`: top spend column is `Fincgriffin US-CAR-EN`. The sheet also has a lower mini table at `TQ100:TV185` with `Data / Gestor / Gasto / Receita / Lucro / Margem`; continue that table by gestor and sum into the top column.
- `openzed.com`: there is a second lower block starting at `NF100`:
  - `NF100` = `ICARO - G001-D`
  - `NF101` and `NM101` = `PREENCHER ESSA`
  - `NF102` = `GROSS_USD_US`
  - `NM102` = `GROSS_USD_GB`
  - Fill `openzed.com` g001/Icaro revenue in this lower block; fill the principal g003 revenue in the main top block.

## Tested partial fill on 2026-07-02

Rodolfo requested a test-fill for only:

- `financeadx.com`
- `gamezonead.com`
- `gamingadx.com`
- `openzed.com`
- `finanzas.openzed.com`

Implementation updated 294 cells on `Junho 2026` and read back samples:

- `QP20` financeadx CAD US = `28.36`
- `RF20` financeadx CAD MX = `552.66`
- `AAV20` gamezonead receita = `1369.47`
- `AAW61` gamezonead gasto BRL = `2741.40`
- `AAH61` gamingadx gasto BRL = `147.11`
- `NF20` openzed principal US = `2636.62`
- `NF120` openzed Ícaro US = `23.40`
- `OI20` finanzas.openzed ES = `1034.19`
- `OJ61` finanzas.openzed gasto ES01 = `626.39`

No formula errors were found in touched bands.

Backup file before test fill:

`/root/mgs-agent/work/revenue-spend-reporting/junho-2026-test-fill-backups/backup-before-test-fill-20260702-185506.json`

## Sheets API operational pitfall

Avoid backing up each cell with one read request. The Sheets API hit `ReadRequestsPerMinutePerUser` quota (`60/min`) during a per-cell backup attempt. Correct pattern:

1. Build the list of target cells.
2. Backup the relevant sheet/grid with one or a few broad `values.get` / `batchGet` calls (FORMULA and FORMATTED/UNFORMATTED as needed).
3. Apply writes with one `values:batchUpdate`.
4. Verify with one compact `batchGet` over the touched bands.

Do not loop hundreds of individual reads against Google Sheets.
