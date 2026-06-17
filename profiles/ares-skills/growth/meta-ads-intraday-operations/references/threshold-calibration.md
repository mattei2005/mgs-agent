# Meta Ads Intraday Threshold Calibration — MGS/Ares

Use this reference when calibrating R1-R5 intraday thresholds from a Meta Ads account month-to-date analysis.

## Minimal-call pattern

Meta API is sensitive to broad/heavy requests. Do not pull full creatives or unnecessary nested fields for threshold work.

Recommended read-only calls:

```text
Call                         Level / fields
---------------------------- ------------------------------------------------------------
account light                name, account_id, status, currency, timezone, business_name
campaigns light              id, name, status, effective_status, created/updated, budget, bid_strategy
adsets light                 id, campaign_id, status, bid_strategy, budget, optimization_goal
insights summary             level=campaign, time_range month-to-date, spend/impressions/cpm/actions
insights daily               level=campaign, time_increment=1, same minimal fields
```

Avoid `adcreatives.object_story_spec` for threshold calibration unless the question is specifically creative-level.

## Metric derivation

`subs` follows Rodolfo's priority order:

```text
1. onsite_conversion.messaging_conversation_started_7d
2. onsite_conversion.total_messaging_connection
3. complete_registration
4. offsite_complete_registration_add_meta_leads
5. lead
6. offsite_conversion.fb_pixel_lead
```

`CPS = spend / subs`; if `subs = 0`, CPS is null/not comparable.

For M0/CPM0, do not assume permanently. If Rodolfo has not confirmed the definition, label it provisional. In the June 2026 analysis the provisional mapping used was:

```text
M0   = onsite_conversion.messaging_conversation_started_7d + onsite_conversion.total_messaging_connection
CPM0 = spend / M0
```

## Calibration approach

1. Use the account timezone for the date range.
2. Analyze month-to-date summary and daily rows.
3. Segment active vs paused campaigns.
4. Compare action source distribution; the first valid `subs` action can change CPS materially.
5. Recommend thresholds in account currency first, then convert to Rodolfo's requested reference currency if needed.
6. Keep suggested thresholds as dry-run until Rodolfo approves write.

## Example initial recommendations from June 2026 OpenzedFinanzas pilot

These were not universal defaults; they were derived from one account and should be recalibrated per account.

```text
Rule | Suggested condition                                      | USD  | CAD approx
-----|-----------------------------------------------------------|------|-----------
R1   | M0 = 0 and spend > X                                     | 5.00 | 7.00
R2   | M0 > 0 and CPM0 > X                                      | 4.50 | 6.30
R3   | Subs = 0 and spend > X                                   | 4.00 | 5.60
R4   | LOWEST_COST + CPS >= X + subs >= 1 + spend >= threshold  | 2.00 | 2.80
R5   | paused + CPS < X + subs >= 2                             | 1.50 | 2.10
```

Operational read: R1 can remain close to original if M0 is confirmed; R3 should avoid cutting too early from noise; R4 may need slightly more tolerance than the seed rule when attribution/action source varies; R5 should be stricter than the pause threshold because reactivation must be conservative.
