---
name: sms-funnel-reporting
description: Report SMS Funnel sends and costs by manager.
version: 0.1.0
author: Rodolfo Mattei, Hermes Agent
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, sms-funnel, reporting, costs, managers]
    related_skills: [sms-funnel-wordpress-routing]
---

# SMS Funnel Reporting

Produce read-only SMS Funnel reports without changing lists, automations, sequences, URLs, credits, WordPress or financial records. Use the packaged script instead of reconstructing the extraction from old sessions.

## When to Use

- A user asks for SMS Funnel sends, consumed cost or `Disparos/Gastos Totais`.
- A user asks for a month, date range, current month or manager G001–G006.
- A user asks for a breakdown by manager or `utm_medium`.
- Do not use this skill to edit SMS Funnel configuration; use `sms-funnel-wordpress-routing` only when Rodolfo explicitly authorizes configuration work.

## Scope and authority

- SMS Funnel is a corporate platform, not a site/domain target. A system-wide read-only report does not require a domain gate.
- If the request explicitly names a site/domain, validate that target through the normal Ares domain scope before associating the result with it.
- Read-only reports are normal Campaign Ops/Growth work for authorized users.
- Never print credentials, tokens, message text, names, phones, short links or raw message rows.

## Source hierarchy

**Canonical override for October 2026 onward:** load `/root/mgs-agent/docs/finance-sms-dashboard-source-policy.md`. The SMS Funnel dashboard is the final quantity/consumption source, including for cost × revenue/ROI reports. Read its actual `/daily-sents?startDate=YYYY-MM-DD` surface: require eight positions and the weekday labels corresponding to eight consecutive dates starting on the requested day; position zero is that day's total. Repeat closed-day reads, require stability, and multiply by the live validated unit cost. The packaged monthly `totals` command below is a diagnostic cross-check, not final authority when it disagrees with the dashboard. Keep Messages Report and consolidated differences only as technical provenance; a residual difference does not create an operational blocker, pending audit, alert or arbitrary manager allocation. This supersedes the precedence/reconciliation criteria below only for October 2026 onward. Test a reporting adaptation against the live dashboard labels, repeated daily quantities and `sum(cost) == sum(sends) × unit_cost` before publishing.

For periods before that override:

1. `/messages-report` is the official monthly send total.
2. `/analytics/funnel-performance` independently validates total sends and live unit cost when queried with the first day of the next month as the end boundary.
3. `/messages` daily detail plus `sequence_id → campaign → G001–G006` is the exact manager allocation only while every charged row remains available.
4. Per-campaign sequence analytics is a fast historical attribution view. It may be lower than the official account total; expose the difference as `unallocated`.
5. WordPress tables and date-filtered list entries are attribution evidence, never a replacement for the vendor total.

Never distribute an unexplained difference, force it into G002 or call partial campaign analytics a closed manager total.

## Manager and UTM normalization

- Resolve manager identity from the whole token `G001`–`G006` in the campaign attached to the `sequence_id`.
- Treat `g001`, `g001-s`, `g001-d` and other suffixes as the same manager identity only for the G001–G006 roll-up.
- Do not require `-s`; do not infer that an old send used today's URL.
- A current sequence URL is current configuration, not historical send-time UTM evidence.
- If a historical row has no recoverable sequence/campaign identity, keep it unallocated even when the present URL now contains a manager UTM.

## Canonical command

Use `terminal` with the packaged script. A month is mandatory; never default silently to September or the current month.

```text
set -a; . /root/mgs-agent/.env; set +a
python3 /root/.hermes/profiles/ares/skills/growth/sms-funnel-reporting/scripts/report.py \
  --month 2026-05 --month 2026-06 --month 2026-07 --month 2026-08 \
  --mode analytics
```

Load `/root/mgs-agent/.env` before execution so the 1Password service-account context is available. If authentication fails, verify only whether the environment variable is present and its length; never print its value.

Modes:

- `totals`: official monthly sends/cost only; fastest.
- `analytics`: official total plus fast per-manager campaign analytics and explicit unallocated difference.
- `exact`: paginates retained daily messages, groups sent rows by `sequence_id`, checkpoints aggregate page counts and reports retention/unallocated gaps.

For a single manager presentation, add `--manager G005`. Extraction and reconciliation remain account-wide; the option only narrows the displayed manager block.

## Procedure

