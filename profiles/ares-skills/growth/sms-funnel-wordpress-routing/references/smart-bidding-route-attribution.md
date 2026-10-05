# Smart Bidding route-level SMS attribution

Load this reference when the goal is to measure SMS cost, net revenue, profit or ROAS by manager and originating SMS stage. It complements the routing flow; it does not authorize an SMS Funnel or production URL write by itself.

## 1. Prove the live attribution contract

Inspect both systems before proposing tags:

1. Paginate `GET /api/campaigns`, de-duplicate by campaign ID and select the exact operation automations.
2. Read each intended sequence with `GET /api/sequences/{sequence_id}`.
3. Build the topology `(manager, vehicle, SMS stage) → campaign/list/sequence/current URL` and assert one intended SMS sequence per automation.
4. Parse only the destination host, path and non-secret query parameters; never print access tokens, credentials or list integration URLs.
5. Query the authenticated Smart Bidding SMS report:

```text
POST https://api.jbfdigital.com.br/report/performance_per_sms
```

6. Validate returned company, publisher, domain and date before inspecting dimensions.
7. Enumerate the actual response keys. Do not design around a UTM dimension until the live payload proves it exists.

The observed SMS report contract groups revenue by `UTM_CAMPAIGN`; `UTM_MEDIUM`, `UTM_CONTENT` and `UTM_TERM` may be absent even though those parameters exist in the landing URL. Therefore, a route/manager value carried only in an absent field cannot support the requested report.

Diagnose collisions explicitly. If SMS 1, 2 and 3 for one manager share one `utm_campaign`, the resulting revenue is not separable by stage. If later Moto stages reuse the Carro campaign token, those revenues are also merged.

## 2. Use a collision-free campaign key

Preserve these independent responsibilities:

```text
utm_source   = sms                 # channel
utm_medium   = g00X-s              # manager identity used by site/GAM
utm_campaign = manager+vehicle+stage attribution key
step         = 01|02|03            # next-list routing instruction
```

Prefer a readable extension of the current campaign namespace, for example:

```text
s01c01g001-car-d01
s01c01g001-car-d02
s01c01g001-car-d03
s01c01g001-moto-d01
s01c01g001-moto-d02
s01c01g001-moto-d03
```

Require uniqueness across every `(manager, vehicle, originating SMS stage)` combination. Under the current Disparo convention, `d01` means “click came from SMS/Disparo 1”; it must not be reinterpreted as “lead moved into List 1.” The existing `step=01` can simultaneously mean that the SMS 1 click routes the lead to the next list. If the operator approves another stage tag, preserve that literal contract throughout registration, SMS Funnel and reporting.

Do not change message text, delay, list binding, phone forwarding, destination path, source, medium or step while making an attribution-only update.

## 3. Choose edit versus clone safely

When each list already has its own stage-specific automation, change only the URL inside the existing sequence. Lists do not store the destination UTM and need no modification merely for attribution.

Do not activate a cloned automation against the same list while the original remains active; both can react to the same lead and double-send. Create new lists and automations only when exact cohort isolation is required and the authorization also covers the corresponding router/list remap, transition plan and duplicate/missed-send controls.

An attribution-only edit is not retroactive. Messages already delivered retain their old URL, so clicks from the old message can continue entering legacy campaign buckets after cutover. Record the exact cutover time, keep old buckets as `legacy/unallocated`, and never redistribute them to routes without evidence.

### Bulk URL edit through the SMS Funnel API

1. Select the target automations by exact operation + automation class + vehicle + manager + stage identity, then resolve stable campaign/sequence IDs. Do not select only by destination host, `utm_medium` or the old `utm_campaign`: CHAT automations can share those values, and later Moto stages can carry a Carro-like historical campaign token. Campaign labels may insert class qualifiers, so use an operation-owned allowlist or anchored class regex plus the expected step topology—not a fragile `startswith` prefix.
2. Assert the full expected topology before writing. For G001–G006 × Carro/Moto × Disparo 1–3, require exactly 36 unique keys and one SMS sequence per automation; treat extra same-domain CHAT sequences without `step` as out of scope and preserve their URL plus stable-field hashes for the final comparison.
3. Save a credential-free full pre-state containing campaign/list bindings and sequence objects. Derive the new key from the verified automation identity and stage, not by parsing the old campaign value.
4. Replace only the single raw `utm_campaign` value in the long URL. Preserve scheme, host, path, query order, encoding, `utm_source`, `utm_medium`, `step` and every unrelated parameter byte-for-byte.
5. Send the full UI-shaped `PUT /api/sequences/{sequence_id}` payload: `id`, `active`, `campaign_id`, `interval`, `text`, `url`, `short_url`, `interval_type_id`, `sequence_type`, `coupon`, `cross_checkout_url`, Call4U/Voxuy fields, retry fields, `send_lead_number`, `is_ac:false` and `ac_tags:[]`. A minimal URL-only payload can default omitted state.
6. Immediately `GET /api/sequences/{sequence_id}` and require the exact long URL, regenerated non-empty HTTPS short URL, unchanged campaign binding, active state, text, interval, type, retry fields and phone-forwarding state. On any HTTP error, read back before retrying; the write may have succeeded despite the failed response.
7. Stop the bounded batch on the first mismatch and roll back only IDs already changed from their saved full forms. Read back every rollback before reporting recovery.
8. Re-enumerate the complete operation after the final batch. Require the full unique target-key cardinality, one unique non-empty short URL per target, all active/phone-forwarding states intact, and every same-domain non-target sequence byte-equivalent on URL and stable fields. For page/query QA, GET every exact long URL with a cache-buster and no phone parameter; require HTTP success, exact final path and preserved query values without claiming a webhook or SMS test.

