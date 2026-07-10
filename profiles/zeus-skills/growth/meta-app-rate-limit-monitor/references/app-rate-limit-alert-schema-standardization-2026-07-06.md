# App-rate-limit alert schema standardization — 2026-07-06

## Trigger

Rodolfo reviewed the B011 app-rate-limit alert layout and corrected the schema:

- B011 `👥 USUÁRIOS ATUAIS` was showing `BOT EMAIL | SEGURADOR | STATUS | PÁGINAS`.
- B001–B010/B005-2 were showing `BOT EMAIL | SEGURADOR | PERFIL ID`.
- B011 `📦 REMOVIDOS ACUMULADOS` had a `MOTIVO` column.

He requested one unified manager-facing schema across all 11 app channels:

```text
BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS
```

And for B011 accumulated removals: remove `MOTIVO`; if a profile is under `📦 REMOVIDOS ACUMULADOS`, that already communicates the profile/link is off/disconnected.

## Canonical source columns

Use the Google Sheet tab `Migracao 22/06`:

```text
BOT EMAIL  -> column A / User
SEGURADOR  -> column D / Segurador
PÁGINAS    -> column E / PG
PERFIL ID  -> column K / USUARIO
NO APP     -> column L / NO APP
```

For B001–B010/B005-2, Meta `/roles` provides current runtime membership and the sheet enriches with bot email/profile ID/pages. For B011, DTR/ChatPion + Meta `debug_token` provides current linked accounts, and the same sheet enriches with bot email/profile ID/pages.

## Implementation pattern

B001–B010/B005-2 (`meta-app-roles-watch.sh`):

- Extend `load_sheet_users()` to store `pages = row['PG']`.
- Extend `sheet_user()` to return `pages` with `'-'` fallback.
- Update `fmt_roles()` header to `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS`.
- Keep `PERFIL ID` fallback to Meta `/roles.user` ID when sheet ID is missing.

B011 (`b011-dtr-link-watch.sh`):

- Extend `sheet_rows()` targets with `pages = row['PG']`.
- Update `fmt_status_rows()` to replace `STATUS` with `PERFIL ID`, keeping `PÁGINAS`.
- Update `fmt_pending_rows()` to replace `MOTIVO` with `PÁGINAS`; do not show raw error/reason in the manager-facing accumulated list.

## Validation pattern

Before sending a real alert:

1. Compile embedded Python from both scripts.
2. Run `bash -n` on both scripts.
3. Dry-run B001 with live Meta + sheet data:

```bash
MGS_META_APP_ROLES_DRY_RUN=1 \
MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1 \
MGS_META_APP_ROLE_ITEMS='BOT B001 Token' \
/root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh
```

Expected B001 current users header:

```text
BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS
```

4. Unit-check B011 format helpers with `/tmp/sb-venv/bin/python` if Playwright is not available in system Python.
5. Only after validation, send the requested real alert using the force-live env var for the specific channel.

## Operational caution

When Rodolfo asks “manda alerta real no B001 primeiro; se ficou bom mando B002–B011”, send only B001 after applying and validating. Do not proactively send B002–B011 until he confirms the B001 visual result.
