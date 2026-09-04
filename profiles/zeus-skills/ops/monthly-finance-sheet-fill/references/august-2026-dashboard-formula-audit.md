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

## Validated staged corrections

Rodolfo repaired each item manually; every item below was independently read back before the next was presented:

- `CR23`: restored the invalid-traffic percentage formula and downstream recalculation.
- `AGT5:AGT35`: changed Yolokfx `RECEITA_NET_TOTAL` from `GROSS_USD_US` (`AGL`) to `NET_USD_US` (`AGN`); 31/31 formulas passed.
- `CM5:CM36`, `FC5:FC36`, `MA5:MA36`, `OC5:OC36`, `QE5:QE36`, `SY5:SY36`, `ABC5:ABC36`: restored omitted country gross components in each site's `ROI_GROSS_TOTAL`; every range passed 32/32 row-matched reference checks.
- `ACM36`: corrected Helixenit total to use gross cells `ABG36`, `ABP36`, `ABY36` rather than tax/net cells.
- `ADW35:ADX35`, `AKR35:AKS35`, `ALI35:ALJ35`, `ALZ35:AMA35`: restored missing day-31 ROI formulas.
- `ALI36`: separated AutoCreditAdx `ROI_GROSS_TOTAL` from the duplicated ROI Net formula.
- `O6:O35`: copied the Conecta Geral future-date expense guard so all 31 daily rows use `TODAY()` consistently.

Post-correction snapshot evidence:

- 50,546 formulas in the principal August tab.
- Zero displayed formula errors.
- All 12 targeted structural checks passed.
- Snapshot SHA-256: `3a5af49a7c74167daf8ede1388db6ca862324be27af3f34aae7d26260ad11200`.

At this boundary `Agosto 2026!H1` still used live USD/CAD through `GOOGLEFINANCE`. That is an owner-decision gate, not a completed repair: never choose or freeze a historical closing rate without Rodolfo defining the criterion/value.

## Range-readback lesson

For impact calculations, request exact driver cells as separate ranges in one `batchGet`. A wide sparse range can contain blank placeholders that make positional hand-indexing unsafe. Recompute the current KPI from the same readback used to validate the formula, especially while exchange-rate cells are volatile.
