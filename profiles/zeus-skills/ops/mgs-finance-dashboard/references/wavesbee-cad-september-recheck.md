# WavesBee CAD / September recheck — 1546607083468623912

Authority: Rodolfo in thread 1545426987756298340. Scope: WavesBee CAD in dash + Sheet August/September 2026; reread September payroll and investigate G29, no authorization to change the latter two.

## Verified result and supersession

- Supersedes the remaining WavesBee currency and literal-August payroll follow-ups in `monthly-networks-and-sheet-parity.md` only as described below.
- Both workspaces now have the explicit WavesBee site flag `currency_policy=wavesbee-cad-1546607083468623912`, `input_currency=CAD`. Local graph converts GP / H1 to USD; public entry editor labels the raw GP inputs CAD. Neither network alone nor monthly name implies currency.
- August Sheet changed GP2, GP3, GQ5:GQ35 only: 33 cells, full entered-value diff, canary and independent GET, zero errors and zero financial input writes. September was already correct and received zero writes. Do not re-run the one-shot Sheet repair.
- 38 Python tests, 25 Node tests, real PG backup/restore/idempotence, isolated nonzero API input and exact restore, 17-scenario scope preservation, public browser 390/1440 and zero JS errors. Source JSON, baseline, all overrides, other sites/15 future workspaces, reviews and accounts preserved.
- Live September O148/O149/O151/O153/O154 now reference Setembro 2026 manager tabs; Nicolas/Isliago BRL floor is 3000. No Zeus payroll writes in this turn. The old literal-August claim is stale, not a current pending correction.
- This recheck is NOT full manager-workbook parity: Sheet commission formulas still use projections E14/F14 and manager H1 reads Caixa J2. These are separate observations requiring scoped disposition, not permission to rewrite manager workbooks. Dash monthly actual-result payroll remains distinct.
- Principal Setembro 2026!G29 is Contecta Geral / US, September 25, NOT WavesBee. D29 is the blank raw CAD input; E29 converts it, F29 applies invalids, G29 intentionally stays blank when E/F are empty. Exact formula is `=IF(AND(E29="",F29=""),"",SUM(E29,F29)*(1-$D$1))`. No import/error; no data or formula changes made.

## Additional live request — Wantabrand display

Rodolfo additionally requested `Wantabrand US-CC-ES + Wantabrand BR-CAR-BR` → `Wantabrand` in sites. Published display-only alias in catalog/editor and account site-selection labels; Wantabrand Finance stays distinct. Internal IDs, name-based binding values and financial history remain unchanged. Never apply display normalization to checkbox `value`, request keys, source names or identifiers. Browser readback covered the label in all 17 months and original checkbox binding; 17 frontend tests passed. Frontend backup is `app-before-wantabrand.js` in this task's local/remote recovery directories. No DB/Sheet writes or restart for the label.

## Reusable procedure

1. Resolve exact site/source metric and month, inspect both raw currency headers and USD conversion; zero-value parity cannot validate a currency change.
2. Keep immutable source evidence untouched. An explicitly scoped monthly site record controls an isolated graph-copy bridge and UI metadata together. Test both original-currency input and downstream normalized USD with nonzero synthetic values, never production financial canaries.
3. Preserve all neighboring site fields and review records during migration; optimistic revision guard and exact post-write readback. Hash baseline/other scenarios, not just count months. Future months are not in scope unless authorized.
4. Deployment dependency preflight must enumerate runtime dependencies. A local-only diagnostic (`verify_live.py`) need not exist remotely and is not production drift. Never suppress a missing actual runtime dependency.
5. This UI/API intentionally rejects blank overwrites: unchanged blank stays blank, clearing an existing input uses numeric zero. Isolated tests needing exact pristine state restore the saved isolated scenario in a guarded transaction/finally; never broaden a currency task to rewrite production blank-input behavior. An initial probe restore with empty string returned 400; probe recovery/restoration was fixed in isolation before publication.
6. Source changes made by the owner during parallel work supersede old captures. Always reread FORMULA, UNFORMATTED_VALUE and FORMATTED_VALUE before presenting a pending formula repair. Do not attribute concurrent changes without evidence.

Canonical doc: `/root/mgs-agent/docs/finance-system-product-direction.md`.
Report: `/root/mgs-agent/reports/finance-wavesbee-1546607083468623912.md`.
Evidence: `apps/finance-system/private/wavesbee-1546607083468623912/`.
Runtime: `currency_bridge.py`, `currency-migration.mjs`, `worker.py`, `workspace.mjs`.
Recovery: remote `/home/zeus/mgs-finance-backups/1546607083468623912`; isolated DB `mgs_finance_currency_1546607083468623912`, stage `/var/tmp/mgs-finance-currency-1546607083468623912`. No automatic retention/delete authorization.
