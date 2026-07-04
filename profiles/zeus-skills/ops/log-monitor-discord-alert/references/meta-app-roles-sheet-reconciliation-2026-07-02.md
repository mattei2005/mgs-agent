# Meta App Roles — full sheet reconciliation, not delta-only

## Trigger

Use when maintaining the `meta-app-roles-watch` cron or any monitor that syncs a Google Sheet column from live API state.

Rodolfo found that the migration sheet had users through row ~225 that were known blocked/absent, but column `Removidos acumulado` was still blank. The monitor was running and authenticated, but the implementation only mirrored `cumulative_removed` deltas observed after the state file started.

## Durable lesson

A monitor that updates an operational sheet must be a **full reconciler**, not only a delta detector.

For Meta App Roles:

- Google Sheet is the intent source:
  - `NO APP` = target Meta app/channel (`B001`–`B010`, `B005-2`)
  - `USUARIO` + `Segurador` = profile identity expected in that app
- Meta API live `/roles` is the runtime truth for who is currently in each app.
- Every run must compare sheet intent vs live Meta roles.
- If a row has `NO APP` and identity, but that identity is absent from the live Meta app, mark `Removidos acumulado = X`.
- If the identity is present in the live Meta app, clear/leave blank.
- If the app was not checked successfully or `NO APP` is unknown, do **not** invent a write; preserve state and report counts.
- `cumulative_removed` remains useful for reporting, but must not be the only write source.

## Pitfall that caused the incident

Delta-only logic:

```text
state.apps[*].cumulative_removed -> normalize names -> mark rows whose Segurador matches
```

This misses users that were already absent before monitor state existed. The cron can look healthy, authentication can be valid, and the sheet can still be stale.

## Correct reconciliation algorithm

```python
for row in sheet_rows:
    app_key = normalize(row['NO APP'])
    identity = row['USUARIO'] or row['Segurador']

    if not app_key or not identity:
        desired_x = ''
    elif app_key not checked_ok:
        desired_x = existing_value  # fail-safe: do not invent changes
    elif identity in live_meta_roles[app_key] by id or normalized name:
        desired_x = ''
    else:
        desired_x = 'X'
```

Track summary fields in state for future triage:

```json
{
  "checked_intent_rows": 221,
  "present": 157,
  "marked": 64,
  "marked_missing_current_meta": 24,
  "marked_cumulative_removed": 40,
  "unknown_app_rows": 0,
  "unmatched_removed": 6
}
```

## Validation checklist

After patching this class of monitor:

1. `bash -n` the script.
2. Run the monitor manually once.
3. Read back state summary.
4. Read back the sheet/export and confirm expected rows are changed.
5. Run via Hermes cron `cronjob(action='run')` and validate state timestamp advanced.
6. Send REPORT-INFRA and update `infra-inventory.json` if script/data changed.

For this incident the expected readback was:

```text
marked = 64
marked_missing_current_meta = 24
marked_cumulative_removed = 40
unknown_app_rows = 0
rows 201–225 absent from Meta marked with X
row 86 marked with X
```

## Reporting pattern to Rodolfo

Be direct and own the flaw:

```text
Você estava certo: o cron estava saudável, mas a lógica estava incompleta.
Ele era delta-only; agora é reconciliador completo planilha × Meta API live.
```

Do not say “estava funcionando” if the business outcome was wrong. Separate technical health from operational correctness.
