# DTR↔SB Phase 1 — global ignore gate + live pending recheck (2026-07-08)

## Context

During Phase 1 reconciliation, Rodolfo corrected the interpretation of the `Fase 1 - DTR sem SB` rows. A subset of 36 pages still appeared in DTR and could appear to “match” when compared elsewhere, but they were not actionable. They were old/off-niche pages inherited inside seguradores/profiles and must be removed from operational consideration.

## Durable rule

Global ignore is a **pre-audit gate**, not a post-report label.

Before any DTR↔SB coverage comparison, lead scan, restricted-page scan, page-health scan, registration payload generation, schedule/backfill, or “what is pending?” report:

1. Load `/root/mgs-agent/data/mgs-global-page-ignore-list.json`.
2. Match ignored pages by:
   - primary: large `FB_PAGE_ID`;
   - fallback: `bot_user + PAGE_ID/PG`.
3. Exclude ignored pages from all operational buckets.
4. Do not report them as `DTR sem SB`, `SB sem DTR`, “needs scan”, “needs cadastro”, “needs template”, or any pending/actionable item.

This rule wins even if the page:

- still appears in DTR/Bot;
- appears to give 100% match in a Sheet backup;
- has subscribers/leads/history;
- can be found in SB;
- has a valid Facebook URL.

Rodolfo’s explanation: these are pages that existed in profiles/seguradores when MGS acquired/started using them, outside the intended niche. They are not part of MGS operations and should never be consulted again.

## Sheet interpretation

For the working Sheet `1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI`:

- `gid=130786795` (`Fase 1 - DTR sem SB`) should show **0 actionable** if its rows are exactly the global ignored set.
- `gid=1798040517` (`Fase 1 - DTR sem SB Custom BKP`) / custom backup can preserve the 36 ignored rows as historical evidence.
- `gid=1627881114` (`Fase 1 - DTR sem SB Custom FULL BKP`) can preserve the full 150-row historical custom sheet.
- Backups are historical; do not treat them as current pending work without live recheck.

## “What is pending?” workflow after a Sheet refresh

When Rodolfo asks what is pending after Phase 1, do **not** answer from stale Sheet row counts alone. Recheck live SB first.

Required live checks:

1. Fetch live full-scope SB `Accounts > Messenger > Page` across all `digital-trust` + `digital-trust-2` child publishers.
2. Reconcile `CADASTRO NA DASH` (`gid=907050576`) by `FB_PAGE_ID` first, then validate `PAGE_ID`, `UTM`, enum fields, schedule/template as needed.
3. Reconcile `Fase 1 - SB sem DTR nao Blocked` against live SB; stale rows may have been deleted or changed.
4. Reconcile `Fase 1 - Login difere` against live SB; a sheet can be stale after a direct Dash correction.
5. Apply the global ignore list before counting `DTR sem SB` as pending.

Example result from this session after live recheck:

- 36 `DTR sem SB` rows: **0 actionable**, all global ignored.
- `CADASTRO NA DASH`: `113/114` already live in SB; only Clara Bailey missing at that moment.
- `Login difere`: Sheet still showed Graciela Scarlatto, but live SB was already corrected.
- `SB sem DTR não Blocked`: 10 rows still existed live and needed decision.

## Pitfall

Do not say “114 cadastro rows are pending” just because the Sheet has 114 rows. That tab is a payload/history tab; many or all rows may already be registered live in SB.

Do not say “36 DTR sem SB pending” if the 36 are in the global ignore list. Those are removed from MGS operational universe.

## Preferred executive report shape

Use a compact table:

```text
Bloco                         Pendente real
----------------------------  -----------------------------------------
DTR sem SB                    0 acionável
36 ignoradas                  resolvido: global ignore, fora do sistema
Cadastro na Dash              N página(s) faltando live
Login divergente              0 live / stale Sheet if already corrected
SB sem DTR não Blocked        N rows ainda existem na Dash
```

Then list only the actual remaining items with login, page name, `PAGE_ID`, and `FB_PAGE_ID`.
