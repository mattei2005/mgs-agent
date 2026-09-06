# Monthly periods and ad-account registry

Authority: Rodolfo message 1546184035921829938, Discord thread 1545426987756298340, including in-turn requests for account name/ID/site-list registration, removal of anonymous empty US/BR-like fields, and a compact month-selectable FX/invalid/tax/share screen. Current product source: `/root/mgs-agent/docs/finance-system-product-direction.md`. Checkpoint: `ZEUS-FINANCE-DASH-AUGUST-20260904`.

## Published scope and supersession

Publication and readback: `apps/finance-system/private/ui-periods-1546184035921829938/`; report `reports/finance-ui-periods-1546184035921829938.md`. This supersedes the historical statements that September cannot open, accounts cannot be registered/renamed, and rates require separate large cards. It does not close the entire financial-system migration.

- Sixteen new periods, September 2026 through December 2027 inclusive, plus preserved August: `workspace-YYYY-MM`, 17 registered workspaces. Calendar lengths are real, including February 2027's 28 days. No financial movements, manual expense amounts, review dates or settled-payment flags are copied from August. Site/status/master templates and fiscal/compensation rules are reused as initial references; each month's edits are isolated. Automatic minimum/commission compensation remains a rule, not a copied historical payment. Future periods have no extrapolated estimate before they start.
- Compatibility calculation still uses the immutable August graph as a template, not a new Google tab. `periods.py` clears monetary input leaves/manual expenses in a calculation-local copy and advances verified calendar anchors. Source key strings containing Agosto 2026 are lineage/slot identifiers, not permission to mix monthly overrides. February rejects day-31-only input keys; all actual daily facts stay within their period. No Sheets writes or source JSON mutation.
- A visible month selector controls every view. FX/invalid/tax/share has a synchronized local month selector and one compact table of ten parameters, not giant cards. C1/D1 and M2 EW82 exception remain correct; editing selected-month parameters must never alter another month's state. Guard open forms and concurrent switch/poll responses so a form cannot save into a newly selected month.
- Projection uses completed elapsed days through yesterday, capped at actual month length. Extrapolate operational daily result, not already-monthly company/payroll costs. Closed month estimate equals realized; no projection before/on day one. This assumes complete portfolio data through yesterday, as in the canonical rule.
- Quote collector remains the existing two-value read-only Google SA feed. `refreshQuotes` updates eligible draft workspaces through the current month, respecting each month's fixed values. Planned future periods start with provisional reference rates; they become scheduler-eligible when their month arrives, and explicit operations also apply current automatic quotes. This is not a future exchange-rate prediction or an independent native FX feed. Preserve the existing finance source/cutover boundary.
- Movimento do mês has Sites Ativos and Sites Inativos, sorted by domain family within each. Group by explicit monthly catalog status, NEVER by nonzero revenue. Inactive historical amounts remain visible and included in accounting. Current seed: 41 labels, 28 active/13 inactive; allocation still uses 43 blocks/units, with two each for Openzed and Infinitynexx. Do not conflate sites and allocation units.

## Account identities and safe reconciliation

`accounts.mjs` stores `master-ad-accounts` in the existing audited JSON workspace store, excluded from financial scenario lists. No new schema/grants/authentication. ID and currency are immutable after registration. Name is local display identity; editing it does not rename the Meta account. Month-specific `bindings[YYYY-MM]` selects site names from the registered site's list. Shared accounts can keep multiple proven sites. Imported source-site bindings are the template default; changing a month's binding does not rewrite others.

Read-only Meta inventory via the approved existing app/user token found 279 visible accounts in Digital Trust BM 155263197283282. A first valid but asset-limited token saw only seven accounts; this was a visibility limitation, not the BM total. Final exhaustive source-slot reconciliation persisted 324 entries, linked 78 distinct accounts securely and left seven named positions unresolved. Do not invent IDs, collapse duplicate names, or replace 015 with 15. Immutable source monetary leaves retain their original values and source lineage. New accounts add explicit daily expense keys; conversion and source-linked spend bridge feed the validated manager/payroll/cash calculation. Native-site daily edits and monthly allocation remain covered.

