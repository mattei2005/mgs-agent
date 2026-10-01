# Native dashboard → monthly Sheets export

Use only after the owner authorizes the exact principal/month/manager/summary targets. A diagnosis request permits GET/SELECT only; approval to export does not authorize dashboard writes, payment execution, automatic synchronization or other months.

## Source and grain

1. Capture one live scenario through a READ ONLY PostgreSQL transaction. Capture source additions, overrides, account metadata and existing ledger separately. Do not call quote-refresh, workspace-open or other mutating application endpoints just to read data.
2. Generate current manager views from the captured scenario using the production-matched `manager-view.mjs`, layouts and period modules. Verify hashes first and require every manager summary control to pass. Legacy domain manager/cash rows alone are not the native UI.
3. Include native **and legacy** revenue facts. A nonzero legacy Gross USD may coexist with a large native GAM import; native-addition currency totals alone then omit valid source revenue. Verify each original CAD/USD pair against the fact's normalized USD and the complete cash total. A legacy USD component must have source-cell provenance; never manufacture a balancing residual.
4. Resolve every nonzero media input through `accountModel`: exact account ID, source fact, site, country, date, currency, value. Require each input to map once, and native-currency conversion to reconcile with cash media. Never copy a whole shared site into each manager.
5. Treat company allocation units separately from unique site count: an approved site can contain two allocation segments. Infer no allocation from positive revenue or catalog existence. Sum active expense sources and approved segment allocations exactly.
6. Respect archived expenses even when their editor retains an old nominal amount. Mirror each active expense's origin currency and charge components; do not promote retained archived amounts into costs.

## Workbook construction and authority

- Retain all supplied spreadsheet IDs and gids. Back up entered values, formulas, effective/formatted values, formats, notes, merges, banding and relevant metadata before editing. Exclude credential-bearing tabs from all broad reads.
- Freeze entered-content hashes of other financial tabs. Define an explicit clear/write region for each target; preserve notes/receipts outside it. If a September redesign needs new panels or columns, keep those within the approved September tab and update the complete formula dependency closure.
- Existing consumer coordinates such as manager D12 can be retained while additional summary sites are placed in a clearly labeled overflow area; include those additional references in the total. Never silently omit the eleventh site to fit a ten-row template.
- Separate original CAD and original USD inputs from normalized USD formulas. Derive invalids, revshare, tax, profits, company allocation and monthly ratios from the same source policies. ROI is blank when media is zero, not a tax-only denominator. Monthly ROI uses sums, never average daily percentages.
- A monthly Caixa can use shared historical row labels that no longer describe the current network. Preserve historical columns/labels; bind the current month's invalid/revshare deductions to its actual network summary. Add clearly labeled month-specific site rows only when authorized, and extend that month's subtotal without duplicating the old shared-manager row.
- A one-time mirror is an explicitly dated, provisional snapshot, not a settlement. Copy the selected dashboard revision's exchange values with a provenance note; do not label them confirmed, alter the dashboard's automatic rates, or promise permanent equality to subsequently refreshing FX. Reconcile authorized quote-only source changes and perform a final narrow rate refresh before delivery. Continuous synchronization needs separate authority.
- Copying an already-recorded receipt for an authorized full-sheet mirror must preserve its exact ID, reference month, sign and amount, excluding voided entries. This is not authority to create/edit/execute any payment in the application. Match the application's cent-based due/opening/movement arithmetic rather than introducing an unexplained cent adjustment.

## Execution and independent proof

1. Build the complete plan before writing. Independently evaluate its generated formula graph from real captured inputs, including cross-workbook references, rounding, month length, source currencies and all manager remunerations. Label this as offline proof, not a live Sheets result.
2. Re-read entered content immediately before each workbook write; stop on unexpected edits. Exercise and restore a blank-cell canary in every target, including a decimal/function formula to test its locale.
3. Use English function names with the target workbook's actual formula separators/decimal convention. Google normalizes `.1` to `0.1` (and the corresponding decimal-comma form); allow only the proven lexical normalization in formula readback, not arbitrary expression equivalence or altered IDs.
4. Reduce request count by packing contiguous cleared rows and rebuilding only the target tab's merge topology. Restore unaffected note/receipt merges. Remove obsolete target-only banding/conditional rules when their old coordinates would misrepresent the new layout. Do not touch another tab's formatting.
5. Persist start/payload hash/readback receipts. After a transport error or verifier failure, read the actual target before retry. Skip an already-applied workbook rather than replaying destructive formatting or deleted banding IDs.
6. Principal→manager→principal IMPORTRANGE propagation can briefly show errors or old remuneration while the multi-workbook cluster is being updated. Finish the authorized cluster, then reread the complete chain; do not hardcode salaries or introduce compensating constants to fix a transient cache.
7. Compare every planned entered cell and every numerical/formula result, all displayed errors, all site/manager/day/account controls, remuneration, main close and Caixa. Independently check cent-rounded financial results, not just a floating tolerance.
8. Compare the complete target before/after scope diff; require every change to be explicitly planned or inside an authorized rebuilt region. Recheck all protected tab hashes. Validate gids, dates, effective number formats, header visibility and structural merge readback.
9. Finally re-read the dashboard: source additions, ledger and non-FX inputs must be unchanged by this operation. Reconcile automatic quote events by audit evidence rather than calling them unauthorized drift. Seal source revision, final readbacks, hashes, scope proof, backup and honest recovery notes.

Verified reference implementation and evidence: `/root/mgs-agent/apps/finance-system/private/september-export-1555274844109803522/`; source authority and final outcome belong to its report/checkpoint, not this reusable procedure.
