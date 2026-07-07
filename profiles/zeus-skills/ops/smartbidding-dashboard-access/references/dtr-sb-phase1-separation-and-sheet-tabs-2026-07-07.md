# DTR ↔ SmartBidding Phase 1 separation and Sheet tab handling — 2026-07-07

## Trigger

Use when Rodolfo asks for the Bot/DigitalTRChat ↔ SmartBidding page registration audit, especially when the goal is to finish **Passo/Fase 1** before moving to error/status checks.

## Correct phase separation

Rodolfo clarified that the primary Fase 1 question is:

> Every page that exists in DTR/Bot should exist in SmartBidding `Accounts > Messenger > Page`.

Therefore, do not mix phases in the same conclusion:

1. **Fase 1A — DTR → SB coverage**
   - Source side: pages collected live from DigitalTRChat/Bot.
   - Target side: live SB `Accounts > Messenger > Page` full scope (`digital-trust + digital-trust-2`).
   - Match rule: `FB_PAGE_ID` global first, fallback `PAGE_ID/PG` global.
   - Output bucket: pages in DTR with no SB match by either ID.
   - This is the first bucket to resolve.

2. **Fase 1B — SB → DTR inverse**
   - Source side: live SB rows.
   - Target side: DTR/Bot pages.
   - Output bucket: SB rows not found in DTR by `FB_PAGE_ID` or `PAGE_ID/PG`.
   - Run only after/after separating DTR→SB, and label it as the inverse.

3. **Fase 2 — DTR error/status sweep**
   - Only after Fase 1 coverage is resolved.
   - Sweep DTR latest reports/errors for every relevant DTR page.
   - Then update SB `NOTES`, `RESTRICTED_UNTIL`, and/or `STATUS` as the agreed operational action.
   - Do not pre-mix error/status/restricted logic into Fase 1 coverage counts.

## Important wording

- `Sem match na SB` means: no live SB row found by global `FB_PAGE_ID` nor global `PAGE_ID/PG`.
- It does **not** mean page name missing, wrong segurador, or login mismatch.
- If the row exists in SB but `LOGIN` differs, it belongs to a divergence/association bucket, not “missing from SB”.
- `PAGE_NAME` is visual context only unless Rodolfo explicitly asks for name cleanup.
- DTR `Segurador` is for navigation/context; SB Pages does not have a comparable segurador column and it must not create a divergence by itself.

## Google Sheet handling

When Rodolfo asks to create or update a new relation/tab:

1. Preserve existing tabs unless he explicitly says to delete them.
2. If he says “não apaga a aba que tem as 150”, create the new tab beside it and verify both tabs still exist.
3. Use a clear tab name that reflects direction:
   - `Fase 1 - DTR sem SB`
   - `Fase 1 - SB sem Bot DTR`
4. Read back row count after writing.
5. Report both the new tab link and confirmation that the protected/previous tab is still present.

## Lessons from the 150 / 475 case

- The `150` bucket is DTR→SB: pages in DTR not found in SB by `FB_PAGE_ID` nor `PAGE_ID/PG`.
- The `475` bucket is the inverse SB→DTR. It should be created as a separate tab and must not overwrite or delete the 150 tab.
- User explicitly wanted the 475 relation added while preserving the 150 relation.
- Avoid saying the 150 is “new” if it is the same previously discussed `05 Nao encontrado SB` bucket.

## Verification checklist

- [ ] SB scope validated live: all child publishers under `digital-trust + digital-trust-2`.
- [ ] DTR scan source stated: all 1Password DTR users or explicitly scoped set.
- [ ] Match rule stated: `FB_PAGE_ID` global first, then `PAGE_ID/PG` global.
- [ ] Direction stated: DTR→SB or SB→DTR.
- [ ] Existing important tabs preserved unless deletion was explicitly requested.
- [ ] Sheet readback count equals expected row count.
