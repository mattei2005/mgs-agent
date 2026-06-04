# MGS Ops Control Plane — read-only collector pattern

Use this pattern when Rodolfo asks to start a broad operational control plane/dashboard/briefing, especially before adding cron delivery or Discord alerts.

## Session-derived rule

If Rodolfo scopes an agent out explicitly (example: "Atena deixa por último e me avise antes de mexer nela"), treat that as a hard gate:

- Do not inspect that agent's profile, logs, config, sessions, skills, or service-specific state in the first collector.
- Make the exclusion visible in the report header (`Atena excluída por gate do Rodolfo`).
- Add the agent only after explicit approval.

## Recommended v1 shape

Create a deterministic read-only script under `/root/mgs-agent/scripts/`, not a cron first. The script should:

- collect systemd service health for allowed agents/services;
- collect root crontab count and stale-monitor summary;
- collect pending approvals and pending REPORT-INFRA state;
- collect git branch/head/dirty state;
- collect disk status;
- summarize recent monitor logs;
- emit both human text and `--json` output for future automation;
- avoid credentials and never print tokens/secrets.

## Validation before reporting success

Run:

```bash
chmod +x /root/mgs-agent/scripts/<collector>.py
python3 -m py_compile /root/mgs-agent/scripts/<collector>.py
/root/mgs-agent/scripts/<collector>.py | head -120
/root/mgs-agent/scripts/<collector>.py --json >/tmp/<collector>.json
python3 - <<'PY'
import json
json.load(open('/tmp/<collector>.json'))
print('json ok')
PY
```

Then append an `events-audit.jsonl` entry with paths, scope, validation, and `secrets_included=false`.

## Phased rollout

1. Read-only collector on demand.
2. Discord-safe renderer/manual briefing.
3. Cron scheduling only after Rodolfo approves cadence and target channel.
4. Proactive alerts only after thresholds are explicit.

Do not turn a first collector into a scheduled alerting system in the same step unless Rodolfo explicitly asks for it.