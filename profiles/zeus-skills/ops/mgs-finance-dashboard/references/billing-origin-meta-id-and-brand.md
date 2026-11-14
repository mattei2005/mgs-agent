# Billing origin, ID-only Meta registration and official brand

## Authority and release
Rodolfo `1546618148571058266`, critical auxiliary-service confirmation `1546619674320441415`, logo/favicon `1546624782785716305`. Canonical decision: `/root/mgs-agent/docs/finance-system-product-direction.md`; proof: `/root/mgs-agent/reports/finance-origin-1546618148571058266.md`. June/September-style historical UI expectations must not override this request.

## Billing origin — company and employees
- Imported `input` + `mode` is the billed input, not the displayed USD/BRL conversion. For explicit dashboard edits, `edit_amount` + `edit_currency` supersede the imported presentation.
- `expenseOrigin(e)` implements that priority; never fall back to `e.usd` or `archived_usd` for the editor's default. Keep canonical IDs, baseline and review/activity history.
- BRL source remains BRL as FX varies; USD source remains USD. Fixed salaries use the same principle. `COMMISSION_FLOOR` is automatic and has no editable amount.
- Original CAD charges divide by monthly H1. Unit-cost rows retain their original quantity and monthly G1 divisor; do not label those quantities USD. Only original unit-cost rows accept UNITS.
- `apply_expense_changes` must receive actual monthly CAD/unit divisors in both worker and company-allocation graph paths. Missing/invalid divisor fails closed.
- FX is dynamic until the specific monthly rate is fixed. Existing quote collector runs every 30 minutes; UI polls every 5 minutes except during open editors. Current financial values use the app's own quote lifecycle, not a fresh import from Sheets at every render. Rate key for USD/BRL is `principal|CAIXA SINTETICO|J2`; `source` is a descriptive label, not stable identity.

## Charge-date presentation

1. Inspect the persisted expense definition and final `/api/workspace` payload before changing the UI. Use the assembled API metadata, not only `result.domain.expenses`: saved `additions` can overlay charge and review fields without replacing the calculated result.
2. Read billing dates from each `charges` component (`id`, `date`, `amount`); keep `checked_on` exclusively for the review date. Render saved date-only values as DD/MM/AAAA without timezone conversion, and use `—` for missing dates; never infer a charge date from the selected month, current clock, review status or review date.
3. Preserve component order and multiplicity. For several charges, show every date with its component number and original amount/currency; do not deduplicate equal dates, because separate debits can occur on the same day. Keep the existing editor when it already captures these fields.
4. Scope the column and its CSS to the requested expense list. Inspect native and historical renderers separately; where a historical source has no charge dates, display `—` without modifying immutable history or unrelated dashboard summaries and personnel lists.
5. Test single, multiple, repeated-date and null-date expenses against the API, then open/cancel the editor and reload. Check desktop column fit and mobile reachability for every column, not only table overflow. Finish with unchanged expense definitions and financial fingerprints; presentation acceptance must not depend on saving a real expense.

## Account creation — live BM, not cached optional inventory
- New registrations: ID is the only editable identity field. Sites remain selectable per month. Name, currency and IANA timezone are readonly and filled by a real BM read.
- `meta-lookup.mjs` exposes authenticated/CSRF-protected start/status endpoints. Numeric literal ID only (no silent act_ cleanup). Queue is private filesystem JSON with UUID handles, 16 pending cap, timeout and readiness checks.
- `accounts.mjs` requires a fresh ready lookup for new IDs and derives metadata server-side; client-forged name/currency/timezone cannot replace the verified result. Existing account ID/currency usage protection and monthly bindings remain.
- Production app remains PrivateNetwork/AF_UNIX. The authorized auxiliary unit `/etc/systemd/system/mgs-finance-meta-lookup.service` runs `meta-lookup-worker.py` on Zeus. It transports the private request queue via the existing pinned SSH route, then reads Meta and writes sanitized metadata back. No Meta credential is copied to RunCloud or the browser.
- Use the finance inventory's established 1Password item `APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei`, not the acquisition account registry fallback. A small successful BM page with another actor proved only 7 visible accounts, not finance-wide access. Resolve exact historical finance identity before claiming coverage. Cache/token values remain protected, outside Git; SSH password is memory-only with 24h refresh, not a new vault call on every poll.
- BM target is Digital Trust `155263197283282`; verify identity and fully paginate owned/client edges with name/currency/timezone. Current successful proof saw 279 unique visible accounts in 4 pages; do not hardcode that as a permanent count or claim coverage of every BM. Unknown/inaccessible ID fails closed; never grant permissions or change credentials automatically.
- On repeated transport failures, service records a sanitized state and alerts at 3; blocks after 5. State: `private/meta-lookup-worker-state.json`. Rollback can stop/disable this auxiliary service; deletion remains a separate Critical Subset gate.

## Display/brand
- Exact alias `FinanceTopFeed` → `Topfeed Finance`, sorted using display name. Internal ID/name/account checkbox values/domain `finance.topfeed.fun` stay intact; TopFeed Finanzas remains separate.
- Prior Wantabrand alias remains intact.
- Historical cropped logo superseded by Rodolfo 1546703031033405501: use the complete original square, not a tight crop. Current procedure is in google-mcc-self-profile-square-logo.md. Favicon from the earlier release was not changed in that correction. Assets: mgs-logo.png, favicon.ico (16/32/48/64), favicon-32.png, apple-touch-icon.png. Login and authenticated UI use the logo; only these exact non-sensitive assets are public before auth.
- User corrected G29 to G129 and reported G129 populated. No Sheet write for that observation; don't resurface the G29 diagnosis as his current problem.

## Verified acceptance and reusable harness
- 40 Python, 28 Node and focused auth/display tests PASS. Restored PostgreSQL/API exercise uses a real queue/Meta response; final public browser verified 17 periods, 56 expense/personnel editors, ID→metadata, mobile/desktop, asset hashes and zero JS errors. No production financial test mutation or Meta/Sheets write.
- `deploy/origin-release.py` is an authorization-specific one-shot code-only release with backups, second-copy SHA256, restore and production scenario hash readback. Do not rerun completed prepare/publication as a new workflow.
- For stage worker + API exercise, start both subprocesses within ONE bounded foreground controller, consume both and stop only the test worker. Two tool calls that appear parallel may serialize and produce a false queue timeout.
- If an isolated exercise partially mutates fixtures, `tests/reset-origin-stage.mjs` restores only the two test rows using SELECT-only production reads. Never drop/truncate or restore the live DB to repair a test.
- Test files: tests/test_expense_origin.py, tests/origin-editor.test.mjs, tests/origin-pg.mjs, tests/origin-browser.mjs, tests/run-origin-public.py. Evidence and retained recovery artifacts are inventoried in `private/origin-1546618148571058266/` and the release report.
