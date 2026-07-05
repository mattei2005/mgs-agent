---
name: smartbidding-dashboard-map
description: Use when Rodolfo asks where something lives inside the Smart Bidding dashboard, asks for SB reports/menus/routes/endpoints, or requests a new SB analysis beyond the already-known Messenger workflows. Provides the read-only dashboard map and routing rules; pair with smartbidding-dashboard-access for login/API execution.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, smartbidding, dashboard-map, sb, reports, routes, api, menu]
    related_skills: [smartbidding-dashboard-access]
---

# Smart Bidding Dashboard Map — MGS

## Overview

This skill is the dashboard-wide map for `https://app.smartbiddingdigital.com/` under the Zeus SB account. It complements `smartbidding-dashboard-access`:

- `smartbidding-dashboard-access` = how to log in and execute known SB workflows safely.
- `smartbidding-dashboard-map` = where dashboard sections, report routes, table columns, and SPA API endpoints live.

Use this skill before broad SB investigations so Zeus can route the request to the right screen/API without guessing.

## Source and Validation

Initial map captured live on **2026-07-05 ET** with headed Playwright/Xvfb, authenticated as `Zeus - Agent`, in read-only mode.

Captured artifacts:

- `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-crawl-20260705-010029.json`
- `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-routes-20260705-010957.json`
- `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-routes-deep-20260705-012422.json` — recapture with long waits; resolved every initial `LOADING...` route.

Mode:

- No Save/Update/Delete/Import/Run Approval buttons were intentionally clicked.
- Some SB report/table screens use `POST` for read/query endpoints (`/report/...`, `/photo/...`, `/routing`, `/estimated/...`). Treat those as read-query POSTs unless the endpoint is an explicit write route like `/update-many` or `/broadcast/Messenger` POST with template payload.
- Live SB/DTR always wins over this map if runtime has drifted.

## Mandatory Pairing

Before executing against the dashboard:

1. Load `smartbidding-dashboard-access` for login, headed browser, Auth0/BotGuard, credentials, full MGS scope, and write safety rules.
2. Use this map to choose the screen/API.
3. Re-query live. Do not answer operational state from the map alone.
4. For any write, backup exact rows and get confirmation when required by AGENT.md/MGS rules.

## Top-Level Menu Map

```text
Menu / area        Route or route family                                Primary use
-----------------  ----------------------------------------------------  -------------------------------------------
Dashboard          /                                                     KPI cards, daily/monthly overview
Reports            /reports/*                                            Revenue, acquisition, channel, health reports
Accounts           /accounts                                             Account/User/Page/Broadcast Template config
Smart Routing      /company/{company}/{domain}/routing                   Routing pools and RPP route performance
Ads Pilot          /ads-pilot                                            Ads pilot config/manager
IA Content         /company/{company}/{domain}/content-ia                AI content queue/workflow
Quiz Maker         /company/{company}/{domain}/quiz-maker                Quiz inventory/config
OKRS               /okrs and /okrs/dashboard                             OKR list and dashboard
Users              /users                                                Dashboard users/roles/companies
Changelog          /changelog                                            Internal changelog table
Helpdesk           /helpdesk                                             Support tickets
Notifications      /notifications                                        Dashboard notifications
My Profile         /my-profile                                           Profile/security settings
```

Known company/domain route examples from the live Zeus scope:

```text
/company/digital-trust/autocreditadx/routing
/company/digital-trust/autocreditadx/content-ia
/company/digital-trust/autocreditadx/quiz-maker
```

For other domains, derive route parameters from the selected company/domain context in the UI; do not assume `autocreditadx` is always the target.

## Accounts Area

Route: `/accounts`

Source selector determines the tab set. For MGS Messenger work, explicitly select `Messenger` and validate the full `digital-trust + digital-trust-2` scope before analysis/writes.

