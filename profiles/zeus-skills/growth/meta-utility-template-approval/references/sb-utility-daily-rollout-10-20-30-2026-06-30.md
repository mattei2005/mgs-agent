# SB Utility daily rollout 10 → 20 → 30 — 2026-06-30

## Source of rule

Rodolfo corrected the rollout strategy after Ciro explained the real approval cost:

```text
Approval cost ≈ 8 seconds per message per page
Approval run starts around midnight ET before sends begin
```

For templates with hundreds of pages, 70 active messages is not operationally viable. Example:

```text
300 pages × 10 messages × 8s = 24,000s ≈ 6h40
300 pages × 70 messages × 8s = 168,000s ≈ 46h40
```

## Correct operating model

Use a progressive active-template size, not a static 70:

```text
Day 1: 10 active approved messages
Day 2: replace rejected/error/invalid + add 10 = 20 active messages
Day 3: replace rejected/error/invalid + add 10 = 30 active messages
After 30: keep 30 active, rotate bad rows out for fresh approved rows
```

Important: do **not** block the next +10 because a large template still has blank/unknown status. Rodolfo explicitly rejected the conservative rule “do not increase if status is incomplete.” Blanks are kept temporarily and handled in the next cycle.

## Daily action rule

For each template, each daily cycle:

1. Read current SB template messages and approval counters.
2. Keep `APPROVED` and blank/unknown rows.
3. Remove/replace rows with `REJECTED`, `INVALID_FORMAT`, or `ERROR`.
4. Add fresh approved-bank rows until the next target size is reached:
   - 10 → 20
   - 20 → 30
   - 30 stays 30; only replace bad rows.
5. Preserve each template’s own link sequence/target links when installing messages.
6. Do not re-add the exact same rejected/error row from the bank in the same cycle.

Example:

```text
Current 10 rows: 7 approved, 3 rejected
Next cycle: keep 7 + replace 3 + add 10 = 20 active rows
```

If there are blank/unknown rows:

```text
Current 10 rows: 6 approved, 2 blank, 2 rejected
Next cycle: keep 8 + replace 2 + add 10 = 20 active rows
```

## Scheduling/check windows

Use pages to calculate when a template is likely ready for a check:

```text
ETA = pages × active_messages × 8 seconds
first_check = midnight ET + ETA + 30 minutes margin
```

Run/check hourly between 01:00 and 18:00 ET, but decide per-template by `next_due_et` calculated from the ETA. The 18:00 cutoff is **not** a “do not increase” rule; it is just a practical last-check window. If a template is due and still has unknown statuses, keep unknowns and still apply the +10 progression.

## Implementation artifact from the session

Zeus created an operational manager for this workflow:

```text
/root/mgs-agent/scripts/sb-utility-rollout-manager.py
/root/mgs-agent/scripts/sb-utility-rollout-cron.sh
/root/mgs-agent/data/sb-utility-rollout-tracker.json
Hermes cron: 69d8eaa11ff4 — 0 1-18 * * *
```

These paths are session artifacts, not universal requirements, but the algorithm is reusable.

## Reporting style lesson

Do not surface internal ad-hoc verification details to Rodolfo unless he asks. For this class of ops task, report the business outcome first:

```text
Feito: 59 templates reduzidos para 10; cron diário criado; próxima execução 01:00 ET.
```

Keep test/script verification in one short line or the audit path. Rodolfo explicitly complained when the response over-focused on internal verification jargon.
