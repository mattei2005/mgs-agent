# BitNinja console: read-only traffic interference audit

## Scope and authentication
- Resolve the exact BitNinja Login item through the canonical MGS 1Password wrapper; never print raw item data or credentials. Try the normal browser first; use PC1 only if needed and authorized.
- The legacy `https://admin.bitninja.io/site/login` can redirect after authentication to `https://console.bitninja.io/servers`. Use browser_vault for secret entry. When 1Password is unavailable in that browser, follow the temporary same-origin relay and mandatory cleanup procedure in `onepassword-service-account-vault-operations`.
- Scope by the exact server ID and corrected target domains. A `Server: BitNinja-WafPro` header does not prove WAF Pro is enabled: check module status separately from IP Reputation/CAPTCHA.

## Collection
- Use a desktop-width viewport; a narrow viewport can hide IP, victim domain and action columns without removing their data.
- Inspect the console's actual read-only requests rather than guessing an API. Observed search: POST `https://api.bitninja.io/v2/incident/ip/search` with JSON `{from,to,offset,limit,filters:{domain:[hostname],serverId:[id]},sort:{date_created:'desc'}}`; time bounds are epoch milliseconds and the accepted page maximum is 500. POST here is a search, not a protection change.
- Keep session authentication inside the active browser and same-provider requests. Never emit authorization values, cookies, raw incident request headers, arbitrary API payloads or unrelated-domain records. Match the console transport; cross-origin fetch with `credentials:'include'` may fail while the bearer-authenticated `credentials:'omit'` path succeeds. Any temporary instrumentation must be removed with a full document navigation after collection.
- Persist each medium batch into the workspace, paginate until an empty response, require HTTP 200 with no API errors, and deduplicate/count by incident ID in code. An initial `1–50 of 51` can be a pagination sentinel, not the final incident total.
- Clamp returned timestamps again to the exact reporting window and preserve timezone uncertainty. A response may include records outside the requested sub-day boundary; never silently count them in the report period.
- Read details through the observed GET `/v2/incident/ip/one?id=<encoded-id>&dateCreated=YYYY-MM-DD`. The result `data` can contain raw headers, cookies and tracking values. Reduce in memory to an allowlist: domain/path, date, country, user-agent classification, referer origin, selected UTM source/medium and presence of attribution. Do not dump the body.

## Interpretation
- Confirm action labels in the UI: `BL_WEB_HONEYPOT_DELIST_BADURL` was displayed as Captcha presented; `WL_WEB_HONEYPOT_CAPTCHA_SUCCESS` as Captcha solved. Do not infer a nonexistent/bad article URL from the internal enum name alone.
- Distinguish event count, unique IP count, visits and users. Repeated presentations, absent success and failed CAPTCHA events cannot directly establish abandonment or lost revenue.
- Domain-filtered events do not enumerate all server-wide IP-level firewall drops. A zero domain count is not proof that nobody was blocked.
- Facebook/Instagram user agents and paid UTMs establish compatibility with acquisition traffic, not human identity or a confirmed false positive. Self-declared crawler user agents also require IP verification.
- CAPTCHA before page entry is separate from GAM creative-load time after an ad request. Correlation by country/period does not establish that CAPTCHA caused a slow creative-speed report.
- Preserve all rules and IP lists during diagnosis. Changing WAF, reputation lists or CAPTCHA requires the applicable exact confirmation; never solve suspected false positives by disabling the whole protection.
- Correlate origin records by IP, exact user-agent, path and timestamp rather than IP alone: shared/NAT egress can mix people. Treat a matched CAPTCHA-success → origin-200 sequence as a case observation, not a population-wide delay or proven loss rate.
- Do not label `Captcha __invoke - wrong parameters` on an initial article GET as a broken implementation merely from that warning. Check the subsequent challenge POST, verification result and origin access before classifying a defect.
- Verify current local daemon/process state before presenting historical cloud configuration as active protection. A stopped daemon or stale dashboard does not authorize reactivation: reconcile audit → inventory → REPORT-INFRA → Git → session history and report an unattributed concurrent stop when its owner remains unknown.
- Scope browser audit state to one document lifetime. The console's global IP Search can perform full navigation, dropping in-memory headers and collected variables. Missing state followed by unauthenticated HTTP 401 is a collector/session-state defect, not proof of denied account permissions or a vendor outage. Save batches before navigating and reacquire authentication only through an observed authorized UI request; never expose headers.
