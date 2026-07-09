# SB explicit delete list + DTR full target recheck (2026-07-09)

## Context

Rodolfo gave an explicit list of Messenger Page IDs to delete from SmartBidding and one page to verify again in DigitalTRChat/Bot:

```text
Delete SB:
FB_PAGE_ID + pg_<PAGE_ID> pairs

Verify DTR:
802843239573486 pg_5461
```

This was a targeted executive instruction, not a generic stale-row cleanup audit.

## Durable rules

### 1. Explicit delete list from Rodolfo overrides the usual `STATUS=Blocked` precondition

The generic SB cleanup skill requires `STATUS=Blocked` before deleting stale rows. That remains the default for agent-proposed bulk cleanup.

When Rodolfo explicitly says `deletar da dash da SB` and provides exact `FB_PAGE_ID + pg_<PAGE_ID>` pairs, treat that as authorization to delete those exact SB rows even if the current SB status is `On-hold` or another non-Blocked state.

Still mandatory before delete:

1. Fetch live full-scope SB Page rows (`digital-trust + digital-trust-2`, all child publishers).
2. Match by exact pair:
   - large `FB_PAGE_ID`;
   - numeric `PAGE_ID` extracted from `pg_<PAGE_ID>`.
3. Validate `UTM_CAMPAIGN == pg_<PAGE_ID>` when present.
4. Delete by SB internal `ID` only.
5. Re-fetch live SB and validate:
   - target pair absent;
   - internal ID absent;
   - row count decreased by the number actually deleted.

If the exact pair is already absent live, report it as `already absent / not live in SB`, not as a failure.

### 2. If Sheet column D says global ignore, update the global ignore list too

For tab `Fase 1 - SB sem DTR nao Blocked` (`gid=860481715`), rows with column D:

```text
IGNORAR TOTALMENTE DO SISTEMA TODO DA MGS
```

must be added/confirmed in `/root/mgs-agent/data/mgs-global-page-ignore-list.json` after handling the SB row. This prevents future DTR scans, SB registration, scheduling, restricted-page monitoring, and pending reports from resurfacing the same off-scope pages.

### 3. `verificar novamente no bot DTR` can require full 1Password DTR sweep

If Rodolfo asks to verify a specific page in DTR/Bot and the named/expected login returns no match, do not stop at that one login when the operational question is whether the page exists anywhere in DTR.

Escalate to a full DTR target search:

1. Enumerate all DigitalTRChat items in 1Password.
2. For each login, iterate all top-bar seguradores/accounts.
3. Parse every page card.
4. Match by large `FB_PAGE_ID` first, then small `PAGE_ID/PG`.
5. Report users scanned, pages scanned, and whether any match was found.

This is a targeted ID search, not a full campaign/error audit, so it does not need to open latest Completed reports unless the user asks for error/status diagnosis.

## Validated execution pattern

Ad-hoc script route used successfully:

- SB delete:
  - live SB full scope: 56 publishers;
  - rows before: 2884;
  - 8 exact pairs deleted by `DELETE /campaigns/Messenger/{SB_ID}`;
  - 1 pair already absent live (`1063903433472026 / pg_19337`);
  - rows after: 2876;
  - readback confirmed all deleted pairs and IDs absent.
- DTR target recheck:
  - first checked `disparoszuout@gmail.com`: 7 seguradores / 150 pages, no match;
  - then swept all 88 DigitalTRChat logins in 1Password: no match for `802843239573486` or `pg_5461`.

## Reporting shape

Use a compact outcome table:

```text
Ação                         Resultado
---------------------------  -------------------------------
Delete SB solicitado          N deletadas com readback OK
<page / pg> já ausente        não existia live na SB; ID/FB/PG ausentes
Rows SB                       X → Y
Global ignore                 N páginas adicionadas/confirmadas
DTR <page / pg>               encontrado/não encontrado no Bot/DTR
```

Include artifact paths only if useful; do not paste raw JSON.

## Pitfalls

- Do not block an explicit Rodolfo delete just because the row is `On-hold`; the `STATUS=Blocked` gate is for default agent-initiated cleanup, not an exact CEO delete list.
- Do not report an already-absent pair as a deletion failure.
- Do not verify only the named login if Rodolfo’s wording implies “is it in the Bot/DTR anywhere?”.
- Do not update `mgs-global-page-ignore-list.json` without infra inventory/report when that data file changes.
