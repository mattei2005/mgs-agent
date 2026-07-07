# SmartBidding Messenger Page delete cleanup — 2026-07-07

## Trigger

Use when Rodolfo asks to remove/delete stale rows from SmartBidding `Accounts > Messenger > Page`, especially rows that are in SB but no longer exist in DigitalTRChat/Bot.

## Operational context from validated session

During Step 1 DTR ↔ SB cleanup, the `SB sem Bot/DTR` bucket had 475 rows. Rodolfo clarified:

- Rows already `Blocked` and absent from Bot/DTR are expected stale inventory: Meta/Facebook may have blocked/deleted the page or the gestor removed it, so the page can disappear from the segurador/Bot while remaining in SB.
- Rows that were `On-hold` but manually confirmed as Facebook-unavailable should first be set to `Blocked`, then can be deleted from SB as stale.
- Rows that still open publicly must remain pending; do not delete them automatically.

Validated breakdown in that session:

```text
SB sem Bot/DTR total                        475
Already Blocked, absent from Bot/DTR        386  -> delete candidates
On-hold, manually confirmed unavailable      79  -> set Blocked, then delete candidates
Open/available pages                         10  -> keep pending
Unmapped open URL                             1  -> keep pending until mapped
```

## Safe delete rule

Do not delete by `FB_PAGE_ID` alone. Execute the delete by the SB internal row `ID`, but only after preflight validates the candidate row still matches all expected fields:

```text
SB internal ID     exact row to delete
LOGIN/USER_LOGIN   expected bot login from backup/sheet
PAGE_ID            expected small PG
FB_PAGE_ID          expected large Facebook Page ID
UTM_CAMPAIGN        expected pg_<PAGE_ID>
STATUS              must be Blocked
Bot/DTR match       absent by both FB_PAGE_ID and PAGE_ID
```

If any field changed or status is not `Blocked`, skip the row and report it for manual review.

## Validated endpoint

The UI trash icon on `Accounts > Messenger > Page` maps to deleting the SB Messenger campaign/page row by internal ID:

```text
DELETE https://api.jbfdigital.com.br/campaigns/Messenger/{SB_ID}
Expected success body: true
```

Validated canary:

```text
Page          Violet Payne
SB ID         684e8cd4-7e02-9a6f-5a50-b5f4bacfcbb1
LOGIN         disparosspe@gmail.com
PAGE_ID       4888
FB_PAGE_ID    650473824820001
UTM           pg_4888
Status        Blocked
DELETE        HTTP 200 / true
Readback      rows 3237 -> 3236; row absent
```

## Required workflow

1. Fetch live SB full scope: all child publishers under `digital-trust + digital-trust-2`.
2. Build/delete candidate set from a trusted audit bucket, not from ad hoc visible UI rows.
3. Backup the full candidate rows before any delete.
4. Validate every candidate by internal ID plus `LOGIN + PAGE_ID + FB_PAGE_ID + UTM + STATUS=Blocked`.
5. Delete one canary first.
6. Re-fetch live SB and confirm:
   - row count decreased by 1;
   - canary internal ID absent;
   - page IDs absent where expected.
7. For bulk delete, prefer small/sequential or limited-concurrency batches.
8. If the API returns transient HTTP 500 on some rows, do **not** assume failure is permanent. Re-fetch and retry failed rows sequentially; in the validated session, 38 initial HTTP 500 rows all succeeded on one-by-one retry.
9. Final readback must prove:
   - `rows_after == rows_before - deleted_count` for the current run;
   - all deleted IDs are absent;
   - failed/still-present lists are empty.
10. Update the operational Sheet after cleanup so stale deleted rows are not still shown as pending.

## Reporting shape

For Rodolfo, report the outcome compactly:

```text
Delete SB — stale Messenger Page rows

Backup criado                 N rows
Canário deletado              1
Restante deletado             N
Total deletado                N
Rows SB antes                 X
Rows SB final                 Y
Falhas finais                 0
Readback                      OK
```

Include local backup/result paths but do not paste raw JSON.

## Pitfalls

- Do not conflate `SB sem Bot/DTR` with `DTR sem SB`; they are opposite directions and should be kept in separate Sheet tabs.
- Do not delete open/available pages just because they are absent from Bot/DTR; Rodolfo may need to inspect them.
- Do not rely on Facebook availability checks from an unauthenticated browser session; login walls can create false “available” results. In the validated session, Rodolfo’s manual browser check was treated as source for the unavailable/open split.
- Do not use `PAGE_NAME` as a delete key. Names repeat and can differ by Unicode/accent.
- Do not report success after HTTP 200 alone; re-read live `/campaigns/Messenger` and verify row absence.
