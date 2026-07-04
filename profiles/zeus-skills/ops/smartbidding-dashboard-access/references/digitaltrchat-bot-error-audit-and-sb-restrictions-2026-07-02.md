# DigitalTRChat bot error audit + Smart Bidding restriction workflow — 2026-07-02

## Context

Rodolfo mapped the operational bridge between DigitalTRChat/ChatPion bot reports and Smart Bidding Messenger Page controls.

Goal: before treating a Messenger Broadcast Template purple/error approval bar as a copy/template problem, identify whether one or more pages in the bot are actually restricted, missing permissions, tied to a deleted app, outside the allowed messaging window, or have no campaign report yet.

## DigitalTRChat internal endpoints

The public ChatPion/DigitalTRChat API docs do **not** expose the useful “Last 7 days error report” / campaign report data. The dashboard uses authenticated internal endpoints with session cookies + CSRF.

Observed route:

```text
GET  https://digitaltrchat.com/messenger_bot_enhancers/subscriber_broadcast_campaign
```

Main campaigns table:

```text
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
```

Campaign report modal init:

```text
POST /messenger_bot_enhancers/campaign_sent_status
payload: id=<campaign_id>, csrf_token=<csrf>
```

Per-subscriber report data:

```text
POST /messenger_bot_enhancers/campaign_sent_status_data
payload: campaign_id=<campaign_id>, csrf_token=<csrf>, DataTables params
```

Dashboard JS confirms the filters:

```text
search_page_id       page dropdown value
search_status        0 Pending, 1 Processing, 2 Completed, 3 Stopped, 4 On-hold
search_value         search box
campaign_date_range  optional date filter
csrf_token           #csrf_token hidden input
```

## What to extract

For each bot user:

1. Login to `digitaltrchat.com` using the bot credentials from 1Password.
2. Open `/messenger_bot_enhancers/subscriber_broadcast_campaign`.
3. Read the `search_page_id` dropdown; each option is a page in that bot user.
4. For each page, query recent campaigns via `/subscriber_broadcast_campaign_data`.
5. If no rows: report `NO_REPORT` for that page.
6. If rows exist but no sent/completed campaign: report `NO_SENT_YET`.
7. For sent/completed campaigns, open the report via `/campaign_sent_status`, then query `/campaign_sent_status_data`.
8. Classify `Sent response` values:
   - `Sent : ...` / `Sent :: ...` = OK, no report needed.
   - `(#2022) ... temporarily restricted ... until DATE` = page temporarily restricted.
   - any other error = report to Rodolfo; do not auto-fix.

Default reporting should include only exceptions, not OK pages.

## #2022 workflow agreed by Rodolfo

For confirmed temporary messaging restriction:

```text
DigitalTRChat error: #2022 restricted until DATE
Smart Bidding action: Status = Broadcast
Restricted Until: DATE + 1 day
```

Rationale:

- Ciro’s scheduler already avoids pages with `Restricted Until` in the future.
- Setting `Status = Broadcast` also removes the page from the Broadcast Template `PAGES` count and from the practical approval/send pool.
- This keeps template page counts aligned with “pages actually available to send/approve.”

When the date passes, reactivation requires manual/automated cleanup:

```text
Edit Messenger Page
→ Broadcast tab
→ Restricted Until calendar
→ Clear
→ Save
→ restore Status to Broadcast when ready to send again
```

Do **not** use `Blocked` as the default for every error. Use it automatically only for the agreed `#2022` case unless Rodolfo approves more categories.

## Broadcast Template PAGES semantics

Rodolfo clarified and live validation confirmed:

```text
Broadcast Template PAGES = Page rows with Status Broadcast + Status Campaign
```

`Campaign` is operationally active and sends broadcast; some gestores leave pages in `Campaign` after launching campaigns.

The following statuses are excluded from the Broadcast Template `PAGES` count:

```text
Blocked
On-hold
```

For operational availability, also exclude rows with active `RESTRICTED_UNTIL` even if status still says `Broadcast`.

## Error categories seen in phase-1 scan

Treat these as triage buckets:

```text
#2022 temporary restriction       Auto-action candidate after Rodolfo-approved rule.
Permission missing/pages_messaging Investigate app/page permissions/profile access.
Application has been deleted      Developer app issue; app/profile migration likely.
#10 outside allowed window        Messaging policy/window issue; do not block automatically.
#551 person unavailable           Subscriber-level availability; usually not page restriction.
#100 template not found           Template/content mapping issue.
Token/session invalid             Token/profile auth issue.
Other/non-code errors             Report exact response.
```

## Smart Bidding update path

For SB Messenger Page rows, the authenticated SPA API can update fields with:

```text
PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many
payload: {"ids":[<row ID>], "RESTRICTED_UNTIL":"YYYY-MM-DD", "STATUS":"Broadcast"}
```

Use the headed/Xvfb SB route to capture current `/campaigns/Messenger` auth headers and validate by re-reading the row after update. Never report success without readback.

## Reporting shape for Rodolfo

Phase 1 diagnostics:

```text
Usuários testados
Logins OK
Usuários sem páginas no bot
Páginas sem report/campanha
Páginas com erro
Páginas com #2022
```

Then list only exception pages, grouped by actionability:

```text
#2022 — ready for Fase 2
Other errors — investigate first
No report — likely page added but not used yet
No pages in bot — inventory/setup note
```

OK pages should be omitted unless Rodolfo explicitly asks for full inventory.


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
