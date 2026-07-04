# SB Utility rollout — Broadcast Template `PAGES` correction (2026-07-02)

## Context

Rodolfo corrected Zeus during the SB Utility rollout report: when he asks for the template list with `Pages` and message count from the **Broadcast Template** tab, the `Pages` column must come from the **Broadcast Template tab / `/broadcast/Messenger` payload field `PAGES`**, not from a join/count of rows in the **Page** tab (`/campaigns/Messenger` by `BROADCAST_TEMPLATE_NAME`).

The Page-tab count can be useful for page-schedule work and ETA estimates tied to page rows, but it is **not** the same column Rodolfo sees in the Broadcast Template tab.

## Concrete divergence observed

Live SB data after the run showed mismatches:

```text
Template                         Page-tab row count   Broadcast Template PAGES
Newsoun DE-CC-DE g005            51                   19
Spe US-JOB-ES g006               224                  4
Xyvlov DE-CC-DE g003             59                   42
Spe US-JOB-EN g006               1                    0
```

Rodolfo expected the right-hand value because he was pointing at **Accounts → Messenger → Broadcast Template**.

## Rule

For SB reports, always label the source of a `Pages` value:

- `Pages (Broadcast Template)` = `/broadcast/Messenger[].PAGES` / visible Broadcast Template tab column. Use this when Rodolfo asks for “templates com páginas e quantidade de mensagem” or points to Broadcast Template.
- `Page rows live` = `/campaigns/Messenger` rows grouped by `BROADCAST_TEMPLATE_NAME`. Use this for page schedule operations, `BROADCAST_TIME`, and page-row ETA calculations.

Never silently substitute one for the other.

## Report delivery lesson

The hourly Utility cron ran correctly at 01:01 EDT and created local output, but Rodolfo did not see the report in the thread. In future SB Utility cron/report work, state explicitly:

1. whether the cron ran;
2. where the report was delivered or saved;
3. whether it was review-only or applied;
4. current tracker state (`N templates in 10/20/30/etc.`);
5. next scheduled run.

If the user says they are lost, stop the deep technical narrative and provide an operational state block first.

## Files from the session

- Review-only cron output: `/root/.hermes/profiles/zeus/cron/output/69d8eaa11ff4_20260702_010111.txt`
- Applied rollout log: `/root/mgs-agent/logs/sb-utility-rollout-20260702-013857.json`
- Message snapshot CSV: `/root/mgs-agent/logs/sb-utility-rollout-20260702-013857-message-snapshot.csv`
- Tracker: `/root/mgs-agent/data/sb-utility-rollout-tracker.json`
