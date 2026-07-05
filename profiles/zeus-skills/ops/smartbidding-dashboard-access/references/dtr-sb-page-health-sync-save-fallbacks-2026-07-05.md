# DTR → SB page-health sync — save fallback lessons (2026-07-05)

## Trigger

Use when the DTR→SB page-health sync logs `update_failed` / SB HTTP 500 while saving Messenger Page fields (`NOTES`, `STATUS`, `RESTRICTED_UNTIL`), especially after a run where DTR login and report parsing succeeded.

## Key correction from Rodolfo

If a row can be saved manually in the SmartBidding Dashboard, do not label it as a page/row impossibility. Treat the failure as an automation-save mismatch and try alternate save paths until readback proves success.

## HTTP 500 root cause found

For many rows, the API failure was caused by reproducing the modal save with optional fields sent as JSON `null` (for example `PUBLISHER_ID: null`). The Dash/UI omits those fields.

Validated fallback:

1. `GET /campaigns/Messenger/{ID}`.
2. Build a full editable payload from the current row.
3. Drop optional/derived/null fields before POST, especially:
   - null values in general;
   - `PUBLISHER_ID` when null;
   - display/derived fields such as `USER_LOGIN`, `PROFILE_NAME`, `BROADCAST_TEMPLATE_NAME`, `COMPANY`, `DOMAIN`, `URL`, `LOGIN`.
4. Apply the intended field changes (`NOTES`, `STATUS`, `RESTRICTED_UNTIL`).
5. `POST /campaigns/Messenger` with JSON.
6. Accept `200` or `201` only if exact readback confirms the target fields.

This resolved the 35 prior HTTP 500 failures from the 2026-07-05 run.

## Classification rule

Do not conflate these buckets:

- **DTR login/report failure** — Bot/DigitalTRChat could not be read.
- **SB save failure** — DTR data was read, but SmartBidding rejected the write path.
- **DTR context unsafe** — top-bar segurador context signatures repeated/ambiguous; writes need dedupe/safe handling before applying.

When reporting to Rodolfo, explicitly say which bucket failed.

## Unsafe DTR context handling

When `account_context_signatures_not_unique` appears, do not blindly write every report as if the segurador label is trustworthy. A safer resolver can still process by unique SB page row:

1. Re-scan the user.
2. Match each DTR page to SB by FB page / user+page / user+name.
3. Group planned changes by SB row ID.
4. If multiple reports plan the same exact payload for the same row, write once.
5. If multiple conflicting payloads target the same row, skip and report conflict.
6. Preserve the rule: latest Completed report per page only.
7. Validate readback for every write.

This recovered many previously skipped rows without trusting ambiguous segurador labels.

## Blocked row caveat

Some `Blocked` rows can accept `STATUS=Broadcast` via `update-many` after Facebook URL validation, but still reject `NOTES` changes via both modal-style `POST /campaigns/Messenger` and `update-many`.

Validated handling:

- First check `https://facebook.com/{FB_PAGE_ID}`.
- If Facebook page is available, `STATUS=Broadcast` can be applied and readback-validated.
- If `NOTES` append still returns HTTP 500, treat the operational status fix as complete and report the residual as `NOTES append refused by SB`, not as unresolved restriction.
- Do not keep retrying the same `NOTES` payload indefinitely; after testing the modal-style/fallback paths, escalate as SB backend/UI-specific behavior.

## Reporting shape

For final ops reports, separate:

```text
Resolved writes/readbacks
Skipped no-op rows
No-match SB rows
Context conflicts
Residual SB backend save refusal
```

Avoid saying “não consegui logar” unless the failure was actually login/auth. In this case the main failures were SB save-path problems, not DTR access problems.
