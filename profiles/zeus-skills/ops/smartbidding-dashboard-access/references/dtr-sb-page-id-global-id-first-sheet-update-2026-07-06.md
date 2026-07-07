# DTR ↔ SmartBidding PAGE ID audit — global ID-first matching + Sheet tabs

Session lesson from 2026-07-06 after Rodolfo corrected a false `NO_SB_MATCH` report.

## Trigger

Use for audits comparing DigitalTRChat/Bot page cards to SmartBidding `Accounts > Messenger > Page`, especially when updating Google Sheet tabs for:

- login/user divergences;
- PAGE_ID / FB_PAGE_ID divergences;
- UTM divergences;
- pages not found in SB;
- rows fully OK.

## Critical correction

Do **not** pre-filter SmartBidding rows by `USER_LOGIN`/Bot user before matching DTR pages.

That creates false `NO_SB_MATCH` rows when the page exists in SmartBidding under a different `USER_LOGIN`.

Correct order:

1. Fetch full SB Messenger Page scope across all child publishers under `digital-trust + digital-trust-2`.
2. Fetch all DTR/Bot pages for the target DTR users.
3. Match each DTR page against **global SB rows** by:
   - first: `FB_PAGE_ID` globally;
   - fallback: `PAGE_ID` globally;
   - avoid page-name matching unless explicitly labeled as manual/probable.
4. After a row is matched, validate fields:
   - `USER_LOGIN` / bot login;
   - `PAGE_ID`;
   - `FB_PAGE_ID`;
   - `UTM_CAMPAIGN == pg_<PAGE_ID>`.
5. Only classify as `NO_SB_MATCH` after no global `FB_PAGE_ID` and no global `PAGE_ID` match exists.

## Report buckets used in this class

- `OK LOGIN PAGE FB UTM` — all four validation fields match.
- `Login difere ou vazio` — global page exists in SB, but `USER_LOGIN` differs from DTR bot user.
- `FB ok PG difere` — global `FB_PAGE_ID` match exists but `PAGE_ID` differs.
- `UTM difere` — expected `UTM_CAMPAIGN=pg_<DTR_PAGE_ID>` differs.
- `Não encontrado por IDs` — no global match by `FB_PAGE_ID` nor `PAGE_ID`.

A row may be written to more than one problem tab when multiple validation fields diverge. For concise Discord reports, aggregate by issue class and state the exact matching rule used.

## Google Sheet write pattern

When Rodolfo provides destination tabs/gids and says he deleted the old content:

1. Resolve target tab names by `gid` via Sheets metadata.
2. Clear each tab range before writing.
3. Write headers + rows; chunk large value writes (e.g. 4k rows) to avoid API limits.
4. Apply readable formatting: frozen header, filter, bold colored header, autoresize.
5. Read back `A:A` and verify row count equals expected row count before reporting success.

Final report should include:

- DTR users found in 1Password;
- DTR logins OK;
- DTR seguradores/accounts read;
- DTR pages read;
- SB publishers read;
- live SB rows;
- SB rows belonging to audited DTR users (metric only, not match filter);
- each destination Sheet URL and readback count.

## Pitfall example

Bad: `sb = [row for row in all_sb_rows if row.USER_LOGIN in dtr_users]` then call missing rows `NO_SB_MATCH`.

Good: match against `all_sb_rows` by global `FB_PAGE_ID`/`PAGE_ID`; if matched but `USER_LOGIN` differs, classify as login divergence.
