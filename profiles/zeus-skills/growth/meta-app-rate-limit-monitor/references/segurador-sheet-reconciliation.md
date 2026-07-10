# Segurador Sheet Reconciliation — B001–B010

Session learning from Rodolfo's Meta app monitor setup.

## Source sheet

Google Sheet tab:

```text
Spreadsheet: 1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY
Tab/GID:     Migracao 22/06 / 562940072
CSV export:  https://docs.google.com/spreadsheets/d/1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY/export?format=csv&gid=562940072
```

The export was public/readable and returned `200 OK` during validation.

## Column rule

Rodolfo corrected the column mapping:

```text
Column J / header "NO APP"    = app assignment B001–B010. Use this for reconciliation.
Column K / header "Migracao"  = Rodolfo's internal migration label/status, e.g. OK v1 / OK v2. Do not use it as the app column and do not filter it out unless Rodolfo explicitly asks for OK-only.
```

Default comparison should use **all rows with a non-empty `NO APP`**. Do not filter by `Migracao` by default.

## Normalization

- App codes: normalize `B1`, `B01`, `B001` to `B001` through `B010`.
- Names: trim whitespace and collapse repeated spaces.
- For comparisons, use casefolded Unicode-normalized keys, but report original display names.
- Detect duplicate sheet names per app; duplicates are sheet hygiene issues, not necessarily Meta API issues.

## Operational interpretation

- The Meta Graph `/roles` state is the runtime truth for who is currently an app admin/segurador.
- The sheet is the planning/assignment truth for who should be in each app.
- Reconciliation output should separate:
  - `Falta na API` — in sheet for app, not currently returned by Meta roles.
  - `Sobra na API` — currently returned by Meta roles, not assigned to that app in sheet.
  - `Duplicado sheet` — same normalized name appears more than once in the sheet for the same app.

## Owner/creator profile exceptions

Rodolfo clarified that some extra `/roles` profiles are intentional owner/creator profiles used to create/isolate each Meta app, not seguradores to reconcile against the sheet:

```text
B001 Dale Kuhlman
B002 Lola Lilliana
B003 Siyam Mia
B004 Mst Lija
B005 Wana Hsh
B006 Mic Vb
B007 พรชนิตว์ ฑีฆะวัฒน์
B008 Phạm Minh Thiện
B009 Hindawan Pratama
B010 Lorraynii Criistiinii
```

B009 and B010 owner profiles are also seguradores and have one page each; Rodolfo considers the risk acceptable if either profile is permanently blocked. When reporting reconciliation, include an `extra_non_owner` / `Sobra não-owner` count so these expected owner profiles do not appear as unresolved errors.

## Reporting style

For Rodolfo, report concise operational totals first, then divergence lists by app. Avoid Markdown pipe tables in Discord final messages; use aligned text blocks or bullets.

## Monitor/cron clarification

There is one production Hermes cron (`meta-app-roles-watch`) running every 2 minutes. It monitors all discovered `BOT Bxxx Token` 1Password items and routes alerts to app-specific channels. Do not create 10 separate crons unless Rodolfo explicitly asks for per-app independent schedules/failure isolation.

## Test alert pattern

When Rodolfo asks to preview alert UX, send explicit `TESTE` alerts to each B001–B010 channel using the Zeus Discord bot and current state roles. Do not mutate the monitor state. Include:

- `Estado: CRÍTICO / TESTE`
- `App`
- simulated count drop (`N → N-1`)
- `Removidos agora`
- `Removidos acumulados`
- `Admins atuais`
- `Observação: teste; não é incidente real`

Validate every POST returns `200 OK` and summarize per app/channel/status.