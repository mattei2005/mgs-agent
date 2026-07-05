# CDP hourly query for gamezonead rewards coverage — 2026-07-05

## When to use

Use this reference when Rodolfo asks to validate SmartBidding CDP coverage by day/hour for a site such as `gamezonead`, especially after pricing/floor changes in rewards/rewarded blocks.

## Validated route

Dashboard:

```text
https://app.smartbiddingdigital.com/reports/cdp
Reports > CDP
```

Live endpoint captured from the SPA:

```text
POST https://api.jbfdigital.com.br/report/queryBuilder
```

The endpoint is a read-query POST. It returned `HTTP 201` in the validated run.

## Headed Playwright pattern

Use `smartbidding-dashboard-access` headed/Xvfb login route with storage state:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
xvfb-run -a /tmp/sb-venv/bin/python <script>.py
```

Browser context:

```python
ctx = await browser.new_context(
    storage_state="/tmp/smartbidding_state_headed.json",
    viewport={"width": 1600, "height": 1000},
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
)
```

Capture the first `/report/queryBuilder` request from the live CDP page and reuse its auth headers and metric/dimension object shapes. Do not print auth headers.

## Payload shape that worked

For site `gamezonead`:

```json
{
  "initialDate": "2026-06-15T00:00:00.000Z",
  "finalDate": "2026-07-05T23:59:59.999Z",
  "publishers": ["digital-trust_gamezonead"],
  "dimensions": [
    {"id":"DATE","label":"DATE","type":"DATE","order":0,"prefix":null,"estimatedPrefix":null},
    {"id":"HOUR","label":"HOUR","type":"INTEGER","order":1,"prefix":null,"estimatedPrefix":null}
  ],
  "metrics": [
    {"id":"REQUESTS","label":"AD_REQUESTS","type":"INTEGER","order":0,"prefix":null,"estimatedPrefix":null},
    {"id":"CDP_IMPRESSIONS","label":"AD_MATCHED","type":"INTEGER","order":1,"prefix":null,"estimatedPrefix":null},
    {"id":"COVERAGE","label":"COVERAGE","type":"PERCENT","operator":"AVERAGE","order":2,"prefix":null,"estimatedPrefix":null},
    {"id":"AVG_PRICE","label":"PRICE","type":"INTEGER","order":3,"prefix":null,"estimatedPrefix":null},
    {"id":"PAGEVIEWS","label":"PAGEVIEWS","type":"INTEGER","order":4,"prefix":null,"estimatedPrefix":null},
    {"id":"PAGEVIEWS_REC","label":"PAGEVIEWS_REC","type":"INTEGER","unavailable":true,"order":5,"prefix":null,"estimatedPrefix":null},
    {"id":"PAGEVIEWS_P1","label":"PAGEVIEWS_P1","type":"INTEGER","unavailable":true,"order":6,"prefix":null,"estimatedPrefix":null},
    {"id":"SESSIONS","label":"SESSIONS","type":"INTEGER","order":7,"prefix":null,"estimatedPrefix":null}
  ]
}
```

Notes:

- `publishers` uses `company_domain`, e.g. `digital-trust_gamezonead`.
- `DATE + HOUR` returned hourly rows; `DATE` alone returned daily rows.
- In the validated run, `DATE + HOUR` for 2026-06-15 through 2026-07-05 returned 519 rows; `DATE` returned 22 rows.
- Rows were not naturally sorted; sort by `(DATE, HOUR)` before reporting.

## Interpretation pitfall

The CDP report is monetization-side coverage for the selected site/domain and can show whether coverage recovered by hour after pricing changes. It does **not necessarily separate slot-level rewarded blocks** such as `rec`, `rec2`, or `robux-s > rec > mob-rewarded` unless an additional slot/page-type dimension is selected and validated live.

When reporting, separate claims:

```text
CDP/site-level coverage recovered/did not recover
```

from:

```text
slot-level rewarded rec/rec2 recovered/did not recover
```

Only make slot-level claims if the live query includes a validated slot/page-type dimension or the pricing screen itself shows those slots.

## Validated facts from the session

For `digital-trust_gamezonead`, day-level live CDP showed:

```text
01/07  coverage 62.32%, avg price 161
02/07  coverage 59.37%, avg price 162
03/07  coverage 40.36%, avg price 181
04/07  coverage 22.32%, avg price 159
05/07  partial coverage 35.72%, avg price 112
```

Hourly 05/07 showed recovery after price reductions, but 14h was partial/low-volume at the time:

```text
10h 28.40%, avg price 128
11h 37.25%, avg price 107
12h 41.13%, avg price 90
13h 42.91%, avg price 86
14h 76.52%, avg price 55, partial volume
```

Operational conclusion style: say “site/CDP coverage shows a recovery signal” rather than “rewards slot is fixed” unless slot-level data was verified.
