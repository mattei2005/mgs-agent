# Meta Ads UTM collision and exact-value audit

## Trigger

Use this procedure when Rodolfo asks whether current Meta ads contain an exact UTM value, or sends a Smart Bidding/Spidey alert about duplicated `utm_adgroup`, mismatched `utm_campaign`/`utm_adgroup`, or unexplained QA tracking.

## Read-only workflow

### 1. Freeze the real account scope

1. Classify the request as either one-account exact-value lookup or publisher/domain-wide collision audit.
2. For a publisher/domain alert, enumerate the token's live account inventory first (`/me/adaccounts` with pagination and `summary=true`), then reconcile it with the operation contract and account registry. Runtime wins when a static registry covers only onboarded writer accounts while the shared read token sees a larger fleet.
3. Filter the live inventory by the alert's domain/operation and scan every matching account. Never infer the account from a UTM wrapper such as `b01fb02` or `b01fb03`: the same wrapper can exist in unrelated operations on different domains, and an exact-value global search can therefore produce a false cross-domain collision.
4. Use the operation's configured token item and an operation-specific protected token-cache path. Validate every `act_{account_id}` identity, name, Business, currency, timezone and health before interpreting its ads.

### 2. Read and reconcile every ad

1. Read each `act_{account_id}/ads` with at least:
   - `id,name,status,effective_status`
   - `campaign{id,name,status,effective_status}`
   - `adset{id,name,status,effective_status}`
   - `creative{id,name,url_tags,object_story_spec,asset_feed_spec,effective_object_story_id}`
2. Request `summary=true`, paginate with `paging.cursors.after`, and stop only when no cursor remains.
3. Assert `ads_scanned == summary.total_count` independently for every account. A publisher-wide audit is complete only when all requested accounts reconcile.
4. Recursively inspect every string under the creative object. Tracking may live in `url_tags`, `object_story_spec`, `asset_feed_spec`, nested CTA links or encoded redirect parameters.
5. Decode with bounded repeated `urllib.parse.unquote_plus` passes, maximum five. Match parameter names and complete values case-insensitively at query boundaries; keep a raw substring check only as secondary encoding evidence.
6. Normalize the destination hostname from the same creative string and keep one record per ad containing account, campaign, ad set, ad, creative, statuses, field path, domain and all UTM values.

### 3. Classify duplicate versus mismatch correctly

1. For a domain-level duplicate alert, group by `(normalized destination domain, utm_adgroup)` and count distinct `(account_id, adset_id)` and `(account_id, campaign_id)` pairs.
2. Do not flag several ads inside the same ad set as a duplicate; sibling ads normally share one ad-group UTM. Do not merge equal UTM values across different domains when the alert itself is domain-keyed.
3. A same-domain value on more than one distinct ad set is a collision even when every ad set belongs to one campaign; campaign count alone misses duplicated sets. Report every campaign/ad-set/ad ID and effective status.
4. Classify delivery separately from structure: more than one **ACTIVE** distinct ad set is a current live collision; a duplicate confined to paused/terminal objects is historical residue; one active and one paused object is not concurrent delivery but still needs disclosure before any reactivation.
5. Validate `utm_campaign` against `utm_adgroup` using the operation's tracking contract—for example, an ad-group token derived from the campaign token plus `gNN`. Treat this link-level mismatch separately from campaign-name or ad-set-name drift.
6. Inspect each sibling ad independently. One creative can carry a mistyped URL while the other ads in the same campaign remain correct; campaign-level inspection alone misses this failure.
7. Compare object-name tokens with link tracking as a second diagnostic, not as proof of a Smart Bidding mismatch. A campaign name can be stale while `utm_campaign` and `utm_adgroup` remain internally consistent.

### 4. Broaden a zero match without overclaiming

1. When an alert value is absent from current ads, paginate `act_{account_id}/adcreatives` with the same creative fields and recursively search the complete returned catalog.
2. Also inspect current campaign and ad-set names for the literal value, but do not substitute name matches for link evidence.
3. If both ads and the creative catalog return zero exact matches, report that the value is absent from the inventory Meta returns now. Classify QA/manual/external traffic as a hypothesis, not a fact; permanently deleted objects remain outside coverage.

### 5. Reconstruct an old alert in Smart Bidding

