# App Roles Discord mobile layout — 2026-06-30

## Context

During the B001–B010 Meta App Roles rollout, Rodolfo reviewed multiple Discord screenshots on mobile. The main failure mode was trying to fit too much into embeds or a 4-column table. Discord mobile truncated emails and the rightmost `ROLE/Admin` column became a useless repeated strip.

## Accepted format

Use the same 3-message shape for both forced snapshots and automatic cron role-change alerts:

1. Short embed only for summary:
   - title: `Meta APP - Bxxx`
   - fields: `ESTADO`, `CONTAGEM`, `ADMIN`, `USO`
   - no role/user tables inside the embed.
2. Normal Discord message with one code block:
   - heading: `Usuários Atuais:`
   - table below.
3. Normal Discord message with one code block:
   - no `Movimentações - Bxxx` title
   - no `Ordenado por BOT EMAIL` line
   - sections: `Usuários removidos agora:`, `Usuários adicionados agora:`, `Removidos acumulados:`.

## Accepted table columns

Use:

```text
BOT EMAIL                | SEGURADOR                | PERFIL ID
```

Do not include `ROLE` / `Admin`; all entries are app admins, so the column adds no information and wastes mobile width.

Display BOT EMAIL as the local part only:

```text
disparosopenzed@gmail.com -> disparosopenzed
```

Still sort by the full underlying email so grouping remains stable.

## Data rules

- `BOT EMAIL`: Google Sheet `Migracao 22/06`, column A / `User`.
- `PERFIL ID`: same sheet, column K / `USUARIO`.
- Match sheet rows by normalized `Segurador` name.
- Never show the raw long Meta Graph `/roles.user` numeric ID as the human-facing profile ID when sheet `USUARIO` exists.

## Cumulative removed cleanup rule

`Removidos acumulados` must exclude anyone currently in the app, even if the raw Meta role ID changed. Match by composed identity:

- raw Meta ID
- normalized `Segurador` name
- sheet `PERFIL ID` / `USUARIO`

A person must never appear in both `Usuários adicionados agora` and `Removidos acumulados` in the same alert.

## Pitfall fixed

The forced snapshot path had been updated first, but the cron's automatic role-change alert path still used the old embed-heavy format. Any future layout change must patch both paths or centralize formatting so snapshots and deltas cannot diverge.
