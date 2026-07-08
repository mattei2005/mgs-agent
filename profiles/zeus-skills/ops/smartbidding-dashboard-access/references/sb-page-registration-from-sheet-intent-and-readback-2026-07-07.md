# SB Messenger Page registration from Sheet — intent + readback notes (2026-07-07)

## Trigger / intent correction

When Rodolfo sends a compact row like:

```text
login@gmail.com    <FB_PAGE_ID>    <PAGE_ID>    <PAGE_NAME>
```

and says `cadastra essa`, especially with a Google Sheet link to the SB registration tab, treat it as **Smart Bidding Messenger Page registration**, not user authorization.

Operational target:

```text
Smart Bidding → Accounts → Messenger → Page → New Page
```

Use the linked Sheet row as the execution payload.

## Sheet row fields observed

Sheet `gid=907050576` contained columns:

- Messenger User/login
- FB Page ID
- Page ID
- Page Name
- Country
- Vertical
- Source
- UTM Campaign
- Status
- NOTES
- BROADCAST Message Template
- Current Message ID
- Message ID

For row `Bruna Babdinto`:

```text
login: disparoseggbev@gmail.com
FB_PAGE_ID: 785366574671025
PAGE_ID: 11877
PAGE_NAME: Bruna Babdinto
COUNTRY: United States
VERTICAL: Credit card
SOURCE: Facebook
UTM_CAMPAIGN: pg_11877
STATUS in Sheet: READY
NOTES: Segurador - Jack Smith
Current Message ID: 1
Message ID: -1
```

## Registration pattern validated

1. Read the Sheet via Google `gviz` CSV endpoint when browser/web extract is not needed:

```text
https://docs.google.com/spreadsheets/d/<sheet_id>/gviz/tq?tqx=out:csv&gid=<gid>
```

2. Fetch live SB full Messenger Page scope (`digital-trust` + `digital-trust-2`, all child publishers) and check for existing/conflict rows by `FB_PAGE_ID` and `PAGE_ID` before POST.
3. Resolve `MESSENGER_USER_ID` from `/users/Messenger`; fallback to an existing page row for the same login only if needed.
4. Resolve the broadcast template by the instruction `Escolher o template ref ao site, independente da vertical`: prefer an existing page row for the same login/site carrying the active template. For `disparoseggbev@gmail.com`, the validated template was:

```text
BROADCAST_TEMPLATE_ID: 691bbfd5-e13c-f552-4b39-3dedf76d15bf
BROADCAST_TEMPLATE_NAME: Eggbev - US-CC-EN/EN-SR - g006-d Nicolas
```

5. POST to `/campaigns/Messenger` with a single-row payload. For Sheet `READY`, map to SB enum `Ready` (proper case), not uppercase `READY`.
6. Validate by readback.

## API payload shape

Validated create payload shape:

```json
{
  "MESSENGER_USER_ID": "<resolved user id>",
  "PAGE_ID": "11877",
  "FB_PAGE_ID": "785366574671025",
  "PAGE_NAME": "Bruna Babdinto",
  "UTM_CAMPAIGN": "pg_11877",
  "STATUS": "Ready",
  "SOURCE": "Facebook",
  "VERTICAL": "Credit card",
  "COUNTRY": "United States",
  "NOTES": "Segurador - Jack Smith",
  "BROADCAST_TEMPLATE_ID": "691bbfd5-e13c-f552-4b39-3dedf76d15bf",
  "BROADCAST_CURRENT_MESSAGE_ID": "1",
  "BROADCAST_MESSAGE_ID": "-1"
}
```

SB returned HTTP `201` with the new row ID.

## Readback pitfalls

- `GET /campaigns/Messenger/{ID}` can validate the newly created row immediately even when a full-scope list query does not show it on the first immediate read.
- On a later full-scope re-fetch, the row appeared and validated correctly.
- In full list output, the login may appear under `LOGIN` while `USER_LOGIN` is `null` for newly created rows. Do not fail readback solely because `USER_LOGIN` is null if `LOGIN` matches and `MESSENGER_USER_ID` matches.

Validated final readback for Bruna Babdinto:

```text
ID: 6a4da73a-0f3c-ea81-26cc-819048c7728d
LOGIN: disparoseggbev@gmail.com
PAGE_ID: 11877
FB_PAGE_ID: 785366574671025
PAGE_NAME: Bruna Babdinto
UTM_CAMPAIGN: pg_11877
STATUS: Ready
NOTES: Segurador - Jack Smith
BROADCAST_TEMPLATE_NAME: Eggbev - US-CC-EN/EN-SR - g006-d Nicolas
BROADCAST_CURRENT_MESSAGE_ID: 1
BROADCAST_MESSAGE_ID: -1
```
