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