1. Use the canonical Smart Bidding helper, resolve the exact company and publisher IDs from `/company`, then call `/report/performance_per_campaigns` with the alert's visible civil date (or the narrowest visible range), explicit currency and all matching publisher IDs.
2. Filter by exact `DATE + DOMAIN + UTM_ADGROUP`, then retain `CUSTOMER_ID`, `CAMPAIGN_ID`, campaign name, investment and traffic metrics. `CUSTOMER_ID` is the decisive account locator when the operator knows only the UTM.
3. Multiple campaign IDs prove campaign-level reuse. Multiple rows with one campaign ID identify an intra-campaign collision candidate; confirm its distinct ad sets in current Meta before calling it still live. Historical SB identifies what happened then, while current Meta determines whether it remains broken now.
4. Inspect the response schema instead of assuming the alert columns map one-to-one to this endpoint. Unmatched traffic may lack a campaign ID, and a malformed tracking value can appear on a different report field than expected.
5. Never claim to reproduce the alert's `Investiment` number unless endpoint, window, timezone, publisher set and currency are identical. State the exact date-scoped value and the unresolved aggregation gap instead of forcing reconciliation.

### 6. Verify a reported correction

1. Re-run the complete paginated scan for every account serving the alert domain; a direct GET of the edited ad alone cannot prove the old UTM is unique elsewhere.
2. Batch-GET the changed campaign, ad set and each edited ad with nested creative fields. Confirm the old tracking value is absent where expected, the new pair is internally consistent, and the effective statuses match the operator's intended delivery.
3. Recompute same-domain duplicates by distinct active ad sets and campaigns. Report the correction as complete only when the originally duplicated value has at most one active owner and no edited sibling retains the stale link.
4. Treat Smart Bidding rows already collected for the same civil day as immutable historical evidence. A same-day Spidey alert may repeat after Meta is fixed until its reporting window rolls; judge the live repair from Meta readback, not from immediate disappearance of historical SB rows.

### 7. Trace unexplained Pricing traffic without assuming it is a chat

1. Resolve the highlighted Pricing group through `GET /pricing/{publisher}` and its exact `targeting.pathname`/`utm_source`; a product label such as `finan-60m` is not a chat URL. The canonical SB helper returns `(http_status, body, token_report)`, not the body alone; unpack it and never persist token material. Report query endpoints may return HTTP 201 for successful reads.
2. Cross-check the resolved pathname with `/report/performance_per_operation` and the WordPress post/physical-route runtime before attributing it to a plugin. Compare explicit report dates; Pricing `metricsToday.date` can lag or differ from the report's civil date, so do not infer the period from the field name.
3. Reconcile paginated `/me/adaccounts` with Business owned/client accounts, scan the complete returned ad inventory and inspect every destination/tracking string. Report current active ads separately from historical/paused and permanently deleted coverage gaps.
4. Aggregate origin access logs only after filtering the parsed request pathname exactly; matching a slug anywhere in a line also captures assets whose Referer contains that slug. Show UTC/local window, HTTP status, UTM source/campaign/medium and referrer hostname; never print raw IPs, phone query parameters or complete log lines. Treat HTTP requests as requests, not unique users, sessions or monetized impressions; bot/preview requests may be included.
5. Compare live SMS Funnel sequence destinations and campaign-level activation separately. `utm_source=SMSFunnel` in origin logs may appear as source `sms` in SB. A paused sender can coexist with visits to previously distributed links; attribute confirmed tags/configuration, but label delayed clicks, previews, forwarded links and recent sends as hypotheses unless vendor events prove them. An empty sequence-analytics result does not identify the sender of every request.

### 8. Report executive-first

Lead with one verdict per alert: `continua ativo`, `corrigido agora`, or `histórico sem prova de objeto atual`. Then name the account resolved from live Meta/SB, the exact reused UTM, current campaign/ad-set/ad IDs and active-versus-paused state. Follow with per-ad typos, alert values absent from Meta, other active same-domain collisions discovered by the complete scan, coverage totals, source/window gaps and the explicit statement that the audit made no Meta or Smart Bidding write.

## Interpretation and scope

- Describe the Meta result as the **current inventory returned by the queried edges**. Deleted objects may be omitted and must not be implied as covered without a supported deleted-object route.
- A structural creative-link audit is not constrained by an Ads Manager reporting-date filter. Apply time windows only to delivery/insight or Smart Bidding report evidence.
- If some ads expose only `effective_object_story_id`, resolve their story attachments before declaring no match.
- Distinguish three findings explicitly: duplicated tracking identity, internally invalid campaign/adgroup pair, and object-name drift. They have different causes and correction scopes.
- Keep wider discoveries separate from the alert's direct answer: first identify what triggered the alert, then list additional active collisions found by the same complete scan.
- This is read-only. Replacing an active ad link usually materializes a new creative/ad and can affect delivery or social proof; do not turn the diagnosis into a write without a separately authorized correction scope.
