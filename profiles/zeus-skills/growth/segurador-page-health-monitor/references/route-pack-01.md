## Scope

This skill is for monitoring **segurador/profile + Facebook Pages** health.

Do **not** mix this with the B001–B010 Meta app/rate-limit monitor. App roles, app owner profiles, app rate-limit, and X-App-Usage belong to `meta-app-rate-limit-monitor`.

This monitor answers:

```text
Question                                      Source
--------------------------------------------  --------------------------------------------
Segurador/profile token still works?          Meta Graph API /me + /debug_token
Which pages are inside the segurador?         Meta Graph API /me/accounts
Page disappeared/lost access?                 Meta Graph API /me/accounts diff
Page published or unpublished?                Meta Graph API /{page_id}.is_published
Bot/app still subscribed to page?             Meta Graph API /{page_id}/subscribed_apps
Messenger conversations readable?             Meta Graph API /{page_id}/conversations
Page stopped receiving leads?                 Smart Bidding / ChatPion Messenger report
Lead count by page                            SB/ChatPion report, not Meta Lead Forms
```

## Mental Model

The operational chain here is:

```text
Segurador Facebook profile
→ owns/has access to Facebook Pages
→ page receives Messenger traffic
→ ChatPion/DigitalTrChat/SB registers subscriber/lead metrics
→ page should keep producing leads/messages while active
```

If a page stops receiving leads overnight, likely causes include:

```text
- page got restricted;
- page unpublished/disabled;
- segurador/profile lost access;
- page token / bot subscription broke;
- ChatPion/SB mapping broke;
- Utility/template/broadcast setup is paused or being reconfigured;
- traffic/source stopped, if Meta + SB health are otherwise OK.
```

## Required Token Item Pattern

Use one 1Password item per segurador/profile token.

Example:

```text
Segurador Dân Kbang (B005) Token
```

Expected fields:

```text
field         purpose
------------ -------------------------------------------------------
segurador    Human profile/segurador name, e.g. Dân Kbang
access_token User access token for the segurador/profile
expires_at   Token expiry or non-expiring indicator
app_id       App ID used to debug token, if available
app_secret   App secret used only for /debug_token; never print
```

Never print access tokens, page tokens, app secrets, cookies, Auth0 tokens, or bearer tokens.

## Permission Guidance

For the page/segurador monitor, useful permissions include:

```text
pages_show_list             List pages in /me/accounts
pages_read_engagement       Read page basic metrics/engagement
pages_read_user_content     Read page user content where available
pages_messaging             Read Messenger conversations/messages where allowed
pages_manage_metadata       Validate bot/subscribed app / metadata
pages_manage_posts          Read/manage posts where needed for diagnostics
pages_manage_engagement     Engagement diagnostics
business_management         Business/page visibility when needed
read_insights               Insights endpoints
```

For **lead forms** only, use:

```text
leads_retrieval
pages_manage_ads
```

But MGS lead monitoring for this workflow is usually **not Lead Forms**. Rodolfo clarified that the important leads are Messenger/ChatPion/SB leads, so the primary source for lead counts is the SB/ChatPion Messenger report.

## Meta Graph API Checks

Given a segurador token:

```text
GET /me?fields=id,name
GET /debug_token?input_token={access_token}     using app_id|app_secret when available
GET /me/accounts?fields=id,name,category,tasks,access_token
```

For every page returned by `/me/accounts`:

```text
GET /{page_id}?fields=id,name,category,fan_count,followers_count,verification_status,is_published,link
GET /{page_id}/subscribed_apps
GET /{page_id}/conversations?fields=id,updated_time,message_count,unread_count,participants
GET /{conversation_id}/messages?fields=id,created_time,from,to,message,attachments,tags
```

Interpretation:

```text
Condition                                      Severity
---------------------------------------------  -------------------------------
/me fails                                      Critical: segurador token/profile broken
/debug_token invalid                           Critical: token invalid/expired
/me/accounts loses a known page                Critical: page lost access or removed
/{page_id}.is_published=false                  Critical: page unpublished
/{page_id} fails with permissions/access error Critical: page inaccessible/restricted
/subscribed_apps missing expected bot/app      Critical/Risk: bot may not send
/conversations access fails                    Risk/Critical: messaging access issue
```

## SB / ChatPion Messenger Report Checks

Use the Smart Bidding Messenger Pages report:

```text
https://app.smartbiddingdigital.com/reports/messenger
POST https://api.jbfdigital.com.br/report/messenger
```

For page/message suspension symptoms that appear in DigitalTRChat/ChatPion, also inspect the dashboard `Last 7 days error report` modal. Public ChatPion/XeroChat API docs expose `subscriber_information.unavailable` and `last_error_message`, but do not document a reliable endpoint for the full modal, page suspension status, or template approval error aggregation. Preferred path: capture the authenticated internal endpoint via browser DevTools/Network; fallback to logged-in browser automation. See `references/digitaltrchat-error-report-discovery-2026-07-02.md`.

For DigitalTRChat/ChatPion delivery failures, also inspect the broadcast campaign detail page:

```text
https://digitaltrchat.com/messenger_bot_enhancers/subscriber_broadcast_campaign
```

This page can expose row-level `Sent response` errors such as:

```text
(#2022) You're temporarily restricted from messaging users until July 22 at 11:44 PM.
```

Use this to distinguish a restricted page/profile from a bad template/message. The public ChatPion/XeroChat API docs only expose nearby subscriber fields like `unavailable` and `last_error_message`; the useful broadcast error table may come from an internal dashboard/AJAX endpoint or require logged-in browser extraction.

Relevant fields observed:

```text
DATE
COMPANY
DOMAIN
USER_LOGIN
PROFILE_NAME        segurador/profile
PAGE_ID
USERNAME
PAGE_NAME
STATUS              Broadcast/Campaign/etc.
UTM_CAMPAIGN
COUNTRY
VERTICAL
LANGUAGE
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
REVENUE
BD_REVENUE
DRIP_REVENUE
```

For this monitor, focus first on:

```text
PAGE_ID
PAGE_NAME
PROFILE_NAME
STATUS
LEADS_TOTAL
LEADS
SENDS / BD_SENDS
DELIVEREDS / BD_DELIVEREDS / DRIP_DELIVEREDS
SESSIONS
```

For DigitalTRChat/ChatPion broadcast-send failures, inspect subscriber campaign reports before classifying a page as permanently broken. The logged-in dashboard exposes useful internal XHRs behind `Broadcasting > Subscriber broadcast`:

```text
POST /messenger_bot_enhancers/subscriber_broadcast_campaign_data
POST /messenger_bot_enhancers/campaign_sent_status
POST /messenger_bot_enhancers/campaign_sent_status_data
```

The subscriber report includes `Sent response`; errors like `(#2022) You're temporarily restricted from messaging users until July 22...` mean the page should usually be excluded temporarily, not permanently blocked. Rodolfo's SB cleanup rule: in Smart Bidding `Accounts > Messenger > Page`, keep the page `Status=Broadcast`, then edit `Broadcast > Restricted Until` to one calendar day after the error's until-date. Example: error until July 22 -> set July 23. Use `Status=Blocked` only for permanently dead/retired pages or profile/page failures that should leave the operation.

## Simple Alert Logic

Keep the first version simple. Do not involve app/rate-limit.

