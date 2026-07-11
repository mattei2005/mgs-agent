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

For domain-total SMS revenue, include every returned `UTM_CAMPAIGN` per day. Do not restrict to G001–G006: historical generic campaigns such as `s01c01` and `captura-sms-quiz` carry valid revenue.

When the dashboard's **Discount revenue share** switch is enabled, the primary BRL value rendered in the `REVENUE` column is `NET_REVENUE`; the secondary/info value is gross `REVENUE`. To mirror the visible dashboard metric in WordPress, sum `NET_REVENUE`, while retaining both gross and net cents for auditability.

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
- full mutable snapshot through `2026-07-10`: 50 dates / 68 source rows
- closed-day backfill through `2026-07-09`: 49 dates / 61 source rows, gross `R$ 13.923,73`, net `R$ 12.531,37`

When splitting a broad range into adjacent chunks at `00:00:00Z`, the API can repeat the prior local day's rows at the next chunk boundary. Reconciliation on 2026-07-10 found two duplicated PKs at month boundaries. Always deduplicate by `PK_JBF_PERFORMANCE_PER_SMS` before aggregating chunked responses; never sum raw chunk arrays directly.

Treat these quantities as dated reconciliation fixtures, not immutable business totals; recent days can be revised by the source.

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

## Idempotent WordPress storage

The deployed `mgs-quiz-carro` v1.7.0 schema stores one aggregate per `(revenue_date, publisher, utm_campaign)` in `wp_mgs_quiz_sms_revenue`. This preserves campaign-level provenance while the report still presents the total domain revenue for the selected dates. Fields include:

```text
revenue_date DATE
publisher VARCHAR(190)
domain VARCHAR(190)
utm_campaign VARCHAR(190)
currency CHAR(3) = BRL
discount_revenue_share TINYINT = 1
revenue_cents BIGINT
net_revenue_cents BIGINT
investment_cents BIGINT
source_rows INT UNSIGNED
source_hash CHAR(64)
synced_at DATETIME
UNIQUE (revenue_date, publisher, utm_campaign)
```

Canonicalize and deduplicate source rows by source PK before grouping. Use `INSERT ... ON DUPLICATE KEY UPDATE` to replace each deterministic aggregate, never increment it. The same source snapshot must be a semantic no-op; revised source rows may update only their date/campaign aggregates.

The WordPress card sums `net_revenue_cents` for `digital-trust_creditoparaveiculo` / `creditoparaveiculo` over the report's selected dates. It intentionally does not claim parity with quiz, gestor, parcela, or lead-search filters because the source has no trustworthy historical per-quiz mapping.

Reconcile source vs database by aggregate count, source-row count, date count/min/max, gross/net cent sums, uniqueness, and source hashes. Do not automatically delete a database day merely because a partial API request omitted it. Treat the current day as provisional.