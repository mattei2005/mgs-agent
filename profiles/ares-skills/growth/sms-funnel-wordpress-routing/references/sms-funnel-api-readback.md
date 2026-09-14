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
