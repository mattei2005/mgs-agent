# Closed-history feasibility: January–July2026

**Current-state supersession — Rodolfo1546858367635685396 and direct mid-turn clarification:** load `manager-access-and-history-dispositions.md`. Four manager accesses are now deployed, George=Ícaro confirmed, commissions startMarch, Jan/Febsalarynotzero; AprilS19cleared byRodolfo/readback22errorsresolved; Nicolaslegacyrefs ignoredbydecision;280ROIguards applied/readback withoutfinancialchanges. Import remains unimplemented. Statements below document the prior feasibility snapshot, not current blockers.

Authority: Rodolfo1546757745078968381. Canonical decision/docs and report finance-history-feasibility-1546757745078968381.md. This is a completed read-only feasibility study, NOT an import or manager-access release.

## New business boundary
January–July2026 are closed per Rodolfo. Their future display must use frozen effective values from the principal and manager Sheets, not execute/rebuild source formulas or apply August+ policies. August2026 onward keeps the current calculation system. Preserve historic payroll, FX, commission, daily values and ready totals exactly; do not back-propagate Jislaine3000, present-day percentages, current FX or ROI definitions. Screenshots remain irrelevant: source is the live canonical Sheet values.

## Proven coverage and limitations
- Canonical SA read40monthly tabs in6books plusCAIXA SINTETICOJan–Jul=41tabs.377907nonempty monthlycells; every present tab has all calendar dates in itsmonth.
- Principal/Kelly/Isliago/Nicolas/Joe:7months each. George:March–Julyonly; Jan/Febtabs absent. Do not infer zero or fabricate missing worksheets.
- No Icaro/Ícaro spreadsheet found by direct and broader paginated Drive search. Icaro appears in principal blocks; do not infer George=Ícaro or grant George's data to him. Requires explicit source/identity clarification.
- Jan/Feb layouts differ substantially and mix BRL/USD. Mar–May principal uses879columns,June993,July1041, with lower blocks throughrow338. Capture full named tabs, not reused August bounds.
- CAIXA C:I has7DOLARFECHADO columns and numeric closures, noerrors. Preserve its ready totals alongside site/manager details, without doublecounting or forcing recalculated agreement.
- Jan/Febprincipal132/148DIV0ROI; Nicolas2REFpermonth(P1oldJul2024reference,AF38legacyimport). AF38source1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso returnedDrive404toSA. Not proofdeleted; no authfallback allowed.
- AprilprincipalS19 is string waves in PortalRelevante grossUSD, causing22VALUEerrors through row19/total36. CaixaApril numericclosure still exists. Current error != approved historical number. Never replace error with0 or silently reconstruct.
- March/May/June/July available monthlytabs hadnoerrors in thiscapture. These are observed snapshots, not permanent healthclaims.

## Recommended importer contract (not implemented)
Snapshot by month/book/sheet/block/sourcecell, with effective value, formatted value, type/currency/date and error/blank status. Parse each month's layout and preserve all lower/sharedblocks. Ready totals, realized result, estimates and alternative commissioncolumns are separate facts. Do not derive paidcommission from a7%or10%scenario. Historicalmode read-only, excludedfromliveFXrefresh/edits/currentledger logic. Tests verify exactcopy/fidelity, not semantic recomputation of owner-approved closes.

## Current technical/access gates
periods.mjs only supportsAug2026–Dec2027; periodModel/managerView reuseAugust; finance-ops.mjs restricts usercreation andmanager-workspace toNicolas. Merely adding dates or users is insufficient. Need historicaladapter and generalized per-manager filtering with negative isolationtests. Runtimefinance_users hasNicolasonly; Rodolfoowner separate. Requested Joe/Isliago/Kelly/Ícaro accounts were NOTcreated; credentials/activation require additionalcriticalconfirmation. Ícaro association remains blocked.

## Repeatable audit
Use tests/history-feasibility.py: canonical SA, Drive+Sheets metadata, exact namedtabs, griddata effective/formatted/userEntered values, one persisted file andsummary pertab. Exclude credentialtabs and don't open Gustavo's workbook against standingrestriction; retain any historicalGustavo amounts already inprincipal. Aggregate/count/dedupe incode, compare calendarcoverage, inspectallerrors/headers, readCaixasummary, probeunknownlegacyfilemetadataonly. Skip completed captures, never silently overwrite with a new source epoch. Directorycreation must beidempotent(exist_ok=True). Local manifest includesSHA256 for eachsnapshot; no Sheets/cash/user writes during feasibility.