```text
Source/tab                Key columns / purpose
------------------------  ------------------------------------------------------------------------------
Default/Google accounts   COMPANY, DOMAIN, ACCOUNT NAME, ACCOUNT ID, TIMEZONE, CURRENCY, COUNTRY,
                          VERTICAL, LOGIN CUSTOMER ID, TOKEN UPDATED AT, ACTIVE
Messenger > Account      COMPANY, URL, STATUS
Messenger > User         COMPANY, DOMAIN, URL, NAME, LOGIN
Messenger > Page         COMPANY, DOMAIN, URL, USER NAME, LOGIN, PROFILE NAME, PAGE ID, FB PAGE ID,
                          PAGE NAME, UTM CAMPAIGN, LEADS TOTAL, LEADS ACTIVE, LEADS ACTIVE%, SOURCE,
                          VERTICAL, COUNTRY, NOTES, HOLDER 1, HOLDER 2, ADVERTISER, DATE START,
                          RESTRICTED UNTIL, TEMPLATE NAME, LANGUAGE, BROADCAST_TIME,
                          CURRENT MESSAGE ID, MESSAGE ID, LAST SCHEDULE, STATUS
Messenger > Broadcast    COMPANY, DOMAIN, LANGUAGE, NAME, MESSAGES, LEADS, PAGES, APPROVAL
```

Key live endpoints observed:

```text
GET /accounts/Google
GET /accounts/Facebook
GET /accounts/Messenger
GET /users/Messenger
GET /campaigns/Messenger
GET /broadcast/Messenger
```

Important semantic corrections inherited from the access skill:

- `Broadcast Template PAGES` is not the same as Page-tab row count.
- Messenger Page `MESSAGE ID` maps to `BROADCAST_MESSAGE_ID`; `CURRENT MESSAGE ID` maps to `BROADCAST_CURRENT_MESSAGE_ID`.
- `PAGES` for Messenger templates means active `Broadcast + Campaign`; `Blocked`/`On-hold` are excluded, and active `RESTRICTED_UNTIL` still affects send availability.

## Reports Menu Map

Visible Reports submenu captured live:

