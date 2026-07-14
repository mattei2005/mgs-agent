# Smart Bidding SMS Revenue → WordPress Quiz Report

Use this reference when importing or synchronizing SMS revenue from Smart Bidding into an MGS WordPress quiz report.

## Source contract

- Dashboard route: `https://app.smartbiddingdigital.com/reports/sms`
- Read endpoint: `POST https://api.jbfdigital.com.br/report/performance_per_sms`
- Target publisher for `creditoparaveiculo.com`: `digital-trust_creditoparaveiculo`
- Target API domain value: `creditoparaveiculo`
- Request fields observed: `initialDate`, `finalDate`, `publishers`, `currency`.
- Authenticate through the existing headed/Xvfb Smart Bidding session. Never persist or log authorization headers.

## Revenue semantics

The dashboard can show two amounts inside the `REVENUE` cell when `Discount revenue share` is enabled:

- primary visible amount: API `NET_REVENUE`;
- secondary/info amount: API `REVENUE` (gross).

For a WordPress block intended to mirror the dashboard’s primary visible revenue, store both fields but display `NET_REVENUE`. Record provenance explicitly:

- currency: `BRL`;
- discount revenue share: enabled;
- displayed metric: `NET_REVENUE`.

Do not silently substitute gross `REVENUE` for the primary dashboard value.

## Historical backfill pattern

1. Query only the exact publisher/domain scope.
2. Backfill closed days through yesterday; do not freeze the incomplete current day as historical truth.
3. Validate every response row remains inside the target publisher/domain.
4. Convert currency values with decimal arithmetic to integer centavos.
5. Aggregate/upsert by `revenue_date + publisher + utm_campaign`.
6. Store `revenue_cents`, `net_revenue_cents`, `investment_cents`, source row count, source hash, currency, discount flag, and sync timestamp.
7. Use a transaction and read back row count, distinct dates, first/last date, gross cents, and net cents before commit/reporting.
8. The report block sums `net_revenue_cents` by selected date range.
9. When no imported date exists in the selected range, show `Não disponível` / `Sem dados`, never assume zero revenue.

## API date-boundary pitfall

Chunked date queries can repeat the prior month-end row in the next chunk. This was observed for May 31 and June 30. Therefore:

- deduplicate API rows by `PK_JBF_PERFORMANCE_PER_SMS` before aggregation;
- reconcile a full-range query against deduplicated monthly chunks;
- never sum raw chunk responses without PK deduplication.

## Report scope boundary

Smart Bidding revenue is reliable at domain/date and UTM campaign level. It is not automatically attributable to an individual quiz variant:

- historical rows may use generic campaigns such as `s01c01`;
- several quiz variants can share one G00X SMS route;
- `LABEL` and `MSG_ID` may be blank.

Display the block as total SMS revenue for the domain and state that it respects the date range only. Do not calculate per-quiz profit unless a deterministic attribution mapping is proven.

## Deployment and validation

- Schema changes require a DB-version bump and an automatic one-time upgrade path; an activation hook alone does not run on atomic plugin replacement.
- Back up the plugin and database before the schema deployment.
- Keep the import idempotent with a unique key and upsert.
- Validate the full historical total, one known single-day filter, an empty period, plugin version/status, table engine/schema, report rendering, and public quiz routes.
- A credentials provider rate limit is a blocker, not authorization to improvise or expose secrets. Use bounded retries; after the retry budget, stop without touching production and wait for access to be restored.
- Historical backfill and the recurring 08:00 cron are separate implementation phases, but a request to execute phase 1 first does not cancel a previously requested phase 2. Keep the daily sync explicitly pending unless Rodolfo cancels or defers it.

## Daily closed-day sync pattern

- Schedule at `08:00` in the operator/VPS timezone and fetch yesterday as a closed calendar date in `America/Sao_Paulo`.
- On a transient fetch/import failure (timeout, HTTP 401/408/425/429/5xx, connection reset/refused, or temporary unavailability), make exactly one automatic retry after 5 minutes. Defer the Discord failure alert until that retry also fails. Do not retry permanent validation errors such as invalid date, escaped scope, missing source PK, or readback mismatch. Keep `flock` around the whole attempt/retry window and make retry count/delay test-overridable without changing production defaults.
- Query one timezone-safe instant (for example `12:00:00Z` at both boundaries), reject rows outside the target date/scope, require at least one source row, and never write a synthetic zero.
- Deduplicate by source PK, aggregate by UTM campaign, use centavo integers and deterministic source hashes, then upsert transactionally.
- Validate the exact date in WordPress by aggregate count, source-row count, gross/net/investment cents; rerun once to prove idempotency.
- Keep Smart Bidding authorization and RunCloud credentials outside WordPress. Use a persistent runtime outside `/tmp` when the importer must be readable by a different OS user; verify directory traversal and file ownership before the first production run.
- A WP-CLI importer executed as the site owner must be able to read both the importer and payload. Prefer a shared runtime such as `/var/tmp/<job>` with controlled permissions over a home directory that the site user cannot traverse.
- Log success locally; alert `#alerts-infra` on failure with no credential material. Add `flock`, cron inventory, stale-log monitoring, audit entry, and REPORT-INFRA.
- End-to-end validation must render the actual report for the imported date and verify revenue, cost, profit, ROI, and date fields—not only the database row.
