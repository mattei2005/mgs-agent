# SB Utility live rollout — pages, links, approvals, reports (2026-07-02)

Session lesson from Rodolfo corrections during Messenger Broadcast Template Utility rollout.

## What went wrong

- Reports initially mixed two different notions of pages:
  - `Messenger > Broadcast Template` column `PAGES` from `/broadcast/Messenger[].PAGES`.
  - `Messenger > Page` row-count grouped by `BROADCAST_TEMPLATE_NAME`.
- Rodolfo expected the **Broadcast Template tab** value when asking for template list with `páginas` and message count.
- Some rollout scripts carried the selected message's old `LINK_1` with the text, causing link order to start mid-sequence (example: Zytiva starting at `mct-003-2`).
- After edits/imports/API updates, all messages can show `gray`; this is not useful final status until `Run Approval` is triggered for templates with linked pages.

## Durable rules

1. For any SB/dashboard report requested as current/updated, query the live dashboard/API before answering. Do not answer from snapshot unless Rodolfo explicitly authorizes snapshot-only analysis.
2. For `Accounts > Messenger > Broadcast Template` reports, use live `/broadcast/Messenger` fields:
   - `NAME`
   - `PAGES`
   - `MESSAGES` count/status
3. When editing messages, treat `LINK_1` as a fixed slot by `MESSAGE_ID`, not as a property of the selected text:
   - row 1 gets source-bank link slot 1;
   - row 2 gets source-bank link slot 2;
   - preserve exact URL strings, `-2` variants, query params, repeated links.
4. Validate link sequence after every message edit by comparing live `LINK_1` by `MESSAGE_ID` against `source_bank[:N].LINK_1`.
5. Leveling rule from Rodolfo:
   - templates with `PAGES > 0`: keep/set **20 messages**;
   - templates with `PAGES = 0`: keep/set **10 messages**;
   - do not run approval for `PAGES = 0` templates.
6. Approval rule:
   - run `POST /broadcast/Messenger/{id}/approve` only for templates with `PAGES > 0`;
   - estimate completion as `PAGES × MSGS × 8s`;
   - include ETA in report.
7. Cron rule:
   - monitor templates with `PAGES = 0`;
   - if a template gains pages (`PAGES > 0`), start the normal rule: ensure 20 messages, preserve link slots, run approval, report ETA/status.

## Report format Rodolfo expects

For operational SB template reports, use concise inline tables/lists with these columns unless he asks otherwise:

```text
Nome do template | Páginas | Msgs | Motivo/status | ETA
```

When requested, split into:

1. templates with page linked (`PAGES > 0`);
2. templates without page linked (`PAGES = 0`).

Always mention the live source/scope briefly: `Broadcast Template live`, count of templates, and whether `PAGES` is Broadcast Template column.
