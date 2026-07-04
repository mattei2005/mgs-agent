# Script-only anomaly watchdog for #alerts-infra — 2026-06-22

## Context

Rodolfo asked Zeus to “ficar de olho” on `#alerts-infra` for the next hour after noisy Honcho and auto-push alerts. The first implementation used an LLM cron every 15 minutes and reported OK status. Rodolfo challenged whether this consumed unnecessary VPS/data and clarified the desired behavior: background monitoring that stays silent unless something important appears.

## Durable pattern

For short-lived operational watches where the goal is “only tell me if something is wrong”:

- Prefer `cronjob(no_agent=true)` with a deterministic shell/Python script over an LLM-driven cron.
- Success path must be silent: script writes **empty stdout** when all checks are OK.
- Non-empty stdout means anomaly and is delivered verbatim.
- Keep repeat count bounded for temporary watches (`repeat=12` with `schedule=5m` = 1 hour).
- Deduplicate by a stable anomaly key so the same issue does not ping repeatedly.
- Use local runtime sources that generate the channel alerts instead of scraping Discord when API/thread access is unnecessary.

## Example monitoring scope used

Sources checked for `#alerts-infra` anomaly watch:

- `data/auto-push-monitor.json` — active `consecutive_failures > 0`.
- Git local vs `origin/main` — `HEAD != origin/main` can indicate auto-push divergence.
- `data/honcho-health-state.json` — alert only when `alert_active=true` or `consecutive_failures >= 2`.
- `logs/monitor-service-restarts.log` — trust the fresh log’s latest OK state, not stale `last_alert_level` fields in state.

## Pitfalls

1. **LLM cron is overkill for watchdogs.** It costs tokens and can generate unnecessary OK chatter. Use script-only when logic is deterministic.
2. **`deliver=origin` + `no_agent=true` sends stdout verbatim.** This is desirable only if the script is silent on OK and concise on anomaly.
3. **State files can retain historical alert levels.** Example: `service-restart-state.json` kept `last_alert_level=warn` for `mgs-autocommit`, while the fresh monitor log showed `NRestarts=0 delta=0 level=ok`. For “is it bad now?”, prefer fresh log/runtime over stale alert metadata.
4. **Absolute scripts are rejected by Hermes cronjob.** `cronjob(script=...)` expects a filename relative to `~/.hermes/scripts/`; place the script there and pass `script="name.sh"`.
5. **Do not report OK every cycle unless asked.** The whole value of a watchdog is silence when healthy.

## Validation checklist

Before creating the cronjob:

```bash
chmod +x ~/.hermes/scripts/watch-alerts-infra-anomalies.sh
bash -n ~/.hermes/scripts/watch-alerts-infra-anomalies.sh
out=$(~/.hermes/scripts/watch-alerts-infra-anomalies.sh); rc=$?; printf 'rc=%s bytes=%s\n' "$rc" "${#out}"
# Healthy expected: rc=0 bytes=0
```

Cron shape:

```text
schedule: 5m
repeat: 12
no_agent: true
script: watch-alerts-infra-anomalies.sh
deliver: origin
```

## Response pattern

When switching from LLM watcher to script-only, tell Rodolfo:

- LLM watcher was removed/replaced.
- New watchdog is script-only, silent on OK, alert-only on anomaly.
- Cadence and duration.
- Current smoke test result (`output vazio` = healthy).
