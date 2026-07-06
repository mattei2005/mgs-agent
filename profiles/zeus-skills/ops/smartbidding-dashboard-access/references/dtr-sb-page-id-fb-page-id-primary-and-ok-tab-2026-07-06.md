# DTR/SB PAGE ID audit — FB_PAGE_ID as primary identity + OK tab handling (2026-07-06)

## Context

Rodolfo asked whether two manual-review rows were true duplicates or false positives, then asked for an OK tab in the audit sheet:

- Eva Ontiveros — `FB_PAGE_ID 696521396874142`
- Ophelia Monroe — `FB_PAGE_ID 860836117101608`
- Desired bucket label: `OK: LOGIN + PAGE_ID + FB_PAGE_ID + UTM batem`

## Operational correction

For page identity in Bot/DigitalTRChat ↔ SmartBidding audits, the large Facebook page ID (`FB_PAGE_ID`) is the most reliable differentiator.

Rodolfo clarified:

- The large `FB_PAGE_ID` does not change, even after unlink/relink.
- Inside the same segurador, humans can create pages with the same page name.
- Inside the same segurador, the small DTR/SB `PAGE_ID`/PG can also be duplicated or wrong through human error.
- Therefore, when distinguishing two pages, always anchor on `FB_PAGE_ID` first, then validate `LOGIN`, `PAGE_ID`, and `UTM_CAMPAIGN=pg_<PAGE_ID>`.

## Verified example

Live recheck showed:

### Eva Ontiveros — `FB_PAGE_ID 696521396874142`

DTR had two contexts under the same bot user:

- `disparoscliquet@gmail.com` / John Cesar — `PAGE_ID 4962`
- `disparoscliquet@gmail.com` / Cauã Santos — `PAGE_ID 5210`

SB had one row for that `FB_PAGE_ID`:

- `LOGIN disparoscliquet@gmail.com`
- `PAGE_ID 5210`
- `UTM_CAMPAIGN pg_5210`
- `STATUS On-hold`

Conclusion: real DTR duplicate by `FB_PAGE_ID`; SB had a single row, not a duplicate SB row.

### Ophelia Monroe — `FB_PAGE_ID 860836117101608`

DTR had two contexts across different bot users:

- `disparosfinanceadx@gmail.com` / Ari Irham — `PAGE_ID 10906`
- `disparoslyzmo@gmail.com` / Trương Gia Vinh — `PAGE_ID 13676`

SB had one row for that `FB_PAGE_ID`:

- `LOGIN disparoslyzmo@gmail.com`
- `PAGE_ID 10906`
- `UTM_CAMPAIGN pg_10906`
- `STATUS Broadcast`

Conclusion: real cross-user/context conflict. The important point is not “multiple SB rows”; it is that one immutable `FB_PAGE_ID` appears in multiple DTR contexts and the SB row combines fields from different contexts.

## OK tab rule

When Rodolfo asks to create a sheet tab for `OK: LOGIN + PAGE_ID + FB_PAGE_ID + UTM batem`:

1. Re-read live SB full scope if possible (`digital-trust + digital-trust-2`, all child publishers; baseline around `56` publishers / `3,237` rows as of this session).
2. Use the latest available DTR scan/snapshot only if a fresh DTR re-scan is not requested or would be disproportionate.
3. Include a row only when all checks pass:
   - SB `LOGIN`/`USER_LOGIN` equals DTR bot user.
   - SB `PAGE_ID` equals DTR small PG/PAGE_ID.
   - SB `FB_PAGE_ID` equals DTR large Facebook page ID.
   - SB `UTM_CAMPAIGN` equals `pg_<PAGE_ID>`.
4. Do not force the row count to a user-stated number if live data returns a different count. Write the verified count and note the discrepancy in the tab metadata.
5. If the count unexpectedly differs from a previously reported total, state that the live/current count differs instead of trimming or padding rows.

## Reporting pattern

Short final report:

- tab name created;
- live SB scope used;
- verified row count;
- explicit note if the requested/stated count did not match live validation.
