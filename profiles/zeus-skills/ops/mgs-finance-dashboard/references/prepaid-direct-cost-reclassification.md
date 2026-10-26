# Prepaid purchases and direct-cost reclassification

Use this workflow when a prepaid purchase or recharge must remain visible while the monthly result recognizes actual consumption by site/manager.

## October onward — consumption-only, no historic replay

Rodolfo1555579357651537931 explicitly excludes the May–September retrospective commission reconciliation and its manager/payment explanation from monthly carry. October+ uses verified `direct_daily_cost`/`sms_usage_receipt`; recharge is `prepaid_credit`, not recurring company cost. Never copy historical `direct_monthly_cost` SMS facts, commission adjustments or source-month explanatory notes. Preserve natural payable carry through the ledger instead of adding the historical difference again.

The corrected engine normalizes legacy `company|121` to archived/non-P&L for October+ **before `prepare_catalog` and manager allocation**, not just in the final cash display. A residual BRL30000 template was otherwise charged in parallel with daily usage. Preserve its original stored amount/history, do not invent a real purchase from a template, keep real prepaid credits untouched, and block reactivation through the expense API. Reject historical SMS-reconciliation facts in a new month. Validate owner cash, general allocation, every manager, month-scoped notes and authenticated browser; excluding only the company total is insufficient. `reports/finance-monthroll-1555579357651537931.md` records15periods,8viewports and preserved September notes/ledger.

## Official total versus detail reconciliation

Use the authenticated SMS Funnel dashboard total for the identical period and timezone. Preserve observed manager counts and record a stable source/detail variance separately as `sms_dashboard_reconciliation`, without a manager; this reconciles company cost without changing individual commissions. A properly recorded variance does not leave the financial day pending or require Rodolfo to choose the source again. Missing or unstable dashboard data, incomplete/duplicate/wrong-date detail and unknown sequences still block acceptance. Follow the active source policy in `docs/finance-sms-dashboard-source-policy.md` rather than imposing exact detail equality or treating WordPress as the accounting total.

Apply a residual to a named manager only under an explicit, bounded owner disposition. Preserve observed sequence counts and record the authorized difference separately with its exact scope and provenance; never fabricate message rows or turn a one-off assignment into a permanent G002 fallback. Verify the real financial write and idempotent replay before resuming dependent imports.

## Registering a new recharge through the existing application

Use this branch for an authorized record of an already-paid recharge. It is neither payment execution nor a consumption reclassification; do not replay the historical migration or deploy code to add a routine record.

1. Resolve the payment date and competence before writing. Interpret relative dates against the user's timezone using a calendar tool. Read the live workspace and inspect existing `prepaid_credit` additions by ID, provider, date, currency and amount. If a follow-up merely confirms an already-correct date, report the fresh readback without inserting another recharge. A same-date/amount match is a duplicate candidate, not proof that two genuinely separate purchases cannot exist.
2. Use the canonical finance SSH helper and shared release admission (`finance_release_guard.lease`) for the baseline probe. Read production with `openPostgres({options:'-c default_transaction_read_only=on'})`; save a restricted snapshot of the target scenario and hash its result and the deterministically ordered `finance_ledger`. Retain the revision, overrides and existing additions for comparison.
3. Prefer the supported owner API to a historical one-shot CLI. Inspect `prepaid-credit-cli.mjs` before reuse: a CLI pinned to an earlier authority is not a general-purpose writer. Never substitute the old authorization or remove its guard to make a new request pass. Authenticate through the established owner login/MFA flow, keeping credentials and session material out of evidence, and obtain CSRF from `/api/auth/me`.
4. Read `GET /api/workspace?period=<YYYY-MM>` and require the baseline revision still to match. Submit one `POST /api/scenarios/workspace-<YYYY-MM>/prepaid-credits` with explicit `period`, `revision`, a stable request-specific `id`, payment `date`, `provider: 'SMS Funnel'`, `currency: 'BRL'`, exact decimal `amount`, `status: 'confirmed'`, current authorization message as `authority`, and `label: 'Recarga SMS Funnel'`. Keep the legacy archived expense untouched. A conflict or uncertain response requires readback before any retry; preserve the same request ID.
5. Read back both the authenticated workspace and production scenario. Require exactly one matching row with every submitted field preserved, an audit event `PREPAID_CREDIT_ADDED` for that ID, unchanged result and ledger hashes, unchanged overrides, and all prior additions intact. If a concurrent writer changed the baseline, reconcile that writer before attributing a result change to the recharge. Record the actual revision and audit ID in the receipt; never infer success from HTTP status alone.
6. Treat **Despesas Gerais → Créditos pré-pagos SMS Funnel** as the new record's destination, distinct from the historical **Arquivadas / reclassificadas** line. The recharge is excluded from profit and manager commissions; consumed SMS continues through its separate import. API/database readback proves the record, not browser rendering—claim visual validation only if the actual UI was exercised.
7. End with amount, payment date, competence/location and confirmation that the result was not charged again. If the record already existed, say it was confirmed rather than newly launched. Do not describe bookkeeping as a payment or transfer executed by the agent.

## Accounting model

