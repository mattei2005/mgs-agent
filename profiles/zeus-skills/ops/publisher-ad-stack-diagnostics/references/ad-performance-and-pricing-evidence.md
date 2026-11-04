# Ad performance and pricing evidence

## 1. Freeze the comparison

Record exact hosts, affected article/next-page URLs, traffic parameters, period, timezone and filters. Read chart labels literally: a country-share label is not automatically a country-only cohort. Do not substitute the apex site for the supplied jobs/subdomain target.

When drafting a request for the provider, deliver ready-to-forward text asking for original CSV/Excel data, not additional screenshots. Ask for definitions and sample volumes alongside percentages; those determine whether comparisons and calculations are meaningful. Mark optional fields as optional rather than blocking all analysis on unavailable dimensions.

## 2. Separate the timing stages

Measure server response, visible page content, ad-script initialization, ad request, creative response/download and visible rendering separately on the real mobile flow. Compare the same routes and conditions across sites, and capture JavaScript/network failures. A healthy homepage is only an availability check.

Request performance data by site, country and ad unit/format, including tag/creative timing buckets and sample volume. Request device, connection/operator and creative bytes/identity when available. Compare countries within equivalent formats and device cohorts; aggregate differences can reflect traffic or creative mix rather than a site defect.

Treat bandwidth throttling as a sensitivity test, not a regional measurement: it does not reproduce the country's routing, CDN location, peering or device population. Use an authorized regional probe or real-user data before attributing a geographic slowdown to users' connections. Keep that cause explicitly unproven when these data are absent.

## 3. Reconcile pricing metrics

Obtain the provider's definition of PMR, numerator, denominator, aggregation weights and meaning of each volume column. Do not expand the acronym or label reported counts as rows, requests or impressions without confirmation.

Export rule-applied and `No pricing rule applied` entries together, broken down by URL, country, ad unit, rule and volume. Compare with rule configuration and eligibility criteria effective during the same period.

Recompute aggregates using the documented volume weights, not an unweighted mean of displayed rows. If no-rule entries contribute zero, separate rule coverage from performance conditional on an applied rule. An arithmetically consistent aggregate does not establish that the denominator matches the business definition.

Check whether uncovered entries were intentionally excluded or should have matched a rule. All covered entries at 100% does not prove full coverage, correct commercial prices or optimal revenue. Conversely, an aggregate below 100% does not by itself prove existing rules failed.

## 4. Close with the evidence boundary

Report confirmed findings, plausible causes, missing evidence and one next validation. If protection blocking is suspected, establish the actual DNS/proxy/WAF path using `cloudflare-operations` before requesting access or changing protection. Keep public tests, server/WAF events and provider reports as separate evidence sources until their timestamps and target dimensions reconcile.