```text
Report menu item              Route                                      Main table columns / use
----------------------------  -----------------------------------------  ------------------------------------------------------------
Overview                      /reports/overview                         DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACQUISITION,
                                                                         EMAIL, PUSH, SMS, TOTAL, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, SESSIONS, RPS, SENDS, DELIVERED
Domain                        /reports/domain                           DATE/period, COMPANY, DOMAIN, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, SESSIONS, PAGEVIEWS, RPS, RPP, REQUESTS, MATCHED,
                                                                         IMPRESSIONS, COVERAGE, CPM, PRICE, CTR, EPC, %VIEWABLE
Acquisition                   /reports/acquisition                      COMPANY, DOMAIN, SOURCE, COUNTRY, VERTICAL, PRODUCT,
                                                                         ACCOUNT/CAMPAIGN/ADGROUP, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, acquisition clicks/impressions, sessions/ad metrics
Adgroup                       /reports/adgroup                          DATE, COMPANY, DOMAIN, SOURCE, ACCOUNT/CAMPAIGN/ADGROUP/AD,
                                                                         UTM_ADGROUP, investment/revenue/profit/ROI and ad metrics
Vertical                      /reports/vertical                         Domain-style performance grouped by vertical
Inventory                     /reports/inventory                        Company, Domain, Country, Source, Vertical, Medium, Language,
                                                                         In Use, Available, Content
Operation                     /reports/operation                        DATE, COMPANY, DOMAIN, UTM SOURCE, COUNTRY, VERTICAL, PRODUCT,
                                                                         PAGE TYPE, SLOT ID, REVENUE, RPP/RPS, sessions/pageviews/ad ops
URL                           /reports/url                              DATE, URL, COMPANY, DOMAIN, COUNTRY, SOURCE, VERTICAL, PRODUCT,
                                                                         PAGE_TYPE, revenue, sessions/pageviews, ad metrics
Placement                     /reports/placement                        DATE, COMPANY, DOMAIN, SOURCE, account/campaign/placement,
                                                                         investment/revenue/profit/ROI and ad metrics
SMS                           /reports/sms                              DATE, COMPANY, DOMAIN, SOURCE, UTM_CAMPAIGN, MSG_ID, LABEL,
                                                                         MESSAGES, DELIVERED, FAILED, CTR, sessions/ad metrics
Email                         /reports/email                            DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACCOUNT/CAMPAIGN,
                                                                         UTM_CAMPAIGN, AUTO_NAME, REVENUE, SENDS, OPENS, CLICKS,
                                                                         sessions/ad metrics
Pushalert                     /reports/pushalert                        DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, UTM_CAMPAIGN, TITLE,
                                                                         REVENUE, SENDS, DELIVERED, CLICKS, sessions/ad metrics
Youtube                       /reports/youtube                          DATE, CHANNEL, ID, VIDEO, PUBLISHED, VIEWS, REVENUE, ADS, CPM,
                                                                         likes/comments/shares/subscriber/watch metrics
Messenger Insights            /reports/messenger_insights               DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, PERFORMANCE, MESSENGER,
                                                                         DRIP, BROADCAST, cost subscriber/conversion, leads, delivery,
                                                                         sessions and profit/subscriber metrics
Messenger Pages               /reports/messenger                        DATE, COMPANY, DOMAIN, LOGIN, SEGURADOR, FB_PAGEID, PAGE,
                                                                         PAGE_NAME, START DATE, STATUS, UTM_CAMPAIGN, SOURCE, COUNTRY,
                                                                         VERTICAL, LANGUAGE, performance/messenger/drip/broadcast metrics
Messenger Daily               /reports/messenger_daily                  SEGURADOR by daily columns + Total; useful for weekly/daily messenger revenue
Messenger MSGs                /reports/messenger_message                DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, UTM_CAMPAIGN,
                                                                         UTM_CONTENT, TYPE, SENDS, DELIVEREDS, CTR, SESSIONS, PAGEVIEWS
CDP                           /reports/cdp                              DATE, HOUR (when selected), AD_REQUESTS, AD_MATCHED, COVERAGE, PRICE, PAGEVIEWS, SESSIONS;
                                                                         use /report/queryBuilder with publisher `company_domain` for site-level hourly coverage. See `references/cdp-gamezonead-hourly-query-2026-07-05.md`.
Facebook Ads                  /reports/facebook_ads                     DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACCOUNT/CAMPAIGN/ADSET/AD,
                                                                         UTM_CAMPAIGN, investment, conversion/subscriber/click/impression,
                                                                         revenue, profit, ROI, cost/rate metrics
Ads Pilot                     /reports/ads_pilot                        TIME, INVESTIMENT, INVESTIMENT INCREMENTAL, SUBSCRIBERS,
                                                                         CONVERSIONS, COST SUBSCRIBER/CONVERSION, BUDGET, CPA TARGET
Url Healthy                   /reports/urlhealthy                       DATE, COMPANY, DOMAIN, COUNTRY, SOURCE, VERTICAL, URL,
                                                                         ADS REMOVED, ADS HEALTHY, REVENUE REMOVED, OPERATIONS
GAM Key Values                /reports/gam-key-values                   DATE, COMPANY, DOMAIN, KEY, VALUE, REVENUE, AD REQUESTS,
                                                                         AD MATCHES, IMPRESSIONS, CPM, COVERAGE, CTR, %VIEWABLE
Photo by Vertical             /reports/photo-by-vertical                Hourly vertical photo: HOUR, DATE, COMPANY, DOMAIN, investment,
                                                                         revenue/profit/ROI, sessions/pageviews, ad metrics
Photo by Adgroup              /reports/photo-by-adgroup                 Hourly adgroup photo: HOUR, DATE, COMPANY, DOMAIN, investment,
                                                                         revenue/profit/ROI, acquisition clicks/conversions and ad metrics
Photo by Messenger            /reports/photo-by-messenger-insights      Hourly Messenger photo: HOUR, DATE, COMPANY, DOMAIN, Messenger/Drip/
                                                                         Broadcast, cost subscriber/conversion, revenue/profit/ROI,
                                                                         leads/conversions/subscribed/delivereds/sessions/CTR/RPS
Photo by Email                /reports/photo-by-email                   HOUR, DATE, COMPANY, DOMAIN, REVENUE, SENDS, OPENS, CLICKS,
                                                                         sessions/pageviews/ad metrics by hour
Photo by Url                  /reports/photo-by-url                     Hourly URL photo: HOUR, DATE, COMPANY, DOMAIN, REVENUE,
                                                                         PAGEVIEWS, RPP, CPM, AVG PRICE, requests/matched/impressions,
                                                                         coverage, CTR, EPC, viewable
Photo by FacebookAds          /reports/photo-by-facebookads             Hourly FacebookAds photo: HOUR, DATE, COMPANY, DOMAIN,
                                                                         investment diff, subscribers/conversions diff, cost subscriber/
                                                                         conversion diff, clicks/CTR/cost click, impressions/CPM
```

