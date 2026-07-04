# DigitalTRChat → Smart Bidding page restriction workflow — 2026-07-02

Use this when Rodolfo asks to diagnose purple/error Messenger template approvals caused by page-level broadcast restrictions and then suppress the affected page from future scheduling/approval runs.

## Confirmed internal DigitalTRChat endpoints

The public ChatPion/XeroChat API docs do **not** expose the useful “Last 7 days error report” or broadcast subscriber-send error table. The working source is the logged-in DigitalTRChat dashboard XHR flow.

Logged-in route:

```text
https://digitaltrchat.com/messenger_bot_enhancers/subscriber_broadcast_campaign
```

Network/XHR endpoints observed:

```text
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
  Main Subscriber broadcast campaign DataTable.
  Important POST params added by the page JS:
    search_page_id
    search_value
    search_status
    campaign_date_range
    csrf_token

POST /messenger_bot_enhancers/campaign_sent_status
  Opens the Campaign report modal for a `cam-id`.
  Params:
    id
    csrf_token

POST /messenger_bot_enhancers/campaign_sent_status_data
  Subscriber-level send report inside the modal.
  Params:
    campaign_id
    csrf_token
```

The campaign list row action HTML contains `cam-id="..."` for the report. The page stores a hidden `#csrf_token`; use the dashboard’s own session/cookies and `X-Requested-With: XMLHttpRequest`.

## Error interpretation

A page-level temporary suspension shows in the report table `Sent response` as:

```text
(#2022) You're temporarily restricted from messaging users until July 22 at 7:55 AM.
```

Operational meaning:

```text
Sent at      green/check timestamp means the attempt was made.
Delivered   red/remove means it did not deliver.
Sent response #2022 means temporary Messenger send restriction.
```

This is not evidence that the broadcast template copy is bad. It is a page/profile messaging restriction that can contaminate Run Approval and make a whole template look purple if the approval picks that page first.

## Smart Bidding suppression rule

For temporary `#2022` errors, do **not** set the Page status to `Blocked` by default.

Use Smart Bidding:

```text
Accounts > Messenger > Page > edit page > Broadcast tab > Restricted Until
```

Set:

```text
Restricted Until = one calendar day AFTER the date in the DigitalTRChat error.
```

Example:

```text
DigitalTRChat error: restricted until July 22 at 7:55 AM
Smart Bidding:       RESTRICTED_UNTIL = 2026-07-23
Status:              keep Broadcast
```

This removes the page from scheduling/routing while preserving it as an active Broadcast page after the restriction window.

Use `Status = Broadcast` only for permanent/page-dead cases, profile/developer account collapse, or when Rodolfo explicitly wants the page removed from operation.

## Validated Zytiva test

Credential item used:

```text
1Password: Digitaltrchat - Disparos Zytiva US-CC-EN
URL:       https://digitaltrchat.com/home/login
User:      disparoszytiva@gmail.com
```

Test pages:

```text
Katherine Cook
  SB PAGE_ID: 13784
  FB_PAGE_ID: 940119419174810
  USER_LOGIN: disparoszytiva@gmail.com
  PROFILE_NAME: Dân Kbang
  DigitalTRChat report: #2022 restricted until July 22 at 7:55 AM
  Action taken: RESTRICTED_UNTIL = 2026-07-23
  Validation: STATUS remained Broadcast; RESTRICTED_UNTIL read back as 2026-07-23

Camila Rosas
  SB PAGE_ID: 1250
  FB_PAGE_ID: 482185738302814
  PROFILE_NAME: Simone Oliveira
  DigitalTRChat report: Sent response showed `Sent : ...`
  Action: no edit; no suspension detected
```

## API update path in Smart Bidding

The page restriction can be applied through the authenticated Smart Bidding SPA API after capturing headers from the headed browser session:

```text
PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many
Payload:
{
  "RESTRICTED_UNTIL": "YYYY-MM-DD",
  "ids": ["<SB row ID>"]
}
```

Validation is mandatory: re-read `/campaigns/Messenger` and confirm:

```text
STATUS == Broadcast
RESTRICTED_UNTIL == target date
PAGE_NAME / PAGE_ID / USER_LOGIN match the intended page
```

## Practical diagnostic sequence

1. Log into the specific DigitalTRChat bot user from 1Password.
2. Open Subscriber broadcast.
3. Select the target page via `search_page_id` or UI Page filter.
4. Filter `Completed` campaigns first when looking for real send responses.
5. Open the Campaign report (`cam-id`).
6. Read `Sent response` from `campaign_sent_status_data`.
7. If `#2022` appears, extract the restriction date.
8. Find the same page in Smart Bidding `Accounts > Messenger > Page` using `PAGE_NAME`, `PAGE_ID`, `FB_PAGE_ID`, `USER_LOGIN`, and `PROFILE_NAME`.
9. Set `RESTRICTED_UNTIL` to one day after the error date; keep `STATUS=Broadcast`.
10. Re-read Smart Bidding and report only confirmed status.

## Pitfalls

- Do not rely on the public ChatPion API docs for this problem; they expose subscriber fields like `last_error_message`, but not the campaign error report needed here.
- Do not treat purple approval as a copy/template failure before checking page-level `#2022` errors.
- Do not set `Blocked` for temporary `#2022` unless Rodolfo explicitly asks.
- Do not trust a global search in DigitalTRChat DataTables unless the page JS supports that parameter. Prefer `search_page_id` from the Page dropdown or direct DataTable POST params.
- Do not print passwords, cookies, CSRF tokens, or bearer headers in reports.


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
