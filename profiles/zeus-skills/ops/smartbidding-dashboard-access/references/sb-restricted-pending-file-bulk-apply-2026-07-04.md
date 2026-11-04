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

## Return an exact historical cohort to On-hold

1. Recover the prior plan and final exact-ID readback. Filter by the outcome the user named, index by SB `ID`, and assert unique-ID count and exact membership. Keep the previous operation's other outcomes as an explicit excluded set; do not rebuild the cohort from a current status filter.
2. Fetch the complete authorized publisher scope through the headed, session-leased collector. Reconcile every selected SB `ID`, large `FB_PAGE_ID` and small `PAGE_ID`, then check current statuses and the ignore registry before any write. Permit the approved source status and already-completed `On-hold` rows for resumability; stop on any other status or identity conflict instead of reducing the batch.
3. Back up an allowlisted projection of the fresh rows, including excluded rows for comparison. Preserve current restriction dates and configuration, not the values from the old migration: dates and other approved settings may have changed since that operation.
4. Use a single writer with the SB session lease. Send only `{"STATUS":"On-hold","ids":[...]}` to `PUT https://api.jbfdigital.com.br/campaigns/Messenger/update-many`. Start with one canary, preferably a row with a restriction date, and verify status plus unchanged non-status configuration before batches of at most 100 IDs. Do not resend historical dates, templates or schedules in a status reversal payload.
5. Before each batch, reread its IDs and compare identity, expected source/target status and non-status configuration with the fresh backup. After a timeout or ambiguous response, reread before retrying and send only IDs not yet at the target status; stop on unresolved drift.
6. After all batches, reread the whole scope and require every frozen target to be `On-hold`. Compare allowlisted configuration separately from mutable delivery counters, verify excluded outcomes remain unchanged, and flag outside-target differences for reconciliation. Confirm the selected cohort again in a fresh session before delivery; save this as a separate readback artifact rather than overwriting the original preflight.
7. Report the completed cohort count, exact-ID validation coverage, preserved excluded group and unchanged configuration. Keep the user-facing result short; the current total of all On-hold pages is not the denominator for a historical-cohort reversal.

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
