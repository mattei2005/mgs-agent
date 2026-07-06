# CDP slot-level query for Gamezonead first rewards — 2026-07-06

## When to use

Use this reference when Rodolfo asks whether a Gamezonead rewards recovery analysis is based on:

- the whole site/CDP publisher average; or
- only the first rewards slot shown in Pricing as `robux-s > rec > mob-rewarded`.

The important correction from this session: **publisher-level CDP (`digital-trust_gamezonead`) can look healthy while the first rewards slot is still weak.** Do not use site-level CDP coverage as proof that `rec > mob-rewarded` recovered.

## Validated route

Dashboard:

```text
Reports > CDP
https://app.smartbiddingdigital.com/reports/cdp
```

Read-query endpoint:

```text
POST https://api.jbfdigital.com.br/report/queryBuilder
```

Use headed Playwright/Xvfb login from `smartbidding-dashboard-access`, capture/reuse the live `/report/queryBuilder` request headers, and never print auth headers.

## First rewards identity

The Pricing screenshot line Rodolfo highlighted as the first rewards maps to:

```text
Publisher  digital-trust_gamezonead
PAGE_TYPE  rec
SLOT_ID    digital-trust_gamezonead_mob_br_google_s_rewarded
UI path    robux-s > rec > mob-rewarded
```

Do **not** query only `SLOT_ID`: the same slot id appears under other page types such as `rec-2` and `p1`. For the first rewards, filter/aggregate by both:

```text
PAGE_TYPE = rec
SLOT_ID   = digital-trust_gamezonead_mob_br_google_s_rewarded
```

## Payload shape

Dimensions for daily first-rewards history:

```json
[
  {"id":"DATE","label":"DATE","type":"DATE","order":0,"prefix":null,"estimatedPrefix":null},
  {"id":"PAGE_TYPE","label":"PAGE_TYPE","type":"STRING","order":1,"prefix":null,"estimatedPrefix":null},
  {"id":"SLOT_ID","label":"SLOT_ID","type":"STRING","order":2,"prefix":null,"estimatedPrefix":null}
]
```

Dimensions for hourly first-rewards history:

```json
[
  {"id":"DATE","label":"DATE","type":"DATE","order":0,"prefix":null,"estimatedPrefix":null},
  {"id":"HOUR","label":"HOUR","type":"INTEGER","order":1,"prefix":null,"estimatedPrefix":null},
  {"id":"PAGE_TYPE","label":"PAGE_TYPE","type":"STRING","order":2,"prefix":null,"estimatedPrefix":null},
  {"id":"SLOT_ID","label":"SLOT_ID","type":"STRING","order":3,"prefix":null,"estimatedPrefix":null}
]
```

Metrics used:

```json
[
  {"id":"REQUESTS","label":"AD_REQUESTS","type":"INTEGER","order":0,"prefix":null,"estimatedPrefix":null},
  {"id":"CDP_IMPRESSIONS","label":"AD_MATCHED","type":"INTEGER","order":1,"prefix":null,"estimatedPrefix":null},
  {"id":"COVERAGE","label":"COVERAGE","type":"PERCENT","operator":"AVERAGE","order":2,"prefix":null,"estimatedPrefix":null},
  {"id":"AVG_PRICE","label":"PRICE","type":"INTEGER","order":3,"prefix":null,"estimatedPrefix":null},
  {"id":"PAGEVIEWS","label":"PAGEVIEWS","type":"INTEGER","order":4,"prefix":null,"estimatedPrefix":null},
  {"id":"SESSIONS","label":"SESSIONS","type":"INTEGER","order":5,"prefix":null,"estimatedPrefix":null}
]
```

Filter the returned rows client-side to the exact `PAGE_TYPE` and `SLOT_ID` above unless the dashboard exposes a validated server-side filter.

## Session facts that caused the update

On 2026-07-06, site-level CDP for `digital-trust_gamezonead` showed healthy-looking recovery around `65%` coverage, but first rewards isolated showed weaker recovery:

```text
01/07  requests 28,335  matched 11,740  coverage 41.43%  price 321
02/07  requests 48,331  matched 18,131  coverage 37.51%  price 318
03/07  requests 70,001  matched 10,208  coverage 14.58%  price 288
04/07  requests 55,434  matched    751  coverage  1.35%  price 275
05/07  requests 23,641  matched  7,210  coverage 30.50%  price 154
06/07  requests  1,587  matched    809  coverage 50.98%  price 129  partial
```

Hourly 06/07 showed the slot recovered early but weakened after price rose:

```text
08h  coverage 84.96%  price  98
09h  coverage 67.74%  price 120
10h  coverage 38.72%  price 130
11h  coverage 43.92%  price 131
12h  coverage 37.10%  price 143
13h  coverage 38.04%  price 135
```

Operational interpretation used with Rodolfo:

- Publisher/site-level CDP: useful for overall monetization health.
- First rewards slot-level CDP: required before saying the main rewarded block recovered.
- If first rewards falls below ~45% for recent hours, do not recommend further floor increases based only on site-level recovery.
- To resume increases, prefer at least 2 consecutive hours above ~55–60% on the isolated slot, not on the whole site average.

## Reporting style

When Rodolfo asks for this analysis, explicitly label the source:

```text
CDP — primeiro rewards / rec > mob-rewarded
PAGE_TYPE = rec
SLOT_ID = digital-trust_gamezonead_mob_br_google_s_rewarded
```

Then show daily rows and recent hourly rows. Do not bury the source in prose; the whole point is avoiding confusion between site average and slot-level data.
