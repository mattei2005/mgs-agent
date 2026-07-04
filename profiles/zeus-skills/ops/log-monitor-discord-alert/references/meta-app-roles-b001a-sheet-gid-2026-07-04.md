# Meta app roles — B001A + sheet GID correction (2026-07-04)

## Trigger

Rodolfo asked for repeated Meta App Roles / removidos acumulados counts and corrected two operational assumptions:

1. The active migration sheet tab changed from `gid=562940072` to `gid=542936436`.
2. `B001A` is a new app and must be treated as a separate app, not normalized into `B001`.

## Durable workflow corrections

- For Meta App Roles reconciliation, use the current sheet tab `gid=542936436` unless Rodolfo provides a newer GID.
- App-key canonicalization must preserve alpha suffixes such as `B001A`.
- Do **not** parse `B001A` with a numeric-only regex that collapses it to `B001`.
- Count and report `B001` and `B001A` as distinct channels/apps.
- Operational scope for “all channels” is 11 channels: `B001`, `B001A`, `B002`, `B003`, `B004`, `B005-2`, `B006`, `B007`, `B008`, `B009`, `B010`.
- Current 1Password credential naming may expose B001A as legacy item `BOT B011 Token`; canonicalize item code `B011` to operational app key `B001A` before state, channel routing, sheet reconciliation, or alert titles.
- When user asks for alerts in “all channels” after B001A exists, expected scope is 11 channels: `B001`, `B001A`, `B002`, `B003`, `B004`, `B005-2`, `B006`, `B007`, `B008`, `B009`, `B010`.

## Counting pitfall

Bad parser:

```python
m = re.search(r'B\s*0*(\d{1,2})(?:\s*-\s*(\d+))?', raw)
return f'B{int(m.group(1)):03d}'
```

This turns `B001A` into `B001` and makes B001 look like it has all B001A removals.

Safer parser:

```python
raw = str(value or '').strip().upper()
if raw.startswith('B001A'):
    return 'B001A'
m = re.search(r'B\s*0*(\d{1,2})(?:\s*-\s*(\d+))?', raw)
...
```

## Operational interpretation from the corrected count

After separating `B001` and `B001A`, `B001` can be clean while `B001A` carries the removidos acumulados. Do not describe this as a B001 problem.

If `B001A` shows one API role such as `Thiago Oliveira`, treat it as likely owner/admin until validated against the owner map; owner/admin roles should be ignored like other app owners when reconciling expected seguradores.

## Validation pattern

For a real alert push, run the official monitor **without** snapshot forcing. Constrain scope with `MGS_META_APP_ROLE_ITEMS` only when needed.

Expected live-path validation:

- `items` includes the requested app token items, including `BOT B001A Token` when testing all 11 channels.
- `errors_count == 0`.
- `dry_run == false`.
- `force_snapshot_effective == false`.
- `alerts_sent` may be `0` when there is no real delta/failure/rate-limit event.

Do not use `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` for Rodolfo requests like “manda alerta”, “manda de novo” or “roda o cron”. Snapshot mode is historical/diagnostic only and now requires the explicit unlock `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT`.