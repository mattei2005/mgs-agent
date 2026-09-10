# GAM original → Excel diário consolidado

## Ownership and route

This is the revenue-spend-reporting-pipeline's Excel consolidation workflow. The finance dashboard skill links here; do not copy financial rules into dashboard access helpers. Smart Bidding access/map owns authentication and read-only identity queries only. Generating a workbook does NOT authorize importing it into the financial app or Google Sheets.

Read the ACTIVE decisions in `/root/mgs-agent/docs/gam-revenue-claude-yolo-september-2026.md` before running. Do not replay historical Claude errors to force agreement. Rodolfo1547589806559731742 explicitly defines `-s` as direct traffic and `-d` as bot strategy: preserve them separately. Identifying G00X as the same person does not authorize strategy consolidation. The legacy Long suffix-normalization implementation is not a rule for dropping this financial dimension.

**Active confirmation1547589806559731742:** Escalatepower and Mavroa revenue defaults are `g002-d`, superseding the fixture's four manager-pending lines below. The original Zeus workbook remains preserved for independent comparison; apply confirmation as a separate overlay/version. Mavroa vertical was not confirmed. Claude's subsequent file is evidence to compare, not an authoritative mapping source.

## Active GAM-source priority — Rodolfo1547626692745629796

The original GAM report received by email is always the primary financial consolidation source. Canonical rule: `/root/mgs-agent/context/sources-of-truth.md`, section Receita GAM. Preserve original revenue/currency and available dimensions/UTMs under approved mappings. SB/network dashboards support diagnosis and validation, not a forced reallocation based only on visitor/URL classifications without original-row lineage. Explicitly authorized identity bridges such as Yolokfx remain scoped and retain original amounts.

Eggbev: keep approved GB/US separation, both g006-d; do NOT subtract SB-only CAD28.32 or create an EMP line. This supersedes the earlier request below to block/ask for an EMP split or require joint campaign/URL evidence before continuing this consolidation. Retain the diagnostic evidence; do not claim the proposed cross-page visitor-navigation explanation is proven. Generalized differences found only in dashboard remain reconciliation notes, not invented GAM classifications.

During payment week, reconcile again to the general GAM report Rodolfo requests from SB or the responsible network. Match period/currency/network scope, retain provenance and difference bridge; no email connector, cron, automatic financial import or silent adjustment is authorized by this standing process. The final updated Zeus Excel remains due after all domain decisions, not after each domain.

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

## Domain-by-domain review cadence

Rodolfo1547595092661895178 requested a specific reconciliation cadence: show only domains with actual differences, ONE domain per response, with separate Zeus and Claude sections. Specify period/currency, country/vertical, full gestor-strategy tag and amounts; make the exact disputed allocation explicit. Let Rodolfo decide which classification is correct before advancing to the next domain. Do not repeat a portfolio-wide verdict, dump all domains at once, or treat a review question as permission to rewrite/import workbooks. Persist each new confirmed decision with provenance and preserve independent baselines. Existing approvals remain in force unless Rodolfo changes them; this review rechecks their application. Rodolfo1547595924346376202 further required checking the SB dashboard's country/vertical split before asking him to adjudicate a recoverable classification. For the current domain, consult authenticated Reports > Vertical in the same date range and currency, verify publisher/domain/country scope, then show SB evidence beside Zeus and Claude. SB classification evidence does not authorize replacing original GAM revenue with SB totals. Keep one-domain cadence.

Validated live case1547595924346376202: Openzedfinanzas September1–9, publisher `digital-trust_openzedfinanzas`, `/reports/vertical` → observed `POST /report/performance_per_vertical`; 65 unique records, full period exactly equal to nine daily calls. Both countries appear on all nine days: `ccr`/`es` gross CAD14119.95 and `ccr`/`us` gross CAD4058.21. This corroborates ES/US separation; it does not reconcile exact GAM amounts (GAM ES14126.7522500028941400869, US4074.372674839301...). Evidence: `/root/mgs-agent/work/sb-openzedfinanzas-1547595924346376202/vertical-period.json` and `verification.json`. No SB or finance write.

## Country AND product checks during review

Do not stop at confirming countries: Reports > Vertical may reveal another product within the same country that both workbooks collapsed into CC. Eggbev1–9 September, checked under Rodolfo1547598180990976100: SB has GB/ccr, US/ccr, US/emp and zero-revenue BR/car. US/emp has CAD28.32 gross in the Vertical snapshot; Reports > URL returned loan URLs (`apply-us-loan-alliant-credit-union`, `apply-us-loan-grace-loan-advance`, `apply-us-loan-wells-fargo`), supporting EMP=loans in this case. The original Eggbev US rows have utm_term '-' throughout, so the exact GAM loan split was not established. Do not subtract CAD28.32 from GAM as if the snapshots reconciled or assume the original contains precisely that amount. Present the additional product and its mapping limitation for Rodolfo's decision.

Technical schema note: `/reports/url` was observed calling `POST /report/performance_per_operation`; its rows use lowercase `country`, `vertical`, `url`, nested `metrics.revenue` and `cc`, unlike Vertical's uppercase fields and `ccr`. Check the actual keys before concluding that EMP or another category is absent. Evidence: `/root/mgs-agent/work/sb-eggbev-1547598180990976100/`.

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