Seven unresolved source labels, deliberately not assigned IDs:
- WANTABRAND FINANCE
- Yolokfx · US-SHEIN-EN-01
- Vizioid · MX-CC-ES-01
- Creditoparaveiculo · BR-CAR-BR-015-G001
- FinanciamentoAutoAdx
- AutoCreditAdx
- CarCreditAd

They appear in the administrative reconciliation section; original amounts remain editable/preserved. Source Google positions are not Meta accounts. The account registry is a verified inventory snapshot plus local CRUD, not continuous Meta synchronization. Manual local rows not matching the snapshot are labelled local, not Meta-verified.

Anonymous empty country-like positions are hidden from the editor rather than destructively deleted from source/history. Verified removal: 229 empty slot groups. Never hide a generic position with historical or current nonzero money. Real named accounts may remain available with no new-month spend; these are not anonymous placeholder columns.

## Verification, deployment and retained evidence

- Node regression: 19/19; Python: 26/26. `tests/periods-integration.mjs` registers/reopens all 17 months in isolated PGlite, validates every calendar, zero imported movements, baseline preservation, monthly tax isolation, account currency/ID/site identity and actual new-account spend. It persists the per-period result and expected counts.
- `tests/periods-browser.mjs`: local real UI writes and public read-only acceptance; month switching, February, group counts, compact rates, account create/rename and GBP spend, desktop/mobile widths. `tests/ui-browser.mjs` preserves general UI/financial/security coverage. `tests/sync-browser.mjs` validates manual/automatic refresh, two tabs in isolation and editor pause.
- Browser tests must use `FINANCE_EVIDENCE_DIR` or the current revision's dedicated default. Never reuse an older task directory for new screenshots/evidence. The first generic UI runs in this task reused the historical catalog path; the current source was corrected and public acceptance rerun into this revision's directory. Prior reports/code/DB backups remain retained; those overwritten browser images are not pristine historical evidence.
- Select a unique close/cancel control with `.first()` or its accessible name; `#editor [data-close]` matches both controls. Match workspace response by URL pathname, not exact URL, now that period is a query parameter.
- Publisher `deploy/ui-periods.py` is one-shot: prior hashes, code/PG backup with second copy/hash, isolated restore, staged tests, scoped app-service cutover, actual month/account registration and readback. Do not rerun successful publication. `deploy/register-periods.mjs` skips existing monthly records rather than resetting them; never send `--exercise` to production.
- pg_hba intentionally rejects the app identity on arbitrary test databases. Do not alter HBA, CONNECT, grants or credentials to test. Use a separate test-code copy owned by the existing DB admin; connect only to isolated restore as mgs_pg with startup `role=mgsfinance` applied to every pool connection and assert current_user. The application role remains the execution role. Production uses ordinary mgsfinance peer authentication. `resume-periods-prepare.py` records bounded recovery from the HBA denial and a missing-date canary fixture; no source or financial production test write.
- Retain `/home/zeus/mgs-finance-backups/1546184035921829938`, isolated DB `mgs_finance_periods_1546184035921829938`, stage directory and `/var/tmp/mgs-finance-periods-1546184035921829938` until an authorized cleanup/retention decision. Backup verification is not a claim of recurring DR/retention/encryption.

## Continuity

Read registry/checkpoint, this reference, product direction, latest report and actual runtime before continuing in another thread. Current outstanding work includes the seven account identities, source/import/feed lifecycle and full native migration/final sheet cutover; conference of all revenue/ad-spend and full backup/DR policy are not silently claimed complete. No new user authorization, Meta campaign/budget change, credential, system config, gateway restart or Sheet write was made by this revision.
