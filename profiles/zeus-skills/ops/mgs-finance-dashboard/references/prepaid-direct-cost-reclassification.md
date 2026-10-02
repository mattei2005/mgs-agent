# Prepaid purchases and direct-cost reclassification

Use this workflow when a prepaid purchase or recharge must remain visible while the monthly result recognizes actual consumption by site/manager.

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

## Execution gates

1. Capture a production DB/code backup and verify hashes.
2. Restore an isolated PostgreSQL database and run RED/GREEN tests.
3. Run dry-run and a different-FX test proving fixed BRL consumption.
4. Apply workspace changes and ledger adjustments transactionally with optimistic locks and audit events.
5. Verify idempotency, immutable unrelated scenarios/history/users, and every pre-existing ledger row.
6. Read back authenticated APIs for history, workspaces, managers and ledgers.
7. Exercise the public browser: archived recharge visibility, manager CPV block and payment-adjustment description; require zero app JS errors and zero same-origin failed requests.
8. Do not claim a payment was executed: adjustment rows change payable balance only.
