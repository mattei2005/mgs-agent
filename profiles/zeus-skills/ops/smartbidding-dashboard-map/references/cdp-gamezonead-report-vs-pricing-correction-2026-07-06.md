# Gamezonead CDP vs Pricing view correction — 2026-07-06

## Trigger

Use this note when Rodolfo asks for the Gamezonead recovery view and explicitly references:

- `https://app.smartbiddingdigital.com/reports/cdp`
- date range `1 de julho até hoje`
- Dimensions = `Data` + `Hora`
- page size / Showing = `99999`
- expected row count around `142`
- Pricing route `https://app.smartbiddingdigital.com/company/digital-trust/gamezonead/pricing`

## Correction

Do **not** answer this request with the slot-level first-rewards filter (`PAGE_TYPE=rec` + `SLOT_ID=digital-trust_gamezonead_mob_br_google_s_rewarded`) unless Rodolfo specifically asks for “primeiro rewards” / `rec > mob-rewarded` isolated.

For the report path above, the expected query is **site/publisher-level CDP**:

```text
Publisher: digital-trust_gamezonead
Dimensions: DATE + HOUR
Metrics: REQUESTS, CDP_IMPRESSIONS/AD_MATCHED, COVERAGE, AVG_PRICE, PAGEVIEWS, SESSIONS
No PAGE_TYPE/SLOT_ID dimension/filter
```

This returned exactly `142` filtered rows for `2026-07-01` through `2026-07-06` at 20:57 EDT.

## Validated live result shape

Daily weighted aggregation from the 142 CDP rows:

```text
Date        Hours  Requests  Matched  Coverage  Price
2026-07-01     24    65,735   40,966    62.32%   159.3
2026-07-02     24   111,761   66,350    59.37%   161.0
2026-07-03     24   125,768   50,756    40.36%   181.0
2026-07-04     24   120,212   26,827    22.32%   158.7
2026-07-05     24    54,929   26,282    47.85%    78.4
2026-07-06     22    12,065    6,402    53.06%    76.1
```

Recent hourly rows at that run:

```text
10h 56.08% | 11h 63.25% | 12h 55.15% | 13h 55.21% | 14h 56.77% | 15h 58.17%
16h 43.59% | 17h 39.62% | 18h 45.71% | 19h 41.93% | 20h 41.22% | 21h 46.23%
```

## Pricing view caveat

Pricing route live endpoint:

```text
GET https://api.jbfdigital.com.br/pricing/digital-trust_gamezonead?should_update_metrics=1
```

The pricing table is not the same as the CDP report. It shows current vs previous gray values by hierarchy/slot/rule. In the visible screenshot/live text, the `mob-rewarded` row columns were:

```text
requests matched impressions coverage ctr epc ecpm revenue viewable sessions rpp pagination
2,060    903     517         44%      69% ...
10,607   5,327   2,680       50%      72% ...  # gray previous line
```

Important: the visible `69% / 72%` on that row is under `ctr`, not `coverage`. The coverage on that `mob-rewarded` row is `44% / 50%` in the screenshot. Aggregated hierarchy rows can show different coverage: `robux-s` around `58% / 51%`, `rec` around `60% / 52%` in the same capture.

## Reporting rule

When replying to Rodolfo:

1. Admit the distinction if needed: previous slot-level answer was too narrow for the CDP report he intended.
2. State the exact source used:
   - `CDP report site-level, DATE+HOUR, 142 rows`, or
   - `Pricing hierarchy row`, or
   - `slot-level first rewards`.
3. Do not mix CDP site-level, Pricing aggregate rows, and slot-level first rewards as if they were one metric.
4. If Rodolfo points to `69% coverage` on the screenshot, verify the column: on the shown `mob-rewarded` row, `69%` is CTR while coverage is `44%`.