1. Parse every requested month literally. Reject a missing or malformed month instead of selecting a default.
2. Run `totals` first when the request asks only for account consumption. Completion: `messages_report_total == consolidated_total` and the live unit cost is present.
3. Run `analytics` for historical manager reports. Completion: G001–G006 plus `identified`, `unallocated` and `official` are all present for every month.
4. Run `exact` only when exact manager allocation is requested and message detail is expected to remain retained. Completion: every expected page is read or the output explicitly says `PARTIAL_RETENTION`.
5. Compare the report header at the start and end of an exact current-month read. Label the period partial when it grows during extraction.
6. Report only aggregated quantities and BRL costs. Do not attach files unless Rodolfo explicitly asks.
7. For an intraday interval, interpret the user's stated time in their timezone, convert the boundary to the SMS Funnel `sent_date` clock (`America/Sao_Paulo`), and state both clocks when they cross a month boundary. Paginate every affected `date`, count only `sent=true`, deduplicate by message `id` in memory, and persist no raw row. A literal Eastern midnight can include the first São Paulo hour of the next calendar month; exclude that hour when reconciling a closed SMS Funnel month, but show it separately if the user asked for the literal Eastern interval.

## Revenue, ROI and sessions per send

When the user also requests revenue, ROI or sessions versus sends, load the Smart Bidding route-attribution reference from the `sms-funnel-wordpress-routing` skill (via `skill_view` with that skill name and its linked attribution file) and follow its read-only authentication/currency procedure. Use this skill's `report_rows` and `Client` helpers for closed daily quantities and live unit cost; do not invoke either sync helper's import path.

- Declare the exact date window and the common source calendar. Prefer seven closed days when no rolling-hour boundary is requested; state São Paulo when that is the vendor/publisher calendar and exclude today's partial day.
- Join only the Smart Bidding company/publisher represented by the SMS Funnel account. Verify the live campaign/sequence scope before associating the vendor total with an operation. A broader Smart Bidding query can include unrelated publishers; never add their revenue or sessions to a single vendor account's ROI.
- Request `currency=BRL`; validate returned dates and company/publisher/domain, deduplicate stable source PKs, and sum `NET_REVENUE` and `SESSIONS` with tool arithmetic. Keep legacy campaign revenue in the same-operation period total, but do not assign it to new stages or claim cohort attribution.
- Reconcile daily send sums to consolidated `total_sms_sent` and `sends × sms_unit_cost` to consumed cost. Compute ROI from summed net revenue and summed cost, not the mean of daily ROIs.
- When the user defines CTR as sessions ÷ sends, label it `taxa sessões/disparos (proxy de CTR)`. Sessions are not unique people or verified unique link clicks. State that the period ratio can include visits from older SMS and is not a cohort conversion rate.
- For a closed-day report, repeat the scoped revenue read and compare the daily aggregates before presenting the result. A direct API 403 is not an empty report; use the authenticated browser-context fallback documented in the attribution reference without changing the production system.

## Performance and recovery

- Do not search past sessions before the first canonical script run.
- The exact mode stores only aggregate page counts in the Ares scratch directory with mode `0600`; no PII or message text is stored.
- Resume completed closed-day pages after a retry. Re-read the current São Paulo day because it can grow.
- Respect `Retry-After`; use bounded retries for HTTP 429/5xx and stop after five failures.
- Progress belongs in tool output, not repeated Discord messages. Publish one final report or one exact blocker.

## Pitfalls

- `end_date` semantics differ: consolidated totals require the first day of the next month; per-campaign sequence analytics uses the month's last day inclusively.
- Current URL UTMs may have been added or changed after the historical sends.
- An empty per-campaign sequence-analytics `data` array can mean no activity rows for the period, not a missing configured sequence. Do not require analytics row count to equal configured sequence count. Before reporting zero for a retained recent day, enumerate all matching campaigns regardless of current active status, read the scoped analytics twice, then paginate that day's `/messages`, count `sent=true` by their exact sequence IDs, and reconcile complete detail against `/messages-report`. Persist aggregates only. A complete reconciled detail scan with zero matching sends proves zero; empty analytics alone does not.
- Missing historical `/messages` rows are retention loss, not zero sends.
- A report can be correct at account level and still incomplete by manager.
- Delivery failure does not remove cost when the provider row is `sent=true`.

## Verification

- [ ] Requested months exactly match the user request
- [ ] Official total and consolidated total reconcile
- [ ] Unit cost comes from the live provider response
- [ ] Manager matching ignores UTM suffixes
- [ ] Current URL values are not presented as historical UTM proof
- [ ] Unallocated sends remain explicit
- [ ] Exact mode persists no PII, message text or links
- [ ] No SMS Funnel or financial writes occurred