1. Treat purchase/recharge and consumed cost as different facts. Never replace one silently with the other.
2. Preserve the original expense row, charges, currency, review status and source amount. Archive it from the monthly result with an explicit reclassification marker; the UI must keep it visible as `Arquivada — não participa do resultado` and show the preserved payment/recharge amount.
3. Recognize consumption with `kind: direct_monthly_cost`, fixed in BRL and converted into the engine on every calculation. Require period/date identity, active site, allowed manager, exact original currency, positive decimal amount, source and authorization.
4. Use a monthly closing fact (`date == period`, `monthly_closing: true`) rather than inventing a calendar day or disguising the cost as media spend.
5. Allocate every external manager separately. Use `SEM_COMISSAO` for MGS/G002 so the cost reduces the site/company result without producing external commission.
6. Prove that archived recharge + direct consumption enter the company result exactly once: `removed recharge - recognized consumption - change in manager payables` must equal the owner-profit delta in BRL.

## Closed history and carry

- Refresh closed months through the owner history-refresh flow, creating new immutable versions and preserving original `finance_history` rows.
- Re-read each monthly owner closure after refresh. Carry must use the refreshed prior-month balance, not a hardcoded adjustment.
- Compare each balance only with costs recognized through that same cutoff. Never use the cumulative May–September recharge/consumption difference to explain the August ending balance: August ends before September's recharge and consumption. Build two bridges instead — May–August into the August carry, then September into the September due — and compare old/new results at one frozen FX snapshot.
- When native-month dues are recalculated while historical payment rows remain unchanged, the unpaid difference already appears in the next month's `Saldo anterior`. Do not add that same month's difference again as a ledger adjustment.
- If the ledger begins in August, explicit September adjustments for a May–August reconciliation contain only May–July; August is carried by the recalculated August due versus its preserved payment. State this in the description.

## Cent rounding

- Fixed-BRL consumption must remain exact under FX refresh.
- Commission deltas can move by one cent per manager because the engines round individual payables at different boundaries. Never alter the direct cost or invent a balancing fact to force a manager cell.
- Permit only explicitly enumerated one-cent outcomes proven in stage and authorized by Rodolfo; validate the company-profit bridge from the actual payable deltas. General cent tolerances remain forbidden.

## Read-only monthly SMS recheck

Use this branch for “is this month's SMS correct?”; it is an audit, not permission to repeat the historical reclassification or modify payments.

1. Resolve the approved month's source plan and completion evidence through the registry/checkpoint. Use the old plan only for approved manager allocation and provenance; obtain fresh vendor totals and current financial state before answering.
2. Reuse `scripts/sync-smsfunnel-cost-daily.py` as an imported module, not its write-capable main routine. Load the canonical environment, call `authenticated_session()`, then `fetch_dashboard_day(session, headers, date)` for every closed date in the requested month. Persist only date/count/source-hash evidence, verify unique-date coverage against the calendar, and sum in code. The `/daily-sents` response contains eight consecutive buckets starting at the requested date: the helper validates weekday labels and selects the first bucket; summing all eight on each request would overlap dates. Do not persist message bodies, phone numbers or credentials.
3. Verify the applicable unit price with the vendor and the approved closing basis. Calculate cost in integer cents or `Decimal`; if pricing changed within the period, reconcile each applicable interval rather than applying the latest price to the whole month.
4. Read the actual monthly workspace from the finance PostgreSQL host using `openPostgres({options:'-c default_transaction_read_only=on'})` under release admission. Match each approved `direct_monthly_cost` by exact ID, period, site, manager, original BRL amount and currency. Require unique IDs and exactly one matching calculated fact per cost. Check for daily costs or reconciliation rows that could recognize the same consumption again; total parity alone does not prove absence of duplicate charges.
5. Recalculate the saved workspace in memory with `calculate({period, overrides, additions})`, without committing. Compare its SMS facts to the persisted result. Invoke `managerView` for all five external managers and inspect the exact SMS objects in `blocks[].monthly_closing_adjustments`; a string search for an SMS ID anywhere in the response is not proof that the cost reaches the manager's financial block. Verify each summary control and keep G002 as the company/noncommissioned share.
6. Verify the original recharge row and all its charges remain archived, while its calculated company-expense BRL/USD contribution is zero. Distinguish prepaid purchases, consumed cost, historical payable adjustments and personal reimbursements. A recharge/consumption difference is not by itself an accounting error or a payment to execute. Check that historical monthly SMS facts were not copied into the following daily-consumption month.
7. Aggregate vendor-versus-Dash totals and the signed difference in code. Report the verdict first, then covered dates/send quantity/unit price/recognized cost, approved manager breakdown when useful, and whether recargas were excluded from double charging. State that financial values were unchanged. Distinguish a fresh total reconciliation plus approved-allocation readback from a fresh message-by-message attribution audit; perform full detail pagination only when attribution is disputed or the existing evidence is insufficient.

## Mutation execution gates

Use these only for an authorized reclassification or financial correction, not a read-only monthly recheck.

1. Capture a production DB/code backup and verify hashes.
2. Restore an isolated PostgreSQL database and run RED/GREEN tests.
3. Run dry-run and a different-FX test proving fixed BRL consumption.
4. Apply workspace changes and ledger adjustments transactionally with optimistic locks and audit events.
5. Verify idempotency, immutable unrelated scenarios/history/users, and every pre-existing ledger row.
6. Read back authenticated APIs for history, workspaces, managers and ledgers.
7. Exercise the public browser: archived recharge visibility, manager CPV block and payment-adjustment description; require zero app JS errors and zero same-origin failed requests.
8. Do not claim a payment was executed: adjustment rows change payable balance only.
