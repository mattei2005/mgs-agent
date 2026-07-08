# SB Messenger Page bulk registration — gid 907050576 (2026-07-07)

## Context

Rodolfo asked Zeus to resolve the Google Sheet tab `gid=907050576` by registering the pending Messenger pages in Smart Bidding (`Accounts > Messenger > Page`). The operational goal was not optimization; it was to remove pages from the backlog and put them in the Dash.

## Durable rules learned

- Treat requests like `email + FB Page ID + Page ID + Page Name` + “cadastra essa” as SB Messenger Page registration, not user authorization.
- First read the Sheet row and use every field shown there.
- Fill both modal tabs:
  - Page tab: `Messenger User`, `FB Page ID`, `Page ID`, `Page Name`, `Country`, `Vertical`, `Source`, `UTM Campaign`, `Status`, `Notes`.
  - Broadcast tab: `Message Template`, `Current Message ID`, `Message ID`, `Scheduled Times`.
- For this specific backlog tab, `Scheduled Times` must be exactly `08:00` only. Do not copy the full schedule from an existing template/page row.
- Reason: the final vertical/template use may change later; `08:00` is a neutral placeholder so the team can adjust later.
- Convert Sheet labels to SB internal enum values before POST/readback:
  - `Status READY` → `Ready`
  - `Country United States` → `US`
  - `Vertical Credit card` → `CC`
  - `Source Facebook` → `FACEBOOK`
- Validate against live full-scope `/campaigns/Messenger`, not only `GET /campaigns/Messenger/{ID}`. Direct GET can show text while the modal dropdown is effectively blank if enums are wrong.
- Required validation for this tab: row exists by `FB_PAGE_ID`, `PAGE_ID` matches, `UTM_CAMPAIGN=pg_<PAGE_ID>`, `STATUS=Ready`, `COUNTRY=US`, `VERTICAL=CC`, `SOURCE=FACEBOOK`, `BROADCAST_TIME=["08:00"]`.

## Session outcome

- Sheet useful rows: 114.
- Valid in SB after run: 112.
- Already existed and were corrected/validated: Madelyn Riley, Bruna Babdinto, Greta Baumann.
- Created in bulk: 109.
- Remaining blockers:
  - Row 30 `Ralia Thornwick` / `disparosfinanceadxcafr@gmail.com`: Messenger User not found in SB users. Do not substitute `disparosfinanceadxca@gmail.com` without Rodolfo approval.
  - Row 94 `Clara Bailey`: POST returned `409 This FB_PAGE_ID already exists`, but the row was not visible in the full `digital-trust + digital-trust-2` readback. Treat as hidden/out-of-scope duplicate until investigated.

## Implementation notes

- Use full MGS scope (`digital-trust` + `digital-trust-2`, 56 publishers) before readback.
- If a login has no existing Page row but has a Messenger User, choose the Broadcast Template by site/country/language from `/broadcast/Messenger`, avoiding `NAO USAR` and test templates.
- Keep a backup/report JSON for planned, created, skipped, and final-audit rows.