## 4. Canary and cut over

1. Back up and read back all target sequence URLs, active states, campaign/list bindings and `send_lead_number` before any write.
2. Select the low-volume manager by summing `sms_sent` across its complete Carro/Moto × stage topology for the latest closed local day. Do not use list stock, one stage, or a guessed manager.
3. Canary all three stages for that manager; include both vehicles when vehicle is part of the key.
4. Read back exact URL query values after save and require all non-target fields to remain byte-equivalent.
5. Confirm list movement and absence of duplicate sends without replaying already-proven mapped routes unnecessarily.
6. Wait for real post-cutover traffic and require the new `UTM_CAMPAIGN` rows to appear in Smart Bidding.
7. Reconcile one closed day before rolling out the remaining automations.
8. If Rodolfo explicitly authorizes rollout to all named managers after being told that the Smart Bidding evidence is still absent, that authorization overrides steps 6–7 for the **configuration rollout only**. Preserve the missing evidence as an explicit limitation; it does not authorize a claim of attribution success.
9. Roll out in bounded batches and repeat readback after every batch.

Never claim the attribution scheme works merely because every edited URL saved. You may report the configuration rollout as complete after full platform/site readback; end-to-end attribution proof still requires a post-cutover Smart Bidding row plus the matching SMS Funnel stage cost.

### Post-cutover visibility check

When asked whether the new SMS UTMs are already showing revenue, answer from one fresh report read rather than from the saved cutover audit:

1. Resolve the current civil date and `as_of` time in the operation timezone, and materialize the exact approved target-key set from the cutover contract.
2. Query `POST /report/performance_per_sms` for that local date using the exact publisher and currency. Use a timezone-safe instant such as noon UTC for same-day boundaries when the API maps dates through the publisher timezone.
3. Require the observed success status and a list response, then reject every row whose company, publisher, domain or `DATE` escapes the requested scope.
4. Partition rows by exact `UTM_CAMPAIGN` membership into `new target`, `legacy` and `malformed/unknown`; never classify by prefix alone.
5. Sum `NET_REVENUE` with decimal-safe arithmetic when revenue share is active. Report target keys found versus expected, target rows with positive revenue, target net revenue, and the same row/revenue counts for legacy separately.
6. If the new set has zero rows while legacy rows have positive revenue, state that the Smart Bidding feed is returning current SMS revenue but the new attribution has not yet been observed. Do not call this a dashboard outage, a link failure or proof of zero eventual revenue.
7. State elapsed time since the cutover when useful, label the current day provisional, and keep pre-cutover messages in legacy buckets because already-delivered short links retain their old destination.
8. Re-run the live query immediately before replying; the intraday result can change with new clicks. Use the first closed local day for the definitive attribution reconciliation.

## 5. Join cost and revenue

### Read-only runtime reuse and currency validation

- Reuse the authenticated helpers in `/root/mgs-agent/scripts/sync-sb-sms-revenue-daily.py` and `/root/mgs-agent/scripts/sync-smsfunnel-cost-daily.py` for scoped reads; never invoke their default sync/import paths during a report because those write WordPress/finance data.
- Run the Smart Bidding Playwright helper with `xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python`; the system `python3` may lack Playwright. Preserve the helper's browser arguments and authenticated context User-Agent when adapting a read, because a different browser fingerprint can prevent the report request from appearing.
- Request `currency='BRL'` explicitly when joining against BRL SMS costs. The SMS response may omit a currency field; validate the dashboard currency and, if uncertain, compare a same-date USD query instead of assuming that the default `currency=null` means USD.
- For a D01-only profitability report, join exact approved `-d01` campaign keys to stage-1 sequence costs. Keep residual D02/D03 revenue and legacy buckets separate even when their new sends are zero. The official account total can include CHAT or other automations outside the 36 Quiz routes and must not replace their scoped cost.

Use SMS Funnel sequence analytics as the cost source:

```text
GET /api/analytics/funnel-performance/{campaign_id}/sequences
cost = sms_sent × validated sms_unit_cost
```

Do not substitute list membership for sends. A lead that receives three stages creates three billable sends. Do not rely on Smart Bidding `TOTAL_MESSAGES`, `SENT` or `INVESTIMENT` unless a same-day reconciliation proves those fields are populated and equal the provider source; fields can exist in the schema while carrying zero.

Use Smart Bidding as the revenue source:

```text
revenue = NET_REVENUE
```

Prefer net revenue when the revenue-share discount is active. Join on:

```text
local date + manager + vehicle + originating SMS stage
```

Derive the latter three dimensions from the canonical `UTM_CAMPAIGN` parser. Preserve raw campaign values in lineage and fail closed on malformed or unknown tokens.

Calculate with decimal-safe cents:

```text
profit = net_revenue - sms_cost
ROAS   = net_revenue / sms_cost
ROI    = (net_revenue - sms_cost) / sms_cost
```

Guard division by zero. State timezone, currency, unit cost, revenue source and cutover/legacy limitation in every report.

## 6. Report shape

Render a compact aligned block, then manager and route totals:

```text
Gestor  Veículo  Rota  Enviados  Custo    Receita líquida  Lucro   ROAS
G001    Carro     R1    ...       R$ ...   R$ ...            R$ ...  ...
```

Reconcile these totals before publishing:

- row sends and cost equal the SMS Funnel sequence sum;
- row revenue equals the Smart Bidding `NET_REVENUE` sum for accepted campaign keys;
- manager totals equal their vehicle/stage rows;
- route totals equal their manager/vehicle rows;
- legacy and malformed buckets remain separate and are never silently allocated.
