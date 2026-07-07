# DTR ↔ SmartBidding Phase 1 finalization + SB delete cleanup — 2026-07-07

## Context / trigger

Use this reference when Rodolfo asks to finish or re-run **Phase 1** of the Bot/DigitalTRChat ↔ SmartBidding Messenger Page audit.

Phase 1 means inventory/cadastro reconciliation only:

- What exists in DTR/Bot but not in SmartBidding.
- What exists in SmartBidding but not in DTR/Bot.
- Simple registration divergences: `LOGIN`, `PAGE_ID`, `FB_PAGE_ID`, `UTM_CAMPAIGN`.

Do **not** mix Phase 1 with Phase 2. Phase 2 is the later DTR error/status sweep: latest reports, error codes, NOTES, and restricted-until dates.

## Correct matching model

Rodolfo corrected this repeatedly. The stable rule is:

1. Match DTR pages to SB globally by `FB_PAGE_ID` first.
2. Fallback match globally by small `PAGE_ID`/PG.
3. Do **not** pre-filter SB rows by `LOGIN`/`USER_LOGIN`. That creates false `NO_SB_MATCH` rows.
4. `LOGIN`/`USER_LOGIN` is a validation field after an ID match, not the primary filter.
5. `UTM_CAMPAIGN` must equal `pg_<PAGE_ID>`.
6. `PAGE_NAME` is visual context only. Names can repeat, differ by accent/Unicode, or map to multiple profiles. Never use name to decide existence/correctness unless Rodolfo explicitly asks for a name audit.
7. DTR segurador/account is DTR navigation context only. SB `Accounts > Messenger > Page` does not have a comparable required segurador column; never classify divergence from missing/different segurador.

Recommended final Phase 1 buckets:

```text
OK                         LOGIN + PAGE_ID + FB_PAGE_ID + UTM match
DTR sem SB                 DTR page has no global SB match by FB_PAGE_ID or PAGE_ID
Login difere               IDs/UTM match but SB LOGIN differs from DTR bot user
PAGE_ID/FB difere          global ID match exists but ID pair conflicts
UTM difere                 IDs match but UTM_CAMPAIGN != pg_<PAGE_ID>
Ambíguo                    multiple global ID candidates; manual decision
SB sem DTR não Blocked     SB row has no DTR match by FB/PAGE_ID and is not Blocked/Bloqueado
```

## Final confirmation pattern

Before declaring Phase 1 closed after any SB edits/deletes:

1. Re-read DTR live from all DigitalTRChat 1Password items.
2. Re-read SB live from full `digital-trust + digital-trust-2` child publisher scope.
3. Recompute buckets using the matching model above.
4. Rebuild the Sheet from scratch with at minimum:
   - `00 Resumo Fase 1`
   - `Fase 1 - DTR sem SB`
   - `Fase 1 - SB sem DTR nao Blocked`
   - `Fase 1 - Login difere` if non-zero.
5. Validate Sheets readback row counts before reporting.

The live post-cleanup baseline from the 2026-07-07 confirmation was:

```text
DTR users OK                 88/88
DTR accounts/seguradores     226
DTR pages                    2,912
SB publishers                56
SB rows                      2,771
OK                           2,736
DTR sem SB                   150
Login difere                 26
PAGE_ID/FB difere            0
UTM difere                   0
Ambíguo                      0
SB sem DTR total             9
SB sem DTR não Blocked       9
```

Do not hard-code these numbers as current truth; use them only as sanity context.

## SB sem DTR cleanup rule

When an SB row has no DTR match by `FB_PAGE_ID` nor `PAGE_ID`:

- If `STATUS` is `Blocked`/`Bloqueado`, it is expected cleanup noise. Rodolfo considers these pages likely deleted/unlinked/blocked by Meta and missing from the bot. They can be removed from active comparison.
- If a human validates that the Facebook URL is unavailable (`This content isn't available right now`) and the row is not in DTR, set/confirm `STATUS=Blocked`; it becomes a delete candidate.
- If the Facebook URL opens and the row is not in DTR, keep it in `SB sem DTR não Blocked` for manual review.

Important Facebook availability pitfall: a non-logged browser can hit a Facebook login wall and falsely appear “available/no warning.” Do not claim URL availability unless the session actually resolves the content/availability warning, or Rodolfo manually validates the URLs.

## Deleting SB Messenger Page rows

Validated delete route for `Accounts > Messenger > Page` rows:

```text
DELETE https://api.jbfdigital.com.br/campaigns/Messenger/{SB_INTERNAL_ID}
Expected response: HTTP 200 body true
```

Use the SB internal row `ID` to execute the delete. Do **not** execute delete by `FB_PAGE_ID` or `PAGE_ID` directly.

Before every delete, confirm the live row still matches the backup candidate by:

```text
SB internal ID
LOGIN / USER_LOGIN
PAGE_ID
FB_PAGE_ID
UTM_CAMPAIGN
STATUS = Blocked
```

Safety sequence:

1. Create JSON backup of all candidate rows with the confirmation fields above.
2. Delete exactly one canary by `SB ID`.
3. Re-read full SB scope and verify:
   - total row count decreased by 1;
   - the canary `SB ID` is gone;
   - no other failure occurred.
4. Only then delete the remaining candidates.
5. If parallel/bulk deletes produce intermittent HTTP 500, retry those failed IDs sequentially. In the session, 38 parallel failures all succeeded sequentially.
6. Re-read full SB scope after the final retry and verify expected row count and `still_present_after_readback = []`.

Validated outcome from the cleanup session:

```text
Delete candidates backed up       465
Canary deleted                    1
Remaining deleted                 464
Parallel intermittent failures    38
Sequential retry success          38/38
SB rows before cleanup            3,237
SB rows after cleanup             2,772
Rodolfo manual extra delete       1 row (FB_PAGE_ID 265352986659315)
Final SB rows after manual delete 2,771
```

Again: these numbers are historical evidence, not future truth.

## Reporting to Rodolfo

Keep the final report concise and operational:

- counts first;
- links to Sheet tabs;
- readback validation;
- explicit remaining blockers.

Avoid restating long methodology unless he asks. For this workflow, his preferred answer is the final inventory state and what remains to decide.
