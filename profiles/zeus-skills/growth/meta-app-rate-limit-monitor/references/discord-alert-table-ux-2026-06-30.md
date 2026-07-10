# Discord Alert Table UX — Meta App Roles (2026-06-30)

Session learning from Rodolfo while iterating B001–B010 app-role alerts.

## What Rodolfo rejected

- Wide role tables inside Discord embed fields. Discord/mobile truncates email columns and the result is visually poor.
- Hiding the replacement app label: when the production app is `B005-2`, alerts must show `B005-2`, not canonicalize visually to `B005`.
- Long Meta Graph numeric `/roles.user` IDs in human-facing alerts. Rodolfo wants the profile/user ID from the migration sheet.
- Keeping a user in `Removidos acumulados` after that user is added/current again.

## Data sources for role rows

Google Sheet tab `Migracao 22/06`:

```text
Column A / User     = bot email
Column K / USUARIO  = profile ID to display
Segurador           = display name used to match Graph API role name
NO APP              = app assignment for reconciliation
Migracao            = internal status; do not use as profile ID
```

Meta Graph `/roles` remains the runtime truth for current app admins, but the sheet enriches rows for human-readable bot email/profile ID.

## Preferred alert shape

Use **short Discord embed + normal monospaced message(s)**.

Embed: compact summary only.

```text
Meta APP - B001
Estado: OK
Contagem: 11
Admin: Dale Kuhlman
Uso: 10% (call_count)
```

Normal message/code block 1: current users.

```text
Usuários do app - B001

BOT EMAIL                  | SEGURADOR                | PERFIL ID                | ROLE
...
```

Normal message/code block 2: movements/history.

```text
Movimentações - B001

Usuários removidos:
Nenhum.

Usuários adicionados:
Nenhum.

Usuários acumulados:
BOT EMAIL                  | SEGURADOR                | PERFIL ID                | ROLE
...
```

Keep current users separate from movement/history sections. Do not put the movement sections inside the `Meta APP - Bxxx` current-user block.

## Formatting rules

- Column labels should be short: `BOT EMAIL | SEGURADOR | PERFIL ID | ROLE`.
- Use `|` dividers between columns.
- Preserve a blank line after section/table headers when showing monospaced blocks.
- Avoid embed fields for the role table; embeds are for summary fields only.
- For owner profiles not in the sheet, display `owner do app` as PERFIL ID and `sem email` as BOT EMAIL.

## State/diff rules

- Replacement apps with suffixes, e.g. `BOT B005-2 Token`, should display/state as `B005-2` while routing to the existing B005 channel.
- `Removidos acumulados` must be recomputed by excluding any profile currently present in `/roles` before alerting.
- A profile must never appear simultaneously in `Usuários adicionados` and `Removidos acumulados`.
