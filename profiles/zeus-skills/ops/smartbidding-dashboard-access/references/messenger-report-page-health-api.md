# SB Messenger Report API Notes — Page Health Monitoring

Session-derived notes for using Smart Bidding's Messenger Pages report as the delivery/lead layer in MGS page-health monitoring.

## Dashboard route

```text
https://app.smartbiddingdigital.com/reports/messenger
Title observed: Messenger Pages
```

Use headed Playwright under Xvfb with stored state. Raw navigation may show an SPA 404 response while the app renders normally; validate by body/table content.

## Internal endpoint

Observed authenticated call:

```text
POST https://api.jbfdigital.com.br/report/messenger
```

Example request shape:

```json
{
  "initialDate": "2026-06-30T02:53:19.096Z",
  "finalDate": "2026-06-30T02:53:19.096Z",
  "publishers": ["digital-trust_<domain>", "..."],
  "currency": null
}
```

In the observed run, the endpoint returned a JSON list with 1937 rows. Do not print auth headers/cookies/bearer tokens.

## Key fields

```text
DATE
COMPANY
DOMAIN
USER_LOGIN
PROFILE_NAME       segurador/profile name
PAGE_ID            Facebook page ID
USERNAME           page username
PAGE_NAME
STATUS             Broadcast / Campaign etc.
UTM_CAMPAIGN
COUNTRY / VERTICAL / LANGUAGE
LEADS_TOTAL
LEADS
SUBSCRIBED
UNSUBSCRIBERS
SENDS
DELIVEREDS
BD_SENDS
BD_DELIVEREDS
DRIP_DELIVEREDS
SESSIONS
CTR
REVENUE
BD_REVENUE
DRIP_REVENUE
```

Dashboard visible headers may differ slightly (e.g. `FB_PAGEID` in UI text), but the API row used `PAGE_ID`.

## Filtering pattern

For a specific page, filter rows locally by:

```text
PAGE_ID == "<fb_page_id>"
OR lower(PAGE_NAME) == lower("<page name>")
OR lower(PROFILE_NAME) == lower("<segurador>")
```

Validated example:

```text
PAGE_ID       796622570197092
PAGE_NAME     Patricia Smith
PROFILE_NAME  Dân Kbang
DOMAIN        zytiva
USER_LOGIN    disparoszytiva@gmail.com
STATUS        Broadcast
UTM_CAMPAIGN  pg_13788
LEADS_TOTAL   1396
LEADS         495
SENDS         0
DELIVEREDS    0
BD_SENDS      0
BD_DELIVEREDS 0
DRIP_DELIVEREDS 0
REVENUE       0
```

Rodolfo clarified that `0 sends/delivered` can be intentional during Utility-template/broadcast reconfiguration, so do not alert on zero alone without expected-active/baseline context.

## Authenticated browser-fetch caveat

When using Playwright to call `POST https://api.jbfdigital.com.br/report/messenger` from the logged-in SB dashboard, the UI authentication token may not be attached automatically to a custom `fetch`. The dashboard stores the current bearer token in `sessionStorage.ac`.

Do not print this token. Use it only inside browser context:

```javascript
const token = sessionStorage.getItem('ac');
const res = await fetch('https://api.jbfdigital.com.br/report/messenger', {
  method: 'POST',
  headers: {
    'content-type': 'application/json',
    'authorization': 'Bearer ' + token
  },
  body: JSON.stringify(payload)
});
```

If the same page is visibly logged in but the manual API call returns `401 Unauthorized`, missing `authorization: Bearer ${sessionStorage.ac}` is the first thing to check.

## Date / zero-row caveat

The Messenger report can legitimately return `[]` for the new UTC/current day before data exists. Before posting a page-health report, validate that the period is the intended period and that the row count is plausible. If today's query returns zero unexpectedly, retry with the last complete day or the user-requested reporting date before posting.

Operational validation before posting:

```text
- SB report row count is non-zero for the intended period, unless zero rows is the anomaly being reported.
- PAGE_ID matching count is recorded.
- Domain/User values are derived from SB rows, not copied from examples.
- If an earlier placeholder/zero-row report was posted, identify the corrected final Message ID to Rodolfo.
```

## Operational meaning

Use SB Messenger Report for operational delivery/lead state:

```text
Question                                Field/source
--------------------------------------  ---------------------------------------------
Is page in SB reporting?                row exists for PAGE_ID
Which segurador/profile controls it?    PROFILE_NAME
Which login/account?                    USER_LOGIN
Is it Broadcast/Campaign?               STATUS
How many ChatPion/SB leads?             LEADS_TOTAL / LEADS
Is broadcast sending?                   SENDS / BD_SENDS
Is broadcast delivering?                DELIVEREDS / BD_DELIVEREDS / %DELIVERED
Is drip delivering?                     DRIP_DELIVEREDS
Is it driving sessions/revenue?          SESSIONS / CTR / REVENUE
```

Use Meta Graph for page access/publication/bot subscription/conversations; use SB/ChatPion for subscribers/leads and delivery metrics.

## Alerting guidance

Good page-delivery alert requires at least two dimensions:

```text
Meta page OK + SB delivery bad        => ChatPion/SB/template/disparo issue
Meta page bad + SB delivery bad       => page/profile/token/access issue
App rate-limit high + delivery bad    => app/rate-limit issue
Everything OK but leads/revenue down  => funnel/traffic/offer issue
```

Avoid false positives by maintaining expected-active/maintenance flags, especially during Utility-template migrations.
