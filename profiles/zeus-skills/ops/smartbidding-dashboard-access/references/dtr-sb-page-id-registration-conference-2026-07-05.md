# DTR/Bot ↔ SmartBidding PAGE ID registration conference — 2026-07-05

## Scope correction

This workflow is **not** the same as DTR→SB page-health, restricted-page monitoring, zero-delivery checks, or migration-sheet operational workflows.

Use this only when Rodolfo asks to confer/check/audit the registration relationship between DigitalTRChat/Bot pages and SmartBidding `Accounts > Messenger > Page`, especially the three fields shown in SB:

- `PAGE_ID` — must equal the small PG ID from Bot/DTR.
- `FB_PAGE_ID` — must equal the Facebook Page ID from Bot/DTR.
- `UTM_CAMPAIGN` — must equal `pg_<PAGE_ID>` using the DTR small PG ID.

For this specific conference, scope is **all DigitalTRChat credentials/items Rodolfo placed in 1Password**, regardless of whether the user/page is active in migration sheets or operational monitors. Do not filter by `Migração 22/06`, `Removidos acumulado`, restricted status, zero delivery, `On-hold`, `Blocked`, `Campaign`, `Broadcast`, active/inactive, or page-health status.

## User-facing execution style

For this class of audit/correction, Rodolfo expects normal tool/progress visibility in the transcript, but no assistant message that merely says “rodando”, “em background”, or “aguarde”. Start executing; when finished, send the consolidated result. Only send intermediate status if Rodolfo explicitly asks for status.

## Safe correction sequence

1. Build live DTR inventory by logging into every DigitalTRChat user discovered from 1Password items.
2. Enumerate all top-bar seguradores/accounts and page cards in DTR.
3. Fetch live SB `Accounts > Messenger > Page` rows using the **full child publisher scope** for both companies:
   - normalize company names like `Digital trust` → `digital-trust` and `Digital trust 2` → `digital-trust-2`;
   - include every child `publisherId` under both companies, not only `publisher.active == true`;
   - hard-stop if scope is below the current full baseline (`56` child publishers / about `3,237` Messenger Page rows as of 2026-07-06). A PAGE ID registration audit with only active publishers (e.g. `46` publishers / `3,218` rows) is invalid and must not be reported.
4. Compare by confirmed keys, preferring same-user matches:
   - same `USER_LOGIN` + `PAGE_ID`;
   - same `USER_LOGIN` + `FB_PAGE_ID`;
   - global `FB_PAGE_ID` is diagnostic only and should not be auto-corrected if the SB `USER_LOGIN` differs.
5. For existing SB rows with safe same-user divergence, update only:
   - `PAGE_ID` → DTR PG ID;
   - `FB_PAGE_ID` → DTR FB Page ID if needed;
   - `UTM_CAMPAIGN` → `pg_<DTR PAGE_ID>`.
6. Do not create missing SB rows or delete extra SB rows in this first correction pass unless Rodolfo explicitly asks.
7. Back up live SB rows before writing.
8. Canary one row and validate readback of the three fields before bulk apply.
9. Re-read live SB after bulk apply and verify planned changes are zero.

## API/write lesson

For Messenger Page field edits, `PUT /campaigns/Messenger/update-many` can return HTTP 200 but not persist changes for `PAGE_ID`/`UTM_CAMPAIGN`. Treat `update-many` success as untrusted until readback proves persistence.

The route that persisted `PAGE_ID` + `UTM_CAMPAIGN` was the same save path the UI uses for an edited page:

```text
POST /campaigns/Messenger
```

Payload should be a whitelist of page-edit fields plus the target changes, not the full joined table row. Known-good whitelist used:

```text
ID
MESSENGER_USER_ID
PAGE_ID
FB_PAGE_ID
PAGE_NAME
UTM_CAMPAIGN
STATUS
SOURCE
VERTICAL
COUNTRY
NOTES
HOLDER1
HOLDER2
ADVERTISER
DATE_START
RESTRICTED_UNTIL
BROADCAST_TEMPLATE_ID
BROADCAST_TIME
BROADCAST_CURRENT_MESSAGE_ID
BROADCAST_MESSAGE_ID
```

Drop joined/display fields such as `DOMAIN`, `COMPANY`, `LOGIN`, `USER_LOGIN`, `PROFILE_NAME`, `LEADS_TOTAL`, `LEADS`, `LEADS_PERC`, `STATUS_BADGE`, `RESTRICTION_STATUS`, `BROADCAST_TEMPLATE_NAME`, `BROADCAST_TEMPLATE_LANGUAGE`, `BROADCAST_LAST_SCHEDULE`, duplicate `ID_1/ID_2`, `NAME/NAME_1`, `PASSWORD`, and other display/join fields.

`POST /campaigns/Messenger` returned HTTP 201 and readback validated persisted values.

## Auto-skip conditions

Skip and report for manual decision instead of auto-writing when:

- DTR has duplicate `(bot_user, FB_PAGE_ID)` rows under different seguradores/PG IDs.
- The DTR `bot_user` and SB `USER_LOGIN` differ even if global `FB_PAGE_ID` matches.
- The row is only a name mismatch and the three required fields already match, unless Rodolfo explicitly asks to correct names too.

## Validated 2026-07-05 outcome

- Audit scope: 88 DigitalTRChat users from 1Password.
- Divergences: 161.
- Safe rows auto-corrected: 134.
- Rows already matching the three fields after canary/apply: 159.
- Skipped for manual decision: 2.
- Validation failure after final readback: 0.
