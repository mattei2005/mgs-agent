# SB Utility daily rollout — 10 → 20 → 30 → 40 → 50 messages

Session: 2026-07-01, Rodolfo/Zeus/Ciro operational correction.

## Core constraint

Ciro explained the approval runtime as roughly:

```text
8 seconds × active messages × Facebook pages
```

The nightly approval process starts around midnight ET and then sending begins after approvals are processed. Large templates cannot be treated like small templates: e.g. 300 pages × 10 messages × 8s ≈ 6h40; 300 pages × 70 messages × 8s ≈ 46h40.

## Rodolfo-approved rule

Do **not** run 70 active messages as the operating default. Use a staged rollout up to 50:

```text
Day/cycle 1: 10 active messages
Day/cycle 2: replace bad rows + add 10 = 20 active messages
Day/cycle 3: replace bad rows + add 10 = 30 active messages
Day/cycle 4: replace bad rows + add 10 = 40 active messages
Day/cycle 5: replace bad rows + add 10 = 50 active messages
After 50: keep 50 active and rotate bad rows out
```

Important correction from Rodolfo: do **not** block the increase because a template is large, has blanks/unknown status, or missed the 18:00 ET final check. Gray/no-status does **not** mean the message is bad; it means Meta received it but did not verify it yet. Ciro's system sends it again for verification around the next midnight. Keep gray/no-status through the next retry only; if it is still gray on the second day, replace it. Rejected/error/invalid rows are replaced immediately; +10 is still added until the target reaches 50.

## Daily logic

For each template, the daily order is **analysis/snapshot first, then addition**:

1. At 01:00 ET, analyze eligible existing messages first, before adding new rows.
   - Save the pre-change JSON backup and message-level CSV snapshot.
   - The snapshot must include status, color, reason, text, CTA, and link for every row replaced.
   - Report changed/error rows to Discord in business-readable form, not just `erro`.

2. Calculate the analysis window for eligible older batches:

```text
ETA = pages × eligible_messages × 8 seconds
analysis_start = midnight ET + ETA + 1h safety margin
```

Example: 300 pages × 10 eligible messages × 8s = 6h40; add 1h safety → start analysis around 07:40 ET.

3. During analysis, inspect only older eligible batches, not today's newly added +10:
   - Keep APPROVED rows.
   - Keep blank/unknown/gray rows through the next retry because Meta may re-check them at the next midnight.
   - Remove/replace REJECTED, INVALID_FORMAT, ERROR immediately.
   - Remove/replace gray/no-status rows if they are still gray on the second day.

4. At 50, stop increasing. The job becomes daily health/repair: keep working until all eligible messages are green, replacing bad/stale-gray rows as needed.

## Implementation pattern used by Zeus

Artifacts created in the session:

```text
/root/mgs-agent/scripts/sb-utility-rollout-manager.py
/root/mgs-agent/scripts/sb-utility-rollout-cron.sh
/root/mgs-agent/data/sb-utility-rollout-tracker.json
Hermes cron: SB Utility rollout hourly checker (0 1-18 * * *)
```

The manager:

- derives the initial 59-template set from prior best70/reduce10 audits;
- stores per-template `pages`, `active_target`, `next_due_et`, source bank backup, and history;
- uses the SB headed/Xvfb route and `/broadcast/Messenger` capture/update pattern;
- preserves current approved/blank messages;
- never re-adds the same rejected/error row from the source bank;
- writes logs under `/root/mgs-agent/logs/sb-utility-rollout-*.json`.

## Cron delivery pitfall

For script-only jobs, use `no_agent=True` and keep the prompt empty/irrelevant; otherwise Hermes may still try a provider/model pass and produce a `provider timeout` message in Discord. Script-only stdout semantics matter:

- empty stdout = silent OK;
- non-empty stdout = delivered to the origin thread;
- non-zero exit = error alert.

## SB session/login pitfall

The persistent SB storage state can expire. If `/accounts` shows `Log in to Smart Bidding`, the rollout manager should refresh login using the 1Password item `Zeus - Smartbidding Dashboard` with `--reveal`, save `/tmp/smartbidding_state_headed.json`, then continue. Never print credentials.

## Reporting preference

Rodolfo wants operational messages in business language. If he asks whether the task was done, answer directly with the outcome (templates changed, active counts, errors), not internal ad-hoc verification details unless requested.
