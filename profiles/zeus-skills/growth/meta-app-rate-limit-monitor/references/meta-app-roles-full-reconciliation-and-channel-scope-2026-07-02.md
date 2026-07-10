# Meta App Roles sheet reconciliation corrections — 2026-07-02

## Trigger

Rodolfo found that the migration sheet had users through ~row 225 that were known blocked/out of the app but were not marked with `X` in `Removidos acumulado`.

## Root cause

The `meta-app-roles-watch` cron was behaving as a delta detector: it marked rows only for profiles it had observed disappearing after the monitor state was created. Profiles already absent from Meta roles before state creation were invisible to the `X` sync.

## Correct model

Every run must be a full reconciler:

1. Read Google Sheet tab `Migracao 22/06`.
2. Treat `NO APP` as the app assignment source (`B001`–`B010`, including `B005-2`).
3. Treat `Segurador` + `USUARIO` as the intended profile identity.
4. Fetch current Meta `/roles` for every app.
5. For each row with `NO APP` and identity:
   - present in current Meta roles by Meta ID or normalized name → clear `X`;
   - absent from current Meta roles → write `X`;
   - app not successfully checked → preserve existing marker and surface `unknown_app_rows`, do not invent changes.
6. Keep `cumulative_removed` only as context/history, not the primary source for sheet `X`.

## Important user correction: manager channels are not infra/status channels

Rodolfo rejected a broad Zeus status/correction notice posted to the ten `#b00x-app-rate-limit` channels. Those channels are only for manager-facing, app-specific operational alerts:

- app/token/API/rate-limit failure;
- segurador/admin removed from app roles;
- segurador/admin added to app roles;
- app-specific action needed by managers.

Do **not** post Zeus internal fixes, reconciliation explanations, REPORT-INFRA, or broad status notices there. Keep those in Zeus/#alerts-infra unless Rodolfo explicitly asks for manager-facing broadcast copy and approves the wording.

If an incorrect broad notice is posted, delete it from all ten channels immediately and report the deletion result to Rodolfo.

## Perfil antigo handling

The sheet may encode planned migration in `OBS` as:

```text
Perfil antigo: <old profile name>
```

When a removed Meta role name matches a `Perfil antigo` value for the same `NO APP`, remove/suppress it from `Removidos acumulados`; it is planned migration/housekeeping, not an active incident. Example corrected: B003 row for `Sebastiana Francisca` had `OBS: Perfil antigo: Vanderlina Diogo`, so `Vanderlina Diogo` should not continue in accumulated removed alerts.

## Display fallback

When a current Meta role is not matched to the sheet, do not display `sem ID` if the Meta `/roles.user` ID exists. Use the Meta ID as fallback so the row is actionable. Still prefer sheet `USUARIO` when matched.

## Validation pattern

After changing the monitor:

```bash
bash -n /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh
bash /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh
python3 - <<'PY'
import json
from pathlib import Path
s=json.loads(Path('/root/mgs-agent/data/meta-app-role-monitor-state.json').read_text())
print(s['_sheet_removed_sync'])
PY
```

Expected post-fix fields include:

```text
checked_intent_rows
present
marked
marked_missing_current_meta
marked_cumulative_removed
unknown_app_rows
unmatched_removed
updated
```

The fix that prompted this reference produced `marked=64`, `marked_missing_current_meta=24`, `unknown_app_rows=0` and filled the missing `X` rows including line 86 and the blocked rows in 201–225.
