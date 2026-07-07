# Google Sheet #2022 vs Smart Bidding restricted reconciliation — 2026-07-07

## Class of task

Use this when Rodolfo asks whether rows in a Google Sheet tab with `#2022` in an error-code column are already marked as restricted in the Smart Bidding dashboard, or asks to fill the missing SB restrictions.

## Workflow

1. Read the Google Sheet tab live, not from a stale export.
2. Filter rows where the error-code column contains `#2022`.
3. Extract the large Facebook Page ID from `https://facebook.com/{FB_PAGE_ID}` and match Smart Bidding rows by `FB_PAGE_ID` first.
4. Report counts before writing:
   - total Sheet rows;
   - rows with `#2022`;
   - SB matches;
   - already restricted in SB;
   - not restricted in SB;
   - no SB match.
5. If Rodolfo asks only to confer/list, do not correct. Generate an Excel with the mismatches.
6. If Rodolfo asks to update SB, do not invent the restriction date from the Sheet date. Open DTR/Bot for each missing row and read latest sent/Completed report messages until the `#2022` expiry date is found.
7. Parse/translate the response in the page/profile language. Known formats include EN/PT/ES, but unfamiliar language requires manual reading/translation before declaring missing date.
8. Apply `STATUS=Broadcast` + `RESTRICTED_UNTIL=YYYY-MM-DD` in SB and validate readback before saying it is done.
9. If no expiry date is found after checking all available messages, leave the row unresolved unless Rodolfo gives an explicit manual override date.

## Output expectation

For the initial check, answer with counts and attach/list the Excel path. For apply, summarize:

```text
Pendentes da Sheet          N
Datas encontradas na DTR    N
Atualizadas na SB           N
Readback OK                 N
Sem data encontrada         N
```

Then list the updated pages with `Restricted Until` and any unresolved pages with the reason.

## Pitfalls

- The Sheet `data` column is usually the report/send timestamp, not the restriction expiry date.
- `#2022` in SB `NOTES` alone does not mean the page is marked restricted; `RESTRICTED_UNTIL` must be active/future.
- Do not call a page fixed until SB readback confirms the date.
- Manual override dates must be labeled as user override, not parser inference.