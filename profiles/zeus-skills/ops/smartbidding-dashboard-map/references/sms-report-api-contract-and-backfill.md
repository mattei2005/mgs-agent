# Smart Bidding SMS report — API contract and read-only backfill discovery

Use this reference when inspecting or backfilling SMS revenue from `Reports > SMS` without modifying the dashboard.

## Endpoint and authentication

- Dashboard route: `https://app.smartbiddingdigital.com/reports/sms`
- Read endpoint: `POST https://api.jbfdigital.com.br/report/performance_per_sms`
- Requires the Auth0 `Authorization` header used by the authenticated SPA. Never print or persist the token in reports.
- Successful calls currently return HTTP `201` with a bare JSON array.

Observed payload:

```json
{
  "initialDate": "2026-07-10T23:51:38.214Z",
  "finalDate": "2026-07-10T23:51:38.214Z",
  "publishers": ["digital-trust_creditoparaveiculo"],
  "currency": null
}
```

## creditoparaveiculo scope

Request with the exact publisher ID:

```text
digital-trust_creditoparaveiculo
```

Defensively reject returned rows outside:

```text
COMPANY   = digital-trust
PUBLISHER = digital-trust_creditoparaveiculo
DOMAIN    = creditoparaveiculo
```

`DOMAIN` omits `.com`, and `domain` is not an observed request field. A shortened publisher value such as `creditoparaveiculo` is not equivalent and may return HTTP 403.

For domain-total SMS revenue, sum `REVENUE` across every returned `UTM_CAMPAIGN` per day. Do not restrict to G001–G006: historical generic campaigns such as `s01c01` and `captura-sms-quiz` carry valid revenue.

## Response contract

Important fields:

- Identity: `PK_JBF_PERFORMANCE_PER_SMS`, `DATE`, `COMPANY`, `PUBLISHER`, `DOMAIN`, `UTM_CAMPAIGN`
- SMS: `TOTAL_MESSAGES`, `SENT`, `RECEIVED`, `DELIVERED`, `UNDELIVERED`, `QUEUED`, `FAILED`
- Traffic/ad ops: `SESSIONS`, `PAGEVIEWS`, `CDP_REQUESTS`, `CDP_IMPRESSIONS`, GAM/KTR fields
- Financial: `REVENUE`, `NET_REVENUE`, `INVESTIMENT`, `AVG_PRICE`

Type caveats:

- `DATE` is `YYYY-MM-DD`.
- Source PK is a string and may be negative; if raw rows are persisted, use `VARCHAR`, not unsigned integer.
- Several counters are numeric strings, while sessions/GAM values are integers.
- Revenue fields are JSON numbers; convert with decimal-safe cent arithmetic.
- KTR values may be null.

## Dates and timezone

The date boundary behaves as America/Sao_Paulo / UTC−3. For a requested local date, `00:00:00Z` can resolve to the previous local day. A single-day probe at `03:00:00Z` or later returns the intended date. Prefer a safe instant such as `12:00:00Z` for both ends of a one-day request, or build explicit timezone-aware boundaries.

Validated historical floor for this publisher on 2026-07-10:

- earliest `DATE`: `2026-05-22`
- no rows before `2026-05-22`
- 50 distinct contiguous dates through `2026-07-10`
- 68 unique source rows in that snapshot

Treat these quantities as a dated reconciliation fixture, not an immutable business total; recent days can be revised by the source.

## Pagination

No server-side pagination fields were observed in request or response: no page, limit, offset, cursor, total, or next token. A full historical query returned all 68 publisher rows in one bare array. Dashboard table paging is therefore client-side for the observed contract. Revalidate if the API later introduces pagination metadata or truncation.

## Read-only discovery procedure

1. Open the authenticated SMS report with headed Playwright/Xvfb if BotGuard requires it.
2. Capture the SPA request to discover the current payload and authorization header; redact the header in all output.
3. Reuse the header only in-memory for read requests.
4. Query a broad range for the one exact publisher.
5. Validate response type, scope fields, PK uniqueness, min/max dates, distinct dates, row count, and gross/net sums.
6. Probe the day before the minimum and the minimum day at a timezone-safe instant.
7. Do not write dashboard state, WordPress, database, or local artifacts during a read-only request.

## Idempotent daily aggregate

For WordPress reporting, prefer one row per `(publisher, domain, revenue_date)` in a dedicated revenue table, not the lead table. Recommended fields:

```text
revenue_date DATE
publisher VARCHAR(190)
domain VARCHAR(190)
revenue_cents BIGINT UNSIGNED
net_revenue_cents BIGINT UNSIGNED
source_row_count INT UNSIGNED
source_hash CHAR(64)
created_at DATETIME
synced_at DATETIME
UNIQUE (publisher, domain, revenue_date)
```

Canonicalize source rows sorted by source PK and hash the fields that determine the aggregate. Use `INSERT ... ON DUPLICATE KEY UPDATE` to replace that day's aggregate, never increment it. The same snapshot must be a semantic no-op; a revised source day may update only its deterministic daily row.

Reconcile source vs database by date count, min/max date, sum of source-row counts, gross/net cent sums, uniqueness, and per-day source hash. Do not automatically delete a database day merely because a partial API request omitted it. Treat the current day as provisional.