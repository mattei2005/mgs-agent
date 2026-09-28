# SMS Funnel API readback

Load this reference after endpoints are saved, when the task requires proof of list routing, automation binding, sequence-link correctness or synthetic-lead cleanup. It supplements the WordPress checks; it does not authorize platform writes by itself.

## Evidence levels

Keep these claims separate:

1. **Router executed** — the landing returned the expected sanitized router header.
2. **Webhook accepted** — the mapped call returned `delivered`.
3. **Lead entered the intended list** — an authenticated list query found the exact test phone in the exact list.
4. **Automation is configured** — campaign/list binding and sequence fields passed readback.
5. **SMS was delivered** — a controlled real phone or provider delivery record proves carrier delivery.

Never promote a lower evidence level into a higher claim. In particular, `delivered` means the webhook returned 2xx; it does not prove that the SMS Funnel scheduled or delivered an SMS.

## Credential-safe API session

Use the corporate credential route already approved for the SMS Funnel monitor. Load the runtime environment, resolve the saved login from 1Password, then authenticate with:

```text
POST https://web2.smsfunnel.com.br/api/login
Content-Type: application/json

{"email":"…","password":"…"}
```

Use the returned access token only in memory:

```text
Authorization: Bearer TOKEN
```

Never print the login, password, token or integration URL. For endpoint preservation checks, print only presence, length and SHA-256 before/after.

## Read-only endpoints

Use the same endpoints as the SMS Funnel web application:

```text
GET /api/lists
GET /api/lists/{list_id}
GET /api/lists/{list_id}/leads?page=1&per_page=20&filter={phone}
GET /api/campaigns?page=1&per_page=100
GET /api/campaigns/{campaign_id}/sequences
GET /api/sequences/{sequence_id}
GET /api/leads/{lead_id}/sequences
```

Resolve the destination `list_id` from the saved WordPress integration URL without printing the URL, then look up the SMS Funnel list by that exact ID. Treat the ID and campaign `lead_list_id` binding as primary identity; labels are advisory and may retain a legacy prefix such as `CHAT` even when the route is functionally correct. Flag naming drift separately instead of rejecting a correct route. Paginate campaigns before filtering client-side; do not assume page 1 is complete.

## Automation and link verification

For every automation in the chain, read the campaign and its single intended sequence and assert:

- campaign is active;
- `lead_list_id` equals the exact source list for that automation;
- sequence is active;
- `sequence_type` is `sms`;
- `send_lead_number` equals `1`;
- URL scheme is HTTPS and hostname is the intended site;
- `utm_medium` equals the manager namespace exactly once;
- `step` equals the expected value exactly once.

The expected sequence is normally:

```text
Automation/List 1 → step=01
Automation/List 2 → step=02
Automation/List 3 → step=03, intentionally inert until List 4 exists
```

Read and preserve the exact URL pathname from each sequence. Run the public `step=01`, `step=02` and `step=03` checks on their own stage-specific URLs; reusing one known landing for every step can hide a broken neutral pathname that the router does not classify.

Require `send_lead_number=1` on all three automations for full future readiness. If List 3 currently ends at an intentionally unmapped `step=03`, a zero value there is a future-List-4 readiness gap, not a failure of the current flow through List 3; report the distinction explicitly.

## Targeted post-correction readback

When the operator fixes a field or renames a list after the routing matrix already passed, verify only the changed surface plus its stable identity:

- for a sequence-field correction, re-read the exact sequence ID and confirm the target field, active state, URL, `utm_medium`, `step` and campaign binding;
- for a list rename, re-read the exact list IDs and confirm the new names while requiring IDs and campaign `lead_list_id` bindings to remain unchanged;
- update the audit/checkpoint from pending to resolved only after both the changed value and stable bindings pass;
- do not rerun mapped webhook calls merely to validate a rename or toggle, because that creates new production leads while adding no evidence about the corrected field.

## Safe no-write routing matrix

Before a mapped-route test, exercise routes that cannot call a webhook:

```text
valid manager + intentionally unmapped final step → route-not-configured
missing or unknown utm_medium                  → invalid-medium
disabled manager                              → group-inactive
```

Use a unique cache-buster on each request and require the normal page HTTP response. These checks prove fail-closed isolation without creating a lead.

## Controlled mapped-route test

Run this only when the current authorization covers a production webhook test and cleanup.

1. Choose a clearly invalid synthetic phone namespace that cannot be a real recipient; never guess a plausible customer number.
2. Enumerate every live destination `list_id` across sibling managers/vehicles and require exact-phone absence before the call.
3. Record the intended list ID and count as context, not as the primary assertion.
4. Call the mapped route on the exact URL pathname stored in that stage's live sequence, with the exact manager `utm_medium`, step and a unique cache-buster.
5. Require the router result `delivered`.
6. Poll the intended list by exact phone until found or the bounded timeout expires.
7. Query all sibling lists and require the test phone to exist only in the intended destination.
8. Capture the exact synthetic lead ID and, when useful, read `/leads/{id}/sequences` before cleanup.
9. Delete only that synthetic lead:

```text
DELETE /api/leads/{lead_id}
```

10. Read every sibling list again and require exact-phone absence everywhere.
11. Repeat with a fresh synthetic phone for the next mapped step.

Live list counts can change while real traffic is entering. Never use before/after count equality as the sole cleanup or routing proof; exact-phone and exact-lead-ID readback is authoritative.

## Daily lead-entry count by list

For a read-only request asking how many leads entered exact lists during a closed local day:

