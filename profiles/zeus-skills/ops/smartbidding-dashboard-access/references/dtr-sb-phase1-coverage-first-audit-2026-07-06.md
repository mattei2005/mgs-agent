# DTR ↔ SmartBidding — Phase 1 coverage-first audit

Session lesson from 2026-07-06 after Rodolfo clarified the intended audit sequence.

## Trigger

Use when Rodolfo asks to audit/compare DigitalTRChat/Bot pages against SmartBidding Page rows and mentions phases, coverage, missing pages, or asks what exists in DTR but not in SB.

## Critical workflow correction

Do **not** mix registry coverage, SB divergences, delivery errors, notes updates, restricted pages, or SB cleanup in the first pass.

Phase 1 is strictly:

> Every page that exists in DigitalTRChat/Bot should have a corresponding row in SmartBidding `Accounts > Messenger > Page`.

The primary report is therefore:

- `DTR → SB match` = page exists in DTR and is present in SB.
- `DTR → sem match SB` = page exists in DTR but no corresponding SB row was found.

Everything else is later:

- `SB → sem DTR` = second pass after DTR missing pages are resolved.
- DTR latest-message errors, `NOTES` updates, `#2022`, `RESTRICTED_UNTIL`, and restricted-page dates = Phase 2.
- Login/UTM/PAGE_ID divergences inside already-matched SB rows are not the headline of Phase 1 unless Rodolfo explicitly asks for them.

## Matching rule for Phase 1

Use full live scope on both sides:

1. DTR: all relevant DigitalTRChat bot users/seguradores/pages for the requested audit scope.
2. SB: full `digital-trust + digital-trust-2` Messenger Page rows, all child publishers.
3. Match each DTR page against the **global SB set**, not a login-prefiltered subset:
   - first by large immutable `FB_PAGE_ID`;
   - fallback by small DTR `PAGE_ID` / PG;
   - do not use page name as a positive match key.
4. Only classify `sem match SB` when no global `FB_PAGE_ID` and no global `PAGE_ID/PG` match exists.

## Sheet/report shape

If prior broader audit tabs were created and Rodolfo asks to rerun Phase 1, delete/clear those old tabs and create one clean tab dedicated to Phase 1, for example `Fase 1 - DTR sem SB`.

Recommended columns:

```text
DTR Bot user | DTR Segurador | DTR Página | DTR PAGE_ID/PG | DTR FB_PAGE_ID | Facebook URL | DTR Email página | DTR raw | Match SB
```

Recommended summary metrics:

```text
DTR usuários lidos
DTR logins OK
Seguradores DTR lidos
Páginas DTR lidas
Publishers SB lidos
Rows SB lidas
DTR pages with SB match
DTR pages missing SB
Ambiguous but exists in SB
```

Always validate the Sheet with readback count equal to the number of missing rows before reporting.

## Communication to Rodolfo

Report the verdict directly:

- If zero missing: `Fase 1 OK: todas as páginas do DTR têm match na SB.`
- If missing exists: `Fase 1 não está 100% coberta: N páginas existem no DTR e não têm match na SB.`

Then give the Sheet link and a compact top-users/top-buckets summary. Do not start diagnosing errors or proposing notes updates in the same report unless Rodolfo asks.

## Why this matters

Earlier audits mixed several concepts at once: ID divergences, SB-only rows, DTR latest-message errors, restricted pages, and notes updates. Rodolfo clarified the operational sequence:

1. Resolve DTR pages missing from SB.
2. Then resolve SB rows missing from DTR.
3. Then run error/status Phase 2 and update SB `NOTES`/restriction dates as needed.
