# Manual FX and historical monthly source correction

Authority: Rodolfo1546975305216827412 and direct mid-turn corrections in thread1545426987756298340 on2026-09-08.

## Confirmed scope
- The Atualizar button must request a fresh read of the existing Google Finance sources before reloading editable-period values. Preserve fixed settlement rates, invalid percentages, historical January–July and future periods. Existing scheduler remains separate.
- **Historical January–July financial Dashboard must use each original monthly tab and its site blocks, NOT Caixa Sintético.** This explicitly supersedes native-closed-month-views.md's Caixa-backed cards/ranking/FX and corresponding prior UI assertions. Preserve source-owned totals, currency, expenses, manager values and original estimates; do not recompute history with August rules, overwrite frozen imports, or force distinct original measures to agree. Caixa may remain in immutable historical evidence, never as financial Dashboard fallback for these months.
- Facebook and Google Ads request is exclusively2026-09-01 through2026-09-07. First validate collection; no import/write yet. This is unrelated to January–July.

## Verified manual FX implementation
manual-quotes.mjs queues actor-owned requests through existing meta-account-lookups; existing Zeus meta-lookup-worker.py executes canonical SA collect under quote-sync.lock and selected-period publish. Web process still PrivateNetwork/AF_UNIX, no credential/network changes. POST/GET quote-refreshes auth+CSRF+owner; dedupe and timeout; full fixed-rate precedence. apply-live-quotes/refreshQuotes selected-period option preserves default scheduled behavior.
67Node/43Python PASS; restored isolated PG queue/auth/CSRF/history/future/non-FX/other-period guards PASS. Production real browser requestf0576b23-b1ac-4418-937f-7c1a1f6868b4: new source timestamp2026-09-08T20:29:05.200402+00:00, started after click, one request,6seconds to collection, three FX read back, historical button no request, zeroJS,390px. Backup /home/zeus/mgs-finance-backups/1546975305216827412; local private/manual-quotes-1546975305216827412; stage /var/tmp/mgs-finance-manual-1546975305216827412. No gateway/system-config/credential changes.

## Historical-source execution state
Correction authorized, in progress; do not claim deployed until source7months and public readback recorded. July snapshot/live principalH137=14334.15596559884, CaixaI80=14130.435020575853; source discrepancy203.7209450229875USD per50%. PrincipalH136 is site-closure sum plusN160; Caixa aggregates separate component paths. No historical financial values edited in diagnosis.

## September read-only proof
Exact application registry82accounts:80Meta and2Google. All82identity/currency/timezone/daily/aggregate pagination probes PASS forSep1–7. Meta80USDtotal111204.59,28withspend; Google2BRLtotal26938.430287, bothwithspend. GoogleGamingadx-US-01/2780300411=3014.871099BRL; Mattei1/5172498094=23923.559188BRL. Both Google accounts lack monthly site assignment; do not infer a domain from name. Evidence spend-registry.json,spend-rows/,spend-summary.json in private/manual-quotes-1546975305216827412. Raw cost_micros retained; no per-day premature rounding or silent currency conversion. Missing rows distinguished from failed calls; no September inputs written.
