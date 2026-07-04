# Meta app roles — B011 + sheet GID correction (2026-07-04)

## Trigger

Rodolfo asked for repeated Meta App Roles / removidos acumulados counts and corrected operational assumptions:

1. The active migration sheet tab changed from `gid=562940072` to `gid=542936436`.
2. The temporary app label `B011` was renamed to canonical app/channel label `B011` in the sheet and 1Password (`BOT B011 Token`).

## Durable workflow corrections

- For Meta App Roles reconciliation, use the current sheet tab `gid=542936436` unless Rodolfo provides a newer GID.
- App-key canonicalization must preserve suffix/replacement labels such as `B005-2`; do not collapse app labels with regex shortcuts.
- `B011` is canonical. Do **not** route `BOT B011 Token` back to `B011`.
- Count and report `B001` and `B011` as distinct channels/apps.
- Operational scope for “all channels” is 11 channels: `B001`, `B002`, `B003`, `B004`, `B005-2`, `B006`, `B007`, `B008`, `B009`, `B010`, `B011`.
- When user asks for alerts in “all channels”, expected scope is those 11 canonical channels/apps.

## Counting pitfall

Bad parser:

```python
m = re.search(r'B\s*0*(\d{1,2})(?:\s*-\s*(\d+))?', raw)
return f'B{int(m.group(1)):03d}'
```

This pitfall now applies historically to `B011`; current canonical label is `B011`. Do not collapse `B011` into any other app key.

Safer parser:

```python
raw = str(value or '').strip().upper()
m = re.fullmatch(r'B\s*0*(\d{1,3})(?:\s*-\s*(\d+)|\s*([A-Z]+))?', raw)
# preserves B011 and B005-2 as distinct labels
...
```

## Operational interpretation from the corrected count

After the rename, `B011` is the only canonical label for the former temporary `B011` channel/app. Do not describe this as a B001 problem and do not emit `B011` in user-facing alerts.

If `B011` shows one API role such as `Thiago Oliveira`, treat it as likely owner/admin until validated against the owner map; owner/admin roles should be ignored like other app owners when reconciling expected seguradores.

## Validation pattern

For a real alert push, run the official monitor **without** snapshot forcing. Constrain scope with `MGS_META_APP_ROLE_ITEMS` only when needed.

Expected live-path validation:

- `items` includes the requested app token items, including `BOT B011 Token` when testing all 11 channels.
- `errors_count == 0`.
- `dry_run == false`.
- `force_snapshot_effective == false`.
- `alerts_sent` may be `0` when there is no real delta/failure/rate-limit event.

Do not use `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` for Rodolfo requests like “manda alerta”, “manda de novo” or “roda o cron”. Snapshot mode is historical/diagnostic only and now requires the explicit unlock `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT`.