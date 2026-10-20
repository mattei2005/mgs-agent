# Meta card billing and limit-risk analysis — 2026-09-09

## Purpose

Validated reference for consolidating spend and card charges across several Meta ad accounts without changing campaigns, budgets, credentials, or billing. The class-level procedure remains in `SKILL.md`; this file preserves the API details, recovery pattern, and session evidence.

## Validated read-only surfaces

### Ad Account identity and current billing state

Read exact target accounts with:

- `account_id,name,account_status,currency,timezone_name,business`
- `funding_source_details`
- `balance,amount_spent,spend_cap`
- `is_prepay_account,user_tasks`

Rules:

- Require exact account-ID and expected-name readback.
- `funding_source_details` requires `MANAGE` for the account.
- Expose only brand and masked suffix; never payment-source IDs or credentials in Discord.
- `balance`, `amount_spent`, and `spend_cap` use minor currency units; Insights `spend` is already in major units.
- A user-confirmed relationship such as several masked AMEX suffixes representing one physical card may be consolidated. Never infer that relationship from brand alone.
- For BM-wide payment-method inventories, paginate owned/client ad accounts with a broad approved BM-admin user token, then verify exact accounts with GET and `user_tasks`. An omitted funding source is not proof of no payment method, especially without `MANAGE`; distinguish identified current cards, inactive card-type records without visible brand/suffix, monthly invoicing, and unavailable details.
- Do not use the root Graph `ids` query parameter on v26.0+: it returns `code=100` with a deprecation message. Recover with ordinary exact-account GETs or a bounded Graph batch whose children are exclusively `method=GET`; validate every child HTTP/body/account ID and reconcile the collected count. The batch transport POST does not authorize any billing mutation and does not bypass quota.

Official reference: <https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-account>

### Period spend

For every account and identical `time_range`:

1. Query `/act_{id}/insights` at account level with `time_increment=1`.
2. Query it again with `time_increment=all_days`.
3. Require complete pagination, exact account/currency identity, each daily date inside the requested range, and daily sum within USD 0.01 of the aggregate.
4. Label the current day partial where account-local time has not closed. Do not mix issuer time, operator time, and account timezone silently.

### Card-charge activity

The public card-transaction route is the account activity edge, not a historical/private `/transactions` endpoint:

- Edge: `/act_{id}/activities`
- Parameters: exact `business_id`, `category=BUDGET`, `since`, `until`, bounded `limit`
- Fields: `event_time,date_time_in_timezone,event_type,translated_event_type,extra_data`

Retain exact billing types:

- `ad_account_billing_charge`
- `ad_account_billing_charge_failed`
- `ad_account_billing_decline`
- `ad_account_billing_refund`
- `ad_account_billing_chargeback`
- `ad_account_billing_chargeback_reversal`
- funding-source add/remove events only when the audit needs payment-method history

For a normal successful charge, `extra_data.type=payment_amount` and numeric `extra_data.new_value` is the minor-unit charge. Preserve `transaction_id` only in protected reconciliation state; do not print or post it.

- Keep `category=BUDGET` explicit even when requesting all event types: an unfiltered activities request can paginate hundreds of delivery/edit events while omitting a billing charge returned by the BUDGET query for the same account and dates. Absence from the unfiltered edge is not negative billing evidence.
- For an issuer charge without a named Business, discover all Businesses visible to the approved broad credential and union their paginated owned/client inventories with `/me/adaccounts`. A card-funded account in a different Business can be absent from `/me/adaccounts` and from the previously audited primary BM.
- Distinguish an exact amount/date/account charge match from issuer reconciliation. If the activity exposes no charged-card suffix, report the current default separately and do not assert it was the card used for that event. Same-value charges in another account, even one currently on Mastercard, cannot be excluded solely from its current default.

Official activity model: <https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-activity/>

### Business invoices

`/{business_id}/business_invoices` returns invoices for monthly-invoicing legal entities. Join every result to requested targets through exact `ad_account_ids`.

Interpretation:

- Invoice rows overlapping the target IDs are invoice evidence for those accounts.
- A successful request with zero target overlap means this invoice surface is not the source for those card-funded accounts.
- It does **not** mean no card charges occurred; use account activities for that.

Official reference: <https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/business/business_invoices>

## High-volume activity recovery

A wide 40-day activity request for a high-volume account repeatedly failed during cursor pagination with transient Graph `code=1/subcode=99`. Retrying the same broad cursor did not produce a complete result.

Validated recovery:

1. Stop the broad retry after the repeated-failure threshold.
2. Derive half-open daily windows from the account's Meta timezone: `[local midnight, next local midnight)`.
3. Query and paginate each day independently with `category=BUDGET`.
4. Deduplicate by transaction ID plus event time, event type, and amount.
5. Persist progress after each window so a later interruption does not discard completed days.
6. Declare the charge total complete only when every daily window is complete.

The recovery completed 40/40 daily windows for the high-volume account, covering 1,435 unique budget events and 70 billing events. This is the durable lesson; do not encode the transient broad-query failure as a permanent claim that the activity API is broken.

## Reconciliation semantics

Never assert:

`period spend = settled card charges + current Meta balance`

Possible deltas include:

- a charge inside the requested dates settling spend from before the period;
- spend near the end of the period not yet charged;
- an opening Meta balance carried into the first day;
- issuer posting/statement timing that differs from Meta event time.

Report the three measures independently:

- Meta period spend;
- successful Meta charge events in the period;
- current Meta bill amount due.

For card-limit risk, the card issuer's live available credit remains authoritative. Use recent closed-day burn only as a projection and label it as such.

## Session evidence

Scope: 12 USD accounts, 2026-08-01 through 2026-09-09, Meta Graph v26.0, zero Meta/billing writes.

Validation:

- 12/12 identities, names, currencies, payment brands/suffixes, and account access matched.
- 12/12 daily spend sums reconciled with aggregate Insights.
- 11 AMEX-funded accounts were consolidated only because Rodolfo confirmed the suffixes represented one physical card; one Mastercard account remained separate.
- AMEX: period spend USD 183,317.67; 157 successful charge events totaling USD 181,612.57; current Meta balance USD 3,972.26; recent seven-closed-day burn USD 5,711.37/day.
- Mastercard: period spend USD 4,697.85; four successful charge events totaling USD 4,246.20; current Meta balance USD 589.81.
- No charge decline, refund, or chargeback event was found in the complete requested range.
- Business invoice query returned 49 BM invoice rows and zero overlap with the 12 target account IDs.

Risk illustration from user-provided issuer state:

- USD 30,000 available divided by USD 5,711.37/day projected about 5.25 days if unchanged.
- Moving the two highest-burn AMEX accounts reduced retained projected burn to USD 1,218.40/day, about 24.62 days of theoretical headroom.
- A third account can be chosen by objective: highest ongoing burn for pure capacity reduction, or largest current Meta balance for near-term charge exposure. State that tradeoff rather than presenting one ranking as universally correct.

## Reporting contract

Lead with:

1. plain risk verdict;
2. exact accounts recommended for migration and why;
3. per-account period spend and recent closed-day burn;
4. card-level spend, successful charges, current Meta balance, and issuer headroom projection;
5. API coverage and any gap;
6. explicit statement that no billing change occurred.

Use one compact monospaced comparison block or concise bullets. For a request asking which accounts use credit cards, default to one consolidated account-first list sorted by exact account name; do not make card groups the primary structure. Group by card only when requested or when card concentration/risk is the subject. If Rodolfo asks to reformat an already validated inventory, reuse that snapshot, preserve account IDs/names and reconcile the count rather than starting a new API audit unnecessarily. Do not expose transaction IDs, payment-source IDs, token details, invoice download URLs, or full card data.

## Business credit-line runway

- Discover the Business's complete `extendedcredits` edge, then read the exact line with `max_balance,balance,credit_available,is_access_revoked,owner_business_name`. Monetary objects expose `amount_in_hundredths` and `currency`; calculate with Decimal, not display-string parsing.
- Inventory owned/client ad accounts completely and classify current credit-line funding by exact `funding_source_details.id` equality with the requested line, not by account name or monthly-invoicing text alone. A type-4 source is monthly invoicing, but another source ID is another line.
- Retry missing funding projections with exact-account GET plus `user_tasks`. Missing funding details without MANAGE remain a visibility gap, not proof that no payment method exists. Read their Insights independently: zero spend can bound the historical runway effect without establishing their funding type. Report the confirmed line count separately from unclassified dormant accounts.
- Empty `extended_credit_invoice_groups` or `owning_credit_allocation_configs` does not prove that the line has no attached accounts; direct funding-source equality remains positive evidence.
- On a repeat audit, compare overlapping closed dates against the prior raw Insights snapshot, not just the new rolling average. Report exact historical revisions separately from the newly closed day; do not present the old snapshot as a current revalidation or attribute the revision to a specific Meta mechanism without evidence.
- Read seven closed local dates, reconcile daily sums against an independent aggregate for every line-funded account, and report yesterday, seven-day average and recent-three-day average separately. List positive-spend accounts and state the exact count and shared zero value for the remaining accounts; never equate yesterday's zero with seven-day zero.
- Refresh available credit at closure. Make the target date inclusive explicitly, label the target timezone, and distinguish an elapsed-time projection from a conservative reserve of complete calendar-day allowances. The latter intentionally reserves a full current day despite the partial day already consumed. Show the additional-credit need or remaining cushion under both recent and baseline burn; do not promise safety when the high-burn margin is only a few hours. Exclude unapproved future payments, limit increases and budget cuts from the baseline.
- Resolve a valid but unavailable IANA timezone alias from `/usr/share/zoneinfo/tzdata.zi` Link records to an installed canonical zone, while preserving the original Meta value in the snapshot. Do not silently substitute the operator's timezone, install packages or change host timezone for an alias-only issue.

## Mutation boundary

A payment-method change is a Critical Subset billing operation. The read-only analysis does not authorize it. Before UI execution, obtain the exact destination card, pre-read each named account's current masked source, state whether already-initiated charges may remain on the old source, define rollback/readback, and obtain Rodolfo's required double-confirmation.
