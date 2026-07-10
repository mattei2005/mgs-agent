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

