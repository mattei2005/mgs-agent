# SB restricted pending file bulk apply — 2026-07-04

## Context

Rodolfo provided a plain text export with columns:

```text
PAGE_ID   FB_PAGE_ID   UTM_CAMPAIGN   STATUS
pg_19196  104292...    pg_19196       Restricted until: 14/07/2026
```

Goal: update Smart Bidding Messenger Page rows with `RESTRICTED_UNTIL` from the file while respecting row status safety.

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
7. Initial safety gate: update operational rows only; do **not** auto-reactivate `On-hold` or `Blocked` rows from this file.
8. Group operational rows by target date and call:

```text
PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many
Payload: {"STATUS":"Broadcast","RESTRICTED_UNTIL":"YYYY-MM-DD","ids":[...]}
```

9. Re-fetch `/campaigns/Messenger` and validate every updated row by `ID`:
   - `STATUS == Broadcast`
   - `RESTRICTED_UNTIL == target date`

## Explicit On-hold second pass

If Rodolfo explicitly approves handling `On-hold` rows while keeping them On-hold, do a separate pass over only `STATUS=On-hold` rows.

Preferred payload:

```json
{"RESTRICTED_UNTIL":"YYYY-MM-DD", "ids":["<row-id>"]}
```

But SB may return HTTP 500 for some On-hold rows when only `RESTRICTED_UNTIL` is sent. Retry with explicit status preserved:

```json
{"STATUS":"On-hold", "RESTRICTED_UNTIL":"YYYY-MM-DD", "ids":["<row-id>"]}
```

This is not reactivation. Readback must confirm:

```text
STATUS == On-hold
RESTRICTED_UNTIL == target date
```

Do not use this pattern for `Blocked` rows; `Blocked` still needs separate approval and Facebook/page validation before any status change.

## Critical pitfalls learned

- The file's `PAGE_ID` has the `pg_` prefix; SB's `PAGE_ID` is numeric (`19196`). Matching on raw file `PAGE_ID` returns false missing rows.
- For full MGS Messenger Page scope, include **all** child publishers from `Digital trust` and `Digital trust 2`, not only `publisher.active == true`. Active-only returned `3,218` rows; all child publishers returned the expected `3,237` rows.
- Passing company slugs like `digital-trust` / `digital-trust-2` directly to `/campaigns/Messenger` returned `0` rows in this route. Use publisher IDs from `/company`.
- `On-hold` rows in a restricted-pending file are real matches but must not be reactivated by default. They should be skipped first, then optionally handled in a separate preserve-status pass if Rodolfo approves.

## Validated run shape

In the 2026-07-04 run:

```text
Input rows:          116
Live SB rows:        3,237
Matched rows:        116
Broadcast updated:    65
On-hold preserved:    51
Readback valid:      116
Failures:              0
```

Backup path pattern:

```text
/root/mgs-agent/logs/sb-restricted-bulk-backup-YYYYMMDD-HHMMSS.json
```

Minimal Rodolfo-facing report:

```text
Total do arquivo        116
Broadcast atualizadas    65
On-hold preservadas      51
Validadas no readback   116
Falhas                    0
```
