# August 2026 dashboard formula audit

## Scope and closure

Target workbook: `MGS - Receita dos Sites 2026` / `Agosto 2026` plus `CAIXA SINTETICO` and the five manager `Agosto 2026` tabs (Kelly, Isliago, George, Nicolas, Joe).

Validated closure:

- 6 spreadsheets, 7 active August/source tabs.
- 51,319 formula cells inventoried.
- 200,169 dependency edges mapped.
- 29,058 manager `IMPORTRANGE` spill cells matched the principal source exactly on fresh readback.
- 132 independent manager calculation checks and 72 site-to-summary mapping checks passed.
- Zero unresolved external spreadsheet IDs and zero displayed formula errors in the audited source tabs.

The principal-to-manager graph is bidirectional by design: managers import monthly site blocks and `CAIXA SINTETICO!J2`; the principal imports `H1`, `D16`, `E14`, and `F14` to calculate manager expenses. Validate the entire cycle before using any summary tab.

## Confirmed defects at audit time

- `CAIXA SINTETICO` August column had 45 missing formulas. Rodolfo explicitly deferred this tab until after the `Agosto 2026` repair sequence.
- USD/BRL and USD/CAD remained live through `GOOGLEFINANCE`; a finished month was therefore not a stable close.
- Multiple active `ROI_GROSS_TOTAL` formulas omitted one or more USD-normalized country grosses; Helixenit's total used semantically wrong columns.
- Yolokfx `RECEITA_NET_TOTAL` referenced gross instead of net, overstating net revenue/profit and ROI Net.
- Four manager tabs displayed a stale `Julho` label in `A1`, although their August imports and calculations were valid.
- The legacy `ROI GERAL AGOSTO` used stale coordinates and was not accepted as a source.

These findings are evidence for staged repair, not authorization to batch-write them. Re-read every target immediately before proposing its edit.

## First validated correction

`Agosto 2026!CR23` (`INVALIDO_US`, TopFeed Finanzas) was the sole interior formula-shape outlier in that column.

Incorrect:

`=IF(CQ23="","",CQ23/$H$1)`

Corrected manually by Rodolfo and validated by API readback:

`=IF(CQ23="","",-CQ23*$J$1)`

Validation contract used:

- Read `CQ22:CV24` with `FORMULA`, `UNFORMATTED_VALUE`, and `FORMATTED_VALUE`.
- Confirm exact formula parity with `CR22` and `CR24` semantics.
- Confirm dependent `CS23:CV23` recalculated and displayed no error.
- Do not fill down or touch adjacent cells.

## Reusable parser lesson

Normalize A1 column letters to uppercase before converting them to numeric indices. Live `IMPORTRANGE` formulas used lowercase ranges; failing to normalize produced false, extremely large spill dimensions and false parity failures. The corrected parser re-ran the complete spill comparison and returned exact parity.