Report read/query endpoints observed:

```text
POST /report/overview
GET  /report/performance_per_domain
POST /report/performance_per_campaigns
POST /report/performance_per_vertical
POST /report/performance_per_operation
POST /report/performance_per_placements
POST /report/performance_per_sms
POST /report/performance_per_email
POST /report/performance_per_pushalert
POST /report/youtube/videos_metrics
POST /report/messenger_insights
POST /report/messenger
POST /report/message
POST /report/facebook_ads
POST /report/ads_pilot_log
POST /report/gam_healthy
POST /report/last_update
POST /report/queryBuilder  # generic report builder; validated for CDP DATE+HOUR site coverage
POST /photo/performance_per_vertical
POST /photo/performance_per_adgroup
POST /photo/messenger_insights
POST /photo/performance_per_email
POST /photo/performance_per_operation
POST /photo/facebookads
GET  /report/dollar
```

## Other Operational Areas

```text
Area            Route                                      Observed columns / buttons                         Observed endpoints
--------------  -----------------------------------------  --------------------------------------------------  -----------------------------
Dashboard       /                                          Daily/Monthly KPI cards, Update                    /report/dollar, performance endpoints
Smart Routing   /company/.../routing                      NAME, SOURCE, COUNTRY, VERTICAL, LANGUAGE,         POST /routing
                                                           MEDIUM, ROUTES, RPP recent days
Ads Pilot       /ads-pilot                                NAME, COMPANY, DOMAINS, ACCOUNTS, CPA_TARGET,      POST /ads_pilot_config
                                                           CPA_MAX, BUDGET_MIN/MAX, TARGETING, STATUS
IA Content      /company/.../content-ia                   Data, Content Key Word, Image Key Word, Category,  GET /content-ia/{company}_{domain}
                                                           Tags, Idioma, URL, Workflow Status, Action
Quiz Maker      /company/.../quiz-maker                   Name, URL, Company, Domain, Country, Vertical,     GET /quizmaker
                                                           Language, Created At
OKRS            /okrs                                     Name, Company, Start Date, Final Date, Profit,     GET /okrs
                                                           Operational Cost, Additional Revenue, Active
Users           /users                                    Name, Email, Roles, Companies                      GET /user, GET /user/validate
Changelog       /changelog                                Date, Company, Domain, Title, Notes, Author, Team  GET /changelog
Helpdesk        /helpdesk                                 Open Date, Company, Domain, Title, Note, Author,   POST /helpdesk/list
                                                           Team, Status, Close Date
Notifications   /notifications                            Company, Domain, Title, Date, Read At              GET /notification
My Profile      /my-profile                               User Info, Security                                profile UI; Save is a write
```

## Routing Recipes

Use these defaults when Rodolfo asks a new SB question:

