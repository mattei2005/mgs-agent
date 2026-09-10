# GAM original → Excel diário consolidado

## Ownership and route

This is the revenue-spend-reporting-pipeline's Excel consolidation workflow. The finance dashboard skill links here; do not copy financial rules into dashboard access helpers. Smart Bidding access/map owns authentication and read-only identity queries only. Generating a workbook does NOT authorize importing it into the financial app or Google Sheets.

Read the ACTIVE decisions in `/root/mgs-agent/docs/gam-revenue-claude-yolo-september-2026.md` before running. Do not replay historical Claude errors to force agreement. The generic Long pipeline normalizes manager suffixes; this specific GAM daily product preserves `-s`/`-d`.

## Procedure

1. Preserve/hash the input and inspect all tabs and rows. Recognize English and Portuguese headers by content. Date comes from the row/report properties, not filename or email delivery. If only usd/cad tab labels identify currency, disclose that provenance rather than invent Properties/network/timezone metadata.
2. Preserve the gross Ad Exchange revenue and currency. Do not use eCPM, net revenue, SB revenue, spend weighting, FX or premature rounding.
3. Map every row once into `(currency, date, site, vertical, manager)`, with source sheet/row, literal placement/medium/campaign, exact Decimal revenue and the rule/proof retained locally.
4. Keep business rules from the active canonical source. Defaults apply only where established. Unexpected placements/countries must retain source geography unless an explicit override applies. Unconfirmed site/vertical/manager mapping is a financial exception: stop before import, request confirmation, and if providing a review Excel preserve the full amount visibly as `A confirmar`, not an invented owner or omitted revenue. A financially reconciled file with classification caveats is not fully attributed.
5. Yolokfx September1–9 only: preserve any valid medium actually present in the new original. For missing medium, obtain the maximal safe same-day campaign→account identity bridge through SB AdGroup; use original GAM amounts. Exclude conflicting code/name evidence. Only unresolved original revenue goes to g002-s under the explicit Rodolfo decision. Distinguish three provenance buckets: explicit GAM medium, verified SB bridge, authorized unidentified residual. Never label valid medium as residual because account_evidence is empty.
6. Verify the SB union of all daily reads equals a full-period read and PKs are unique. The technical pack is `smartbidding-dashboard-map/references/adgroup-gam-revenue-reconciliation.md` (including successful POST201 and campaign-code conflict handling).
7. Deliver operator-facing `Receita USD` and `Receita CAD`, columns `Data | Site | Vertical | Gestor | Receita`, sorted by date/site/vertical/manager, filters/frozen header and per-currency total. Keep full Excel numeric precision and format two decimals; if matching a six-decimal comparison export, treat rounding separately. A concise `Validacao` may show the daily reconciliation, approved exceptions, three Yolo provenance buckets and mapping caveats. Keep verbose lineage local.
8. Read back the output and independently verify every source row maps once, group keys/counts, every currency/day total, source hash, approved rule regressions and no formula/error cells. Use Decimal for reconciliation and document only floating serialization tolerance; never silently drop zero-valued or tiny residual rows.
9. Upload the requested Excel natively to the exact Discord thread, read back the attachment and verify downloaded bytes/hash. Record checkpoint, inventory and REPORT-INFRA for operational artifacts; no second text copy of the report. Compare Claude only after Zeus's independently generated file exists, using currency/date/site/vertical/manager, not just grand totals.

## Validated fixture and acceptance evidence

Request: Rodolfo1547581942474608720, thread1545426987756298340. Evidence: `/root/mgs-agent/work/gam-sep01-09-1547581942474608720/`.

- `collect_sb.py`: read-only SB query, nine daily calls + full period; 288 unique records, exact equality.
- `build_excel.py`: fixture-specific implementation (hard-coded input/range), not a parameterized production runner. Never run blindly on a different report.
- `validate_and_inventory.py`: independent row-lineage and financial rule regression.
- `summary.json`, `lineage.json`, `aggregate.json`, `independent-verification.json`: exact reconciled values and provenance.
- Original: 27,091 rows (1,717 USD + 25,374 CAD); output: 513 groups (105 USD + 408 CAD); all18 currency/days validated.
- USD59,828.65570781756822746681; CAD216,460.49855899488678972775. No FX or finance app/Sheet write.
- Yolo: original CAD16,580.6046364440710968747 = explicit medium414.95213423939689313 + SB identity15,862.222363046283034255 + approved residual303.4301391583911694897.
- Four tiny records for Escalatepower/Mavroa totaling CAD0.26175290822947867783 remained visibly `A confirmar`; Mavroa also lacked confirmed vertical. This fixture proves complete revenue preservation, not full classification approval. Later Rodolfo confirmation must supersede this caveat explicitly, preserving the independent baseline for Claude comparison.
