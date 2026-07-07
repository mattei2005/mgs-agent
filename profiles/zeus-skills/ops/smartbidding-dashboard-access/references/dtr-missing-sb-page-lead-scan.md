# DTR pages missing in Smart Bidding — lead/subscriber scan

Source: Rodolfo workflow correction, 2026-07-07.

Use when a Sheet tab lists pages that exist in Bot/DigitalTRChat but have no match in Smart Bidding. The goal is to separate pages that managers created and never used from pages that were forgotten and should be added/corrected in SB.

## Inputs

Typical Sheet fields:

- Bot/DTR user login.
- Segurador/account name.
- Page name.
- DTR `PAGE_ID` / `PG`.
- Facebook page ID.
- Status such as `SEM MATCH SB por FB_PAGE_ID/PAGE_ID`.

## Manual scan workflow

1. Log into DigitalTRChat with the Bot user.
2. Go to `Subscriber Manager` / `/subscriber_manager/bot_subscribers`.
3. If the Bot user has multiple accounts/seguradores, switch to the segurador from the Sheet.
4. In the left `Pages` list, select/search the page by name or PG.
5. Read current subscriber evidence:
   - `Bot subscriber` count;
   - `24h subscriber` count;
   - subscriber table rows (`Subscriber id`, name, quick info, synced at).
6. If already `Bot subscriber > 0` or table rows exist, classify as `HAS_LEADS` without scan.
7. If no subscribers are visible, click `Scan inbox` / `Scan`.
8. Wait for the scan to finish. Expected maximum wait is about 4 minutes.
9. If an OK/completion message appears, refresh/read the counters and table.
10. If the scan spins/hangs and no OK appears after ~4 minutes:
    - refresh the tab/page;
    - re-read counters/table;
    - if leads appeared, classify as `HAS_LEADS_AFTER_SCAN`;
    - if still empty, click scan again.
11. Repeat refresh → recheck → rescan until an OK/completion message appears, or a real blocker is identified.

## Classification

- `HAS_LEADS_ALREADY` — subscriber table/count already positive before scan.
- `HAS_LEADS_AFTER_SCAN` — subscribers appeared after scan/refresh.
- `NO_LEADS_AFTER_SCAN_OK` — scan produced OK/completion and counters/table stayed empty.
- `SCAN_UNRESOLVED` — repeated scans/refreshes did not produce OK; do **not** classify as no-lead from a hung scan alone.
- `ACCOUNT_NOT_FOUND` / `PAGE_NOT_FOUND_IN_DTR_ACCOUNT` — Sheet/account/page mismatch needs manual review.

## Automation notes

- Group by Bot user, then segurador/account, to avoid repeated logins.
- Persist state after every page so long scans can resume.
- Use DTR as source of truth for this class: Smart Bidding is missing the page by definition.
- Do not add pages to Smart Bidding blindly. Add/correct only pages with lead/subscriber evidence or explicit Rodolfo approval.
- When using endpoint automation, mirror the UI flow: call page details/subscriber table, run `import_lead_action` with inbox folder, wait/refresh/recheck.
