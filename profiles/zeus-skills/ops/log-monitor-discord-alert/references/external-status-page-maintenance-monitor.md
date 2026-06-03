# External status page maintenance monitor

Use this pattern when Rodolfo asks for a cron that watches a vendor status page and alerts `#alerts-infra` only for a specific operational state, e.g. Webshare maintenance.

Validated case: `https://status.webshare.io/` on incident.io status pages.

## Pattern

- Script path: `/root/mgs-agent/scripts/monitor-<vendor>-status.sh`
- State path: `/root/mgs-agent/data/<vendor>-status-state.json`
- Log path: `/root/mgs-agent/logs/monitor-<vendor>-status.log`
- Cron: staggered `*/10` or `*/15` with `flock -n /var/lock/monitor_<vendor>_status.lock ...`
- Webhook: `Discord Webhook - Alerts Infra Channel`, field `webhook_url`, vault `MGS Conteúdo`
- Alert only on state transition `normal -> maintenance`; send green resolution on `maintenance -> normal`.
- Persist state before the external action (`curl` to Discord) to prevent alert loops.

## incident.io status page parsing notes

incident.io status pages may render key state inside escaped Next/React flight HTML rather than a simple JSON endpoint. Fetch the page HTML with a user-agent and parse conservatively:

```bash
curl -sSL --max-time 25 -A 'MGS-Infra-Monitor/1.0' -o "$TMP_HTML" 'https://status.webshare.io/'
```

Then in Python:

```python
import html, re
raw = open(path, errors='ignore').read()
text = html.unescape(raw).replace('\\"', '"').replace('\\/', '/')
```

Do not alert on generic words like `maintenance` or `Under maintenance` in the page: those labels appear in the translation/messages table even when no maintenance is active.

Safer detection:

- Active maintenance if any component has status `under_maintenance`, or an incident status has `maintenance_in_progress`.
- Scheduled maintenance array present but not in progress should usually be logged, not alerted, unless the user asked for advance-warning alerts.
- Degraded/partial outage is not maintenance; if the requested condition is maintenance-only, keep status `normal` and do not alert.

Component names can be listed separately from component statuses. Build an `id -> name` map from component definitions, then map `component_id` statuses from `affected_components` / `component_impacts`.

## Validation checklist

1. `bash -n scripts/monitor-<vendor>-status.sh`
2. `MGS_DRY_RUN=1 scripts/monitor-<vendor>-status.sh >> logs/... 2>&1`
3. Inspect state: `jq . data/<vendor>-status-state.json`
4. Run once without dry-run when current state should not alert, to verify safe no-op.
5. Add cron via backup/temp-file/crontab apply, not unsafe heredoc/pipe editing.
6. Run `infra-discovery.sh` and `cron-control-plane.py --write-doc` after adding the cron.
7. Append an audit event to `logs/events-audit.jsonl` with script, cron, state, source URL, and target channel.

## Discord payload

Use structured embeds. For a maintenance-start alert, include Rodolfo mention in `content` for push:

```json
{
  "content": "<@344196393512075265> Vendor em manutenção",
  "embeds": [{
    "title": "Vendor status em manutenção",
    "color": 15844367,
    "fields": [
      {"name": "Status page", "value": "https://status.vendor.example/"},
      {"name": "Motivo detectado", "value": "`component_under_maintenance`"},
      {"name": "Componentes", "value": "```text\n• API — under_maintenance\n```"},
      {"name": "Impacto operacional", "value": "Evitar iniciar jobs dependentes até normalizar."}
    ]
  }]
}
```

Resolution embed should have `content:""` and green color `3066993`.
