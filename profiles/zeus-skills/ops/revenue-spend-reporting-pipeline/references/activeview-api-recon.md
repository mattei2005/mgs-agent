# ActiveView API Recon — External API + MGS Usage

Session basis: Rodolfo asked to analyze `https://app.activeview.io/en/settings/apis`, then validated a live question: “quanto o openzed rendeu ontem?” and later “openzed finanças últimos 15 dias: receita e gasto”.

## Official external API

Base URL:

```text
https://external-api.activeview.app
```

Auth header:

```text
Authorization: Bearer <API_KEY>
```

The API key is visible only after logging into the ActiveView dashboard and opening:

```text
https://app.activeview.io/en/settings/apis
```

Do not print the key in Discord. Use it internally only.

## Official endpoints observed in docs

Revenue / GAM:

```text
GET  /report/:NETWORK_CODE/:DOMAIN?start_date=:START_DATE&end_date=:END_DATE
GET  /report/:NETWORK_CODE?start_date=:START_DATE&end_date=:END_DATE&domains=:DOMAIN1,:DOMAIN2
GET  /report/kvp/:NETWORK_CODE/:DOMAIN?start_date=:START_DATE&end_date=:END_DATE&key=:KEY&timezone=:TZ
GET  /report/kvp/:NETWORK_CODE?start_date=:START_DATE&end_date=:END_DATE&key=:KEY&domains=:DOMAIN1,:DOMAIN2
GET  /report/session/kvp/:NETWORK_CODE/:DOMAIN?start_date=:START_DATE&end_date=:END_DATE&key=:KEY
GET  /report/gam/custom/:NETWORK_CODE/:DOMAIN?start_date=:START_DATE&end_date=:END_DATE&dimensions=:DIMS&metrics=:METRICS&key=:KEY&site_name=:SITE&order_id=:ORDER
GET  /report/custom/gam/:NETWORK_CODE?start_date=:START_DATE&end_date=:END_DATE&domains=:DOMAINS&dimensions=:DIMS&metrics=:METRICS&key=:KEY
```

Price rules:

```text
GET  /rules/:NETWORK_CODE/:DOMAIN
POST /upsert/:NETWORK_CODE/:DOMAIN
```

Redirect:

```text
GET  /v1/redirects
POST /v1/redirects/:REDIRECT_DOMAIN_ID
GET  /v1/redirects/paths/:REDIRECT_PATH_ID
GET  /v1/redirects/paths/:REDIRECT_PATH_ID/mappings
GET  /v1/redirects/paths/:REDIRECT_PATH_ID/mappings/logs
PUT  /v1/redirects/paths/:REDIRECT_PATH_ID/mappings
```

## Response and field notes

- Standard response wrapper for report endpoints: `{"response": [...]}`.
- `/report/:NETWORK_CODE/:DOMAIN` returns rows with fields such as `revenue`, `impressions`, `eligible_ad_requests`, `responses_served`, `clicks`, `ecpm`, `match_rate`, `request_uri`, `utm_source`, `country`, `device`, `ad_unit`.
- KVP/custom GAM endpoints may return GAM monetary fields in micros, especially `ad_exchange_line_item_level_revenue`; divide by `1_000_000` when using those fields.
- The simple `/report/:NETWORK_CODE/:DOMAIN` endpoint returned `revenue` as normal currency units in the validated live queries; do not divide that field by micros unless the endpoint/field name proves it is GAM micros.
- Status behavior: invalid/missing domain or unauthorized scope can return `401` with `{"error":"Domain not found!"}`.

## Validated MGS mappings from this session

```text
Domain                  Network code  Notes
----------------------  ------------  ------------------------------
openzed.com             23054305319   ActiveView revenue available
finanzas.openzed.com    23054305319   ActiveView revenue available
```

Ares / Meta spend mapping for OpenzedFinanzas-CC-ES:

```text
Operation               OpenzedFinanzas-CC-ES
Meta ad account         act_1356770869843984
Account name observed   OpenzedFinanzas-ES-CC-ES-03
Timezone                Europe/Madrid
Currency                USD
Token item              Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN
```

## Validated examples

### Openzed yesterday

For `openzed.com`, `2026-06-30`, `NETWORK_CODE=23054305319`, `/report/:NETWORK_CODE/:DOMAIN` returned 690 rows and total revenue `US$ 1,164.67`.

### Openzed Finanças last 15 complete days

For `finanzas.openzed.com`, `2026-06-16..2026-06-30`, `NETWORK_CODE=23054305319`, `/report/:NETWORK_CODE/:DOMAIN` returned 2,715 rows and total revenue `US$ 16,787.96`.

Meta spend for the matching Ares ad account `act_1356770869843984` over the same period returned `US$ 4,389.28` spend. Derived:

```text
Revenue   US$ 16,787.96
Spend     US$  4,389.28
Profit    US$ 12,398.68
ROAS      3.82x
Margin    73.85% of revenue
```

## Recommended workflow for ad-hoc AV revenue questions

1. Determine date range in Rodolfo’s preferred timezone context (normally Eastern for display; use full closed days unless he asks live/today).
2. Resolve domain and candidate GAM network code. If unknown, first test likely MGS codes with a small date range and stop when one returns 200 with non-empty `response`.
3. Fetch `/report/:NETWORK_CODE/:DOMAIN?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`.
4. Sum `response[].revenue` as currency units for this endpoint.
5. Optionally aggregate by `utm_source` and `request_uri` for top sources/URLs.
6. For spend, use the relevant ad platform API/source; ActiveView external docs in this session did not expose public Google/Meta spend endpoints.
7. Present only the final totals and source evidence. Do not expose API key/token.

## Recommended workflow for OpenzedFinanças revenue + spend

1. Revenue: ActiveView external API with `NETWORK_CODE=23054305319`, domain `finanzas.openzed.com`.
2. Spend: Meta Graph API through the Ares token/account configuration, account `act_1356770869843984`.
3. Query Meta insights at account level unless Rodolfo asks for campaign/page breakdown.
4. Use the same calendar date range for both sources and state if last day has zero/partial spend.
5. Compute `Lucro = Receita - Gasto`, `ROAS = Receita / Gasto`, and `Margem = Lucro / Receita`.

## Pitfalls

- Do not rely on the unauthenticated `/settings/apis` URL; it redirects to landing/login. Log in first.
- Do not paste secrets in chat. It is acceptable to read/use the API key internally from the dashboard or secure storage, but the final answer must be sanitized.
- Do not assume ActiveView public API includes spend. The dashboard’s internal API exposes more than the external docs, but the official external docs validated here are primarily GAM/revenue/price-rules/redirect.
- Do not use the dashboard internal API as the canonical public integration path unless the task explicitly requires internal/dashboard replication and you reconcile against official/export totals.
