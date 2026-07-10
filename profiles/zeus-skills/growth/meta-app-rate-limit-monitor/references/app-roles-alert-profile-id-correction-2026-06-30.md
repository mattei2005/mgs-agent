# App Roles Alert Profile ID Correction — 2026-06-30

## Trigger

Rodolfo corrected the B001–B010 Meta App Roles alert format after the monitor briefly displayed the long numeric Meta Graph `/roles.user` ID in the user list.

The required human-facing format is:

```text
Nome - profile_id - Admin
```

Example:

```text
Amoey Pnr - decha.aja.161 - Admin
```

## Correct source for `profile_id`

Use the Google Sheet tab `Migracao 22/06`:

```text
Spreadsheet: 1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY
GID:         562940072
CSV:         https://docs.google.com/spreadsheets/d/1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY/export?format=csv&gid=562940072
```

Column mapping as corrected in the live sheet export:

```text
Segurador   = display name used to match Meta role name
USUARIO     = profile_id to show in alerts (Rodolfo called this column K)
NO APP      = app assignment B001–B010
Migracao    = internal migration/status label; not the profile ID
```

## Implementation rule

For `Usuários do app`, `Usuários removidos`, `Usuários adicionados`, and `Removidos acumulados`:

1. Query Meta Graph `/roles` for runtime truth: who is currently in the app and their role.
2. Resolve role names normally via `GET /{user_id}?fields=id,name`.
3. Fetch the sheet CSV.
4. Match `role.name` to sheet `Segurador` using normalized name matching.
5. Display sheet `USUARIO` as the middle identifier.
6. Do **not** display the long Graph numeric `user` ID in human-facing operational alerts.
7. For owner/creator profiles not present as seguradores in the sheet, display an owner marker such as `owner do app`, not the long numeric ID.

## Validation pattern

Do **not** send real forced snapshots for routine validation/resend. Validate formatting in dry-run only, and use the live monitor path for Rodolfo requests like “manda alerta”, “manda de novo” or “roda o cron”.

Dry-run only:

```bash
cd /root/mgs-agent
set -a
source .env 2>/dev/null || true
set +a
MGS_META_APP_ROLES_DRY_RUN=1 \
  MGS_META_APP_ROLE_ITEMS='BOT B001 Token' \
  /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh > /tmp/meta-app-roles-profileid-dryrun.jsonl
```

For an explicit snapshot diagnostic, `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` is not enough anymore; it is blocked unless Rodolfo explicitly asks for snapshot and the command also sets `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT`.

Verify:

- normal live dry-run has `force_snapshot_effective=false`;
- profile IDs resolve from the sheet when a real delta/snapshot diagnostic is rendered;
- the monitor path without snapshot sends only real deltas/failures/rate-limit alerts.

## Pitfall

The Meta `/roles` endpoint returns a `user` value that looks useful, but it is not the identifier Rodolfo wants in Discord. Treat it as a runtime join key only, not as alert copy.