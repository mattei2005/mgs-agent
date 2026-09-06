# August 2026 — integrated audit and reusable closure gates

## Historical verified audit

Source request: Rodolfo `1545877165982355557`, thread `1545426987756298340`.
Artifacts: `/root/mgs-agent/work/finance-final-reaudit-1545877165982355557/`.
Authoritative evidence: `FINAL-SUMMARY.json`, `REPORT.md`, `SHA256SUMS.json`, `final/manifest.json`.

The new full read-only capture included 6 workbooks / 9 tabs, 85,462 content/formula cells and 53,101 formulas. Of those, 53,085 passed local recomputation, six dashboard expressions received independent array/KPI reconstruction, and ten volatile provider formulas were observed and sanity checked, not independently priced. Strict parity: 83 import formulas, 29,058 imported spill cells, zero differences. All 20 manager projection formulas passed 2,240 isolated calendar scenarios. Four chart specifications/source-series were read back; no visual-rendering claim. Final capture had zero source formula/value/note changes and zero displayed errors. 406 historic support reference cells remained unchanged; those historic monthly tabs were not themselves audited in full.

The 19 former findings were rechecked through integral formula/component validation; F17 remains owner-confirmed, not externally documented. No Google cells or filters were written.

Current historical dispositions (resolve checkpoint for later changes):
- Financial integrated checks: PASS within recorded inputs.
- R01, open documentary issue: `BASE_DASH!V123:V153` still describes former global `AOW:APE` references. Actual numerical formulas correctly point to current `APE:APM`. No financial impact; no authorization to rewrite those labels in the read-only task.
- R02, metric disclosure, not arithmetic error: `CAIXA SINTETICO!J79` / `DASH EXECUTIVO!A8` calculate net profit / media spend (11.928283% at capture); `Agosto 2026!APM36` calculates post-share net revenue / all costs - 1 (10.697323%). Recommend precise distinct labels; do not silently harmonize formulas.
- August remains PROVISORIO until active settlement rates and partner/bank proofs are confirmed.

## Reusable closure gates

1. A moved source block requires checking both executable references and literal provenance/dimension text. Sheets automatically adjusts formulas, not an A1 address embedded in a plain text label.
2. Treat same-named ROI KPIs at different grains as a metric-definition check: reconstruct each numerator/denominator, quantify the difference, and separate arithmetic defects from inconsistent labels. Do not change the chosen convention without permission.
3. Validate every QUERY spill (all rows/columns, headers, grouping, ordering, limits, and the blank next row) independently from the normalized base. Verify chart range bounds cover the entire resulting data and that axes/series match intended metrics.
4. For read-only audits, validate current live filters and simulate alternatives locally. Do not mutate a filter just to complete a historical build-time smoke gate; report the narrower verification method explicitly.
5. Distinguish direct IMPORTRANGE spill parity from wrapped calls such as SUM(IMPORTRANGE(...)). Resolve both; compare direct spills with strict equality including blanks, and recalculate wrapped aggregates from the resolved range.
6. Snapshot-level loading errors are not automatically permanent import failures. Preserve the failed capture, retry the exact workbook without writes, and require stable final readback and source parity. A successful retry does not erase the transient observation.
7. A generic continuity scan can cross mini-table totals or USD-to-CAD manual-input transitions. Resolve actual date bands, inspect the neighboring raw-currency column, and retain a disposition for every candidate; never fill a numeric/manual input as if it were a missing formula.
8. Independent test engines may represent scalar formulas as 1×1 arrays. Normalize a genuinely scalar result before comparison; otherwise correct forecast values can be falsely flagged. Execute actual captured projection formulas in isolated in-memory scenarios for 28/29/30/31-day months, before/on day1, elapsed days, month end and post-close; include blank/zero/positive/negative totals.
9. Recapture every audited source, auxiliary range and chart spec at closure; require no unexplained formula/effective/formatted/note drift. Preserve evidence for any transient failure. Internal consistency is not proof of reconciliation to documents that were not supplied.
