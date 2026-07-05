# SB restricted pending file bulk apply — 2026-07-04

## Context

Rodolfo provided a plain text export with columns:

```text
PAGE_ID   FB_PAGE_ID   UTM_CAMPAIGN   STATUS
pg_19196  104292...    pg_19196       Restricted until: 14/07/2026
```

Goal: update Smart Bidding Messenger Page rows with `STATUS=Broadcast` and `RESTRICTED_UNTIL` from the file.

## Durable workflow

1. Parse the file into `{PAGE_ID, FB_PAGE_ID, UTM_CAMPAIGN, TARGET_DATE}`.
2. Convert `DD/MM/YYYY` to ISO `YYYY-MM-DD` before writing SB.
3. Open live SB through headed/Xvfb Playwright using the saved SB storage state.
4. Fetch `/company` and then `/campaigns/Messenger` with the full MGS Messenger scope.
5. Match rows by:
   - SB `PAGE_ID` numeric form against file `PAGE_ID` without `pg_`;
   - `FB_PAGE_ID` exact;
   - `UTM_CAMPAIGN` fallback/external check (`pg_<id>`).
6. Backup all matched rows and all skipped/missing rows before write.
7. Safety gate: do **not** auto-reactivate `On-hold` or `Blocked` rows from this file. Skip them and report separately unless Rodolfo explicitly authorizes a second pass.
8. Group operational rows by target date and call:

```text
PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many
Payload: {"STATUS":"Broadcast","RESTRICTED_UNTIL":"YYYY-MM-DD","ids":[...]}
```

9. Re-fetch `/campaigns/Messenger` and validate every updated row by `ID`:
   - `STATUS == Broadcast`
   - `RESTRICTED_UNTIL == target date`

## Critical pitfalls learned

- The file's `PAGE_ID` has the `pg_` prefix; SB's `PAGE_ID` is numeric (`19196`). Matching on raw file `PAGE_ID` returns false missing rows.
- For full MGS Messenger Page scope, include **all** child publishers from `Digital trust` and `Digital trust 2`, not only `publisher.active == true`. Active-only returned `3,218` rows; all child publishers returned the expected `3,237` rows.
- Passing company slugs like `digital-trust` / `digital-trust-2` directly to `/campaigns/Messenger` returned `0` rows in this route. Use publisher IDs from `/company`.
- `On-hold` rows in a restricted-pending file are real matches but must not be reactivated by default. They should be reported as skipped.

## Validated run shape

In the 2026-07-04 run:

```text
Input rows:        116
Live SB rows:      3,237
Matched rows:      116
Applied rows:       65  (Broadcast/Campaign)
Skipped rows:       51  (all On-hold)
Readback valid:     65
Failures:            0
```

Backup path pattern:

```text
/root/mgs-agent/logs/sb-restricted-bulk-backup-YYYYMMDD-HHMMSS.json
```
