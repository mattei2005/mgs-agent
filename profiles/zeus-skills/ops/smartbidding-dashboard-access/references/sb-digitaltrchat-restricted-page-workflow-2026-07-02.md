# DigitalTRChat restricted-page workflow — purple approval cleanup

Session: 2026-07-02 with Rodolfo.

## Problem

Messenger Broadcast Template approval bars can turn purple when the approval/run uses a page that is temporarily restricted from sending Messenger messages. In large shared templates, one bad page can contaminate the visible approval result and make the whole template look purple, even when the copy/messages are not the root cause.

Operational implication: **purple is not a copy-change decision by itself**. First diagnose page/profile/app health and remove restricted pages from the sending/approval pool.

## Confirmed DigitalTRChat internal endpoints

Public ChatPion/XeroChat API docs do not expose the needed "Last 7 days error report" / per-campaign sent response directly. The useful data is available through the logged-in DigitalTRChat dashboard XHRs.

Observed working route with a logged-in session:

```text
GET  /messenger_bot_enhancers/subscriber_broadcast_campaign
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
POST /messenger_bot_enhancers/campaign_sent_status
POST /messenger_bot_enhancers/campaign_sent_status_data
```

Key observations:

```text
subscriber_broadcast_campaign_data  returns campaign rows and action HTML with cam-id.
campaign_sent_status                opens the campaign report modal for a cam-id.
campaign_sent_status_data           returns subscriber-level rows with Sent at, Delivered at, Sent response.
```

Example error seen in the UI/report:

```text
(#2022) You're temporarily restricted from messaging users until July 22 at 11:44 PM.
```

The endpoints are internal dashboard endpoints, not clean public API endpoints. They depend on logged-in session/cookies and CSRF. Preferred extraction pattern is headed Playwright/Xvfb using the active browser session and capturing/fetching the XHRs from page context. Do not print cookies, CSRF tokens, session IDs, or credentials.

## Operational workflow

When a template has purple/error approval:

```text
1. Open DigitalTRChat bot/user.
2. Go to Broadcasting > Subscriber broadcast:
   /messenger_bot_enhancers/subscriber_broadcast_campaign
3. Open the relevant campaign report via the eye/Campaign report.
4. Inspect subscriber-level Sent response.
5. If the error is #2022 temporary restriction, extract the restriction date/time.
6. Open Smart Bidding > Accounts > Messenger > Page.
7. Locate the exact page row.
8. Keep Status = Broadcast for temporary restrictions.
9. Edit row > Broadcast tab > Restricted Until.
10. Set Restricted Until to **the same calendar date as** the error's until-date.
    Example: error says July 22 -> set July 23.
11. Save.
12. Re-run/await approval after the restricted page is excluded from routing.
```

## Status vs Restricted Until

```text
Condition                                      SB action
---------------------------------------------  ---------------------------------------------
#2022 temporary messaging restriction until X   Keep Status=Broadcast; set Restricted Until=X (same date).
Known permanently broken/dead page              Set Status=Blocked.
Segurador/profile/developer fell                Investigate/migrate profile/app/page; Blocked only if retiring it.
Template still purple after restricted cleanup  Diagnose developer/profile/app/template, not page-temp-restriction.
```

Do **not** use Status=Blocked as the default for temporary Messenger send restrictions. Rodolfo corrected the intended flow: keep Broadcast and use Restricted Until one day after the error date.

## Smart Bidding audit view

Useful SB path:

```text
Accounts > Messenger > Broadcast Template
→ filter exact template
→ note Messages, Leads, Pages, Approval
→ Accounts > Messenger > Page
→ filter/join by Template Name
```

Inspect page rows for:

```text
Restricted / Restricted Until
Status != Broadcast
On-hold
Message ID = -1
Current Message ID
Last Schedule
Template Name
Broadcast_Time
```

Important UI pitfall: a page can visually show `Status=Broadcast` and also have a red `Restricted` badge. Treat that as restricted for routing/approval risk. Also, text filtering by `restricted` in a column may not reliably find the badge; prefer backend row data/XHR or visual review after filtering by template.

## Decision rule for purple

```text
Purple approval/error is a diagnosis queue, not a message-replacement trigger.

Before changing copy:
1. Identify affected page/campaign Sent response.
2. Exclude temporary restricted pages via Restricted Until = same error date.
3. Retry/await approval.
4. Only replace message copy for true rejected/red policy/copy errors.
```


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
