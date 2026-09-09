# Company expenses: source order and original-currency basis

Authority: Rodolfo1547239702464045076, confirmed1547240897752604704; thread1545426987756298340. Canonical decision/evidence: `/root/mgs-agent/docs/finance-company-expenses-order.md`.

## Active rule; supersedes alphabetical company sorting
- In the Dash, August2026–December2027 company expenses follow the exact Sheet/print order. Preserve existing IDs and current display names, including SB LeadsOn Hub, SB Tech Bot and SB Wire Fee. Do not rename them back to JBF. Personnel and closed January–July views retain their previous order.
- August keeps the original amounts/currencies of its own tab; September its own tab. October2026–December2027 copy September's **origin amount + currency**, never converted USD/BRL or the September FX. Each period retains its own rates and conversion logic.
- Do not copy payment/review state or dates. Do not modify personnel inputs, revenue, media, network/site/account bindings or source Sheets.

## Reusable execution and validation
1. Read Sheets only through canonical SA helper. Resolve gids/names live. For expense inputs prefer narrowly scoped M100:P143 plus R106 and R141:R143; do not print or export unrelated notes/columns, which may contain operational access data. Compare `userEnteredValue`, not formatted/effective calculated money. Snapshot privately.
2. Classify origin by formula chain: manual O→USD; O=SUM(P/F1) with manual P→BRL; R/G1→UNITS; R/H1→CAD. Preserve blank versus entered zero. R106 quantity=0 with P106 derived was preserved as existing zero; nonzero or unknown chains require explicit modeling, never silently choose the calculated result as origin.
3. August SMS Funnel already uses USD4099.78; separately entered BRL20000 is retained as source evidence under Rodolfo's accepted F17 no-change decision1545866872048717967. Do not force provisional-FX equivalence or make a new authoritative-currency decision. September SMS origin is BRL30000.
4. Match stable company IDs and labels; the validated catalog is44 IDs company|100 through company|143. No duplicate/new rows for existing expenses. Unknown/ambiguous IDs or formulas fail closed.
5. Dual-host code/database backup with hashes; restore exactly to an isolated database. Test all target months, idempotency, facts/input preservation and alternative FX before canary. Preserve source/default display aliases.
6. Apply in bounded per-month transactions with revision locks and audit. Recompute from original inputs, preserving every monthly override and non-company addition. Read exact targets back. Do not restore a full production database over concurrent work as rollback; use revision-bounded recovery from backup.
7. Verify both Summary and Despesas Gerais order, 44 rows/no duplicates, original currency/value, and each conversion. Exercise actual HTTPS login on desktop/mobile, all17months, static app hash and zero JS/overflow errors. Credentials only via stdin from1Password; log out and read back401.

## Verified release2026-09-09
- Evidence root: `apps/finance-system/private/company-expenses-1547240897752604704/`.
-17months ×44rows=748 origin/ID checks;34desktop/mobile month views. August0financial edits;16later months42existing rows filled each, including explicit zeros. All88protected invariant checks passed; FX/monthly overrides/history/ledger/users and source daily facts preserved.
- Isolated alternative FX test USD/BRL6 and USD/CAD1.5 passed without origin edits; live verification returned0pending changes.
- Code: `company-expense-basis-cli.mjs`, deployment `deploy/company-expense-basis-release.py`, frontend `public/app.js`; tests `tests/expense-sort.test.mjs`, `tests/company-expense-public.mjs`, `tests/test_expense_origin.py`.
- The deployment runner is an authority-bounded one-shot for this request, not a cron and not permission to replay new financial overwrites. Live script uses revision locks; scripts/artifacts remain for evidence/rollback. No gateway/service restart.