1. Resolve each list by exact case-insensitive name through authenticated `GET /api/lists`; fail closed on missing or duplicate matches.
2. Define the requested half-open local window (`00:00:00 <= created_at < next-day 00:00:00`) in the operation timezone, then convert it to UTC before comparing API timestamps. For Creditoparaveiculo reporting, use `America/Sao_Paulo` unless the request explicitly names another timezone.
3. Count lead records by stable lead ID and `created_at`, not by the list's current total. Report unique-phone count separately only when it differs; never print phone values.
4. Do not trust `start_date`/`end_date` query parameters unless the response total and every returned timestamp prove the server applied them; the leads endpoint may silently ignore those parameters.
5. Prefer one API page large enough to contain every record from now back through the requested day. Require the response to honor `per_page`, sort descending by `created_at`, and have its oldest row before the window start (or be the list's final page). This avoids offset-boundary loss when live inserts shift pages or many rows share a timestamp.
6. If one-page coverage is impossible, locate the closed-day page band, include newer/older margin pages, read newest-to-oldest, de-duplicate by lead ID, and repeat until two consecutive passes add zero target IDs. Verify both time boundaries are covered.
7. Treat list membership as live, not append-only. A lead can disappear after deletion or reconciliation, so repeated closed-day snapshots can shrink. If exact sets change, label the result as the current list snapshot with an `as_of` time; do not claim immutable gross historical ingress unless an append-only event source proves it.
8. State list names, counts, timezone, closed interval and API source. Keep access tokens, credentials, phone values and raw lead payloads out of logs and chat.

### Funnel-stock versus historical flow

SMS Funnel lists represent the lead's current funnel stage, not an append-only event ledger. The vendor's integration documentation states that each event moves the customer to the corresponding list and removes the customer from the prior list. Therefore:

- a current D1/D2/D3 list snapshot is **stock by stage**, not the gross number that ever entered each stage;
- D3 can be larger than D2 because D2 loses contacts that advance while a terminal D3 accumulates them;
- zero phone overlap between current D3 and current D1/D2 does not disprove lineage; it can be the expected consequence of movement/deduplication;
- never calculate stage conversion or require `D1 >= D2 >= D3` from current membership filtered by `created_at`;
- historical **per-phone progression** requires an append-only router/click/event log or a controlled transition test with pre-read and cleanup authorization;
- read campaign and sequence active states separately, because a list can keep receiving contacts while its bound automation campaign is inactive.

### Actual SMS sends and operating cost

When the goal is daily SMS volume or cost, do not infer sends from list membership or deduplicate phones across stages. Query the platform's sequence analytics for each exact campaign:

```text
GET /api/analytics/funnel-performance/{campaign_id}/sequences?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Paginate the campaign inventory first. Resolve every requested campaign by exact name and exact `lead_list_id`; fail closed on missing or duplicate matches. Verify one intended SMS sequence and the expected vehicle/manager/stage topology, then use `sms_sent` as the platform-recorded send count for the closed day. Read `sms_unit_cost` from consolidated funnel-performance analytics and require the returned cost to match `sms_sent × sms_unit_cost` within rounding tolerance.

For a closed historical day, run the scoped read twice and require identical campaign names, `sms_sent`, unit cost and calculated costs before reporting. Keep the scope exact: do not mix vehicles, neighboring manager codes, other stages or other dates merely because they share the same account. Treat current `campaign_active` as a separate readback field that can change after the reporting day; it neither invalidates nor rewrites historical sends.

A phone that receives D1, later D2 and later D3 represents **three billable SMS sends** and must be counted once at each stage; cross-stage deduplication understates cost. Sum stage-level `sms_sent` values for total sends. Keep carrier delivery separate: `sms_sent` proves a platform-recorded send, not handset delivery. Render the answer as a compact aligned block with stage, sends, unit cost, stage cost and total, then list the exact included campaign names and state the closed period/timezone.

For an intraday request covering **all automations**, paginate the complete `GET /api/campaigns` inventory, de-duplicate by campaign ID, query the sequence-analytics endpoint for every campaign, and sum only its sequence-level `sms_sent` and `cost`. Report the number of campaigns checked and the number with sends. Do not substitute the consolidated account `total_sms_sent`: it can include broadcasts or other non-automation traffic, while its current-day `total_sms_cost` may remain zero even when sequence costs are populated. Require the sequence-cost sum to equal `sms_sent × sms_unit_cost` within rounding tolerance.

Timestamp intraday results with an explicit `as_of` in the operation timezone and rerun immediately before responding. Do not require two live reads to be identical—new sends legitimately change the total between calls; use repeated reads only to validate scope/formula, then publish the latest snapshot and state that it will increase during the day.

The same data is exposed in the current web app under **Relatórios (beta)**:

- **Relatório de cliques em links** (`/#/analytics/campaigns`) lists each automation with `Envios`, `Cliques` and `CTR`; its sequence-detail action shows the same metrics per message sequence.
- **Performance por Funil** (`/#/analytics/funnel-performance`) exposes SMS volume, unit cost, total cost and campaign/sequence drill-down.

These cards are permission/feature gated. The first requires the account's analytics synchronization flag. Performance por Funil additionally requires the funnel-report feature plus administrator access or the user's show-funnel-report permission. If the card is absent or a direct route redirects, treat that as a UI entitlement issue, not proof that the analytics exist only through the API.

## Result format

Report operationally:

```text
step 01 → intended list: lead found, wrong-list matches 0, cleanup confirmed
step 02 → intended list: lead found, wrong-list matches 0, cleanup confirmed
step 03 → intentionally unmapped, zero webhook action
```

State separately:

- whether carrier SMS delivery was or was not tested;
- whether all current step-01/02 routes passed;
- whether the final step-03 automation is fully ready for a future List 4;
- any naming-only drift that did not affect list IDs or routing.

Do not expose synthetic phone values, access tokens, webhooks or raw API responses.