```text
Question / intent                                Start here
------------------------------------------------ -------------------------------------------------------------
Revenue/profit/ROI by site/domain               Reports > Domain or Overview; endpoint /report/performance_per_domain
Revenue/profit/ROI by vertical                  Reports > Vertical; endpoint /report/performance_per_vertical
Campaign/adgroup/acquisition performance        Reports > Acquisition, Adgroup, Placement
URL-level revenue or health                     Reports > URL or Url Healthy
AdManager/GAM key-value performance             Reports > GAM Key Values
SMS performance                                 Reports > SMS
Email performance                               Reports > Email or Photo by Email for hourly
Pushalert performance                           Reports > Pushalert
YouTube performance                             Reports > Youtube
Messenger page delivery/leads/current errors    Reports > Messenger Pages for metrics; DigitalTRChat for Bot error source
Messenger daily revenue by segurador            Reports > Messenger Daily
Messenger template/page config                  Accounts > Messenger > Broadcast Template / Page
Page schedule/restricted status/message IDs     Accounts > Messenger > Page
Template copy/status/link slots/approval        Accounts > Messenger > Broadcast Template
Routing pool or RPP by route                    Smart Routing
Quiz inventory/config                           Quiz Maker
IA content workflow                             IA Content
Internal users/roles                            Users
Support/tickets                                 Helpdesk
Dashboard changes                               Changelog
```

## Safety Rules

- Treat this skill as a routing/map layer, not a permission to write.
- Any button labeled `New`, `Save`, `Update`, `Resolve`, `Run queue`, `Edit Token`, `Mark as read`, `Import`, `Erase`, `Run Approval`, or similar may change state. Do not click unless the user requested that exact operation and the relevant write-safety workflow is loaded.
- Some dashboard filters also use an `Update` button for read-only table refresh. For new screens, assume `Update` may write until verified.
- For MGS-owned dashboard views, selecting `digital-trust` + `digital-trust-2` can make tabs/reports load slowly because the tables pull a large company dataset. Do not classify a screen as `LOADING`, broken, empty, or unavailable after a short wait. Wait for the real table/API response, pagination, export button, or a clear dashboard error before concluding.
- For MGS Messenger scope, always select/validate all `digital-trust + digital-trust-2` publishers; stale scope causes wrong counts.
- Do not use historical captures as current truth. Re-query live before reporting operational status.
- Never print auth headers, cookies, bearer tokens, passwords, or full profile/session dumps.

## Refreshing This Map

When SB changes or Rodolfo asks for a deeper map:

1. Use headed Playwright via `smartbidding-dashboard-access`.
2. Start read-only: direct routes, table headers, visible buttons, API method/URL/status only.
3. Avoid state-changing buttons.
4. For heavy MGS scopes (`digital-trust` + `digital-trust-2`), use long waits and prefer endpoint-response/table-row detection over fixed sleeps; some tabs legitimately take time because they load large company datasets.
5. Save raw captures under `/root/mgs-agent/work/sb-dashboard-map/`.
6. Patch this skill with new routes, columns, endpoints, and pitfalls.
7. If the skill changes in `ops/`, follow MGS REPORT-INFRA/inventory rules.

## Common Pitfalls

1. **Confusing read-query POST with write POST.** Many reports use POST to query tables. Endpoint path and payload semantics matter.
2. **Assuming `/reports` or `/inventory` direct routes work.** `/reports` and `/inventory` direct routes returned 404 in the first crawl; use concrete submenu routes.
3. **Using this map as live data.** It is a structure map only. Current counts/statuses require a live fetch.
4. **Messenger source confusion.** `Dashboard da SB` answers SB operational state; `Dashboard do Bot/DTR` answers sent-message error codes.
5. **MGS scope drift.** A partial company/site selector changes row counts and can invalidate analysis.

## Verification Checklist

- [ ] Loaded `smartbidding-dashboard-access` before live SB access.
- [ ] Confirmed current login/user and no BotGuard failure.
- [ ] Selected the right company/domain/source scope.
- [ ] Used the route/API that matches the question.
- [ ] Re-read live data before answering operational state.
- [ ] For any write: backed up exact rows and validated readback.
