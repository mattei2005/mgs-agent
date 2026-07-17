# Hermes update 2026-06-12 — stale update cache, self-restart finalizers, and cron alert validation

Use this reference when a Hermes update appears successful by Git state but `hermes --version`, systemd transient units, or cron/alert expectations create ambiguity.

## Durable lessons

### 1. Git state beats stale update banners

Symptom after update:

```text
hermes --version -> Update available: N commits behind
 git HEAD == origin/main, rev-list HEAD..origin/main == 0
```

Cause: `.update_check` cache can survive/lag after controlled/manual update.

Fix:

```bash
rm -f /root/.hermes/.update_check /root/.hermes/profiles/*/.update_check
hermes --version
```

Expected after fix:

```text
Up to date
```

Validation source of truth:

```bash
repo=/root/.hermes/hermes-agent
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD origin/main
git -C "$repo" rev-list --count HEAD..origin/main
```

### 2. Restarting gateways from an update finalizer can make the finalizer fail even when services are healthy

If a systemd-run update/finalizer restarts Zeus/Atena/Ares/agente legado and includes the current Zeus gateway in the restart set, the transient unit can be interrupted or left failed. Do not immediately repeat the update/restart.

Recovery sequence:

1. Inspect current state only.
2. Confirm repo `behind=0`.
3. Confirm all gateways `active/running`, `NRestarts=0`, `ExecMainStatus=0`.
4. Run patch guard.
5. Clear/reset failed transient update units if they are only historical:

```bash
systemctl reset-failed mgs-hermes-update-*.service || true
```

For future all-agent update scripts, prefer:

```bash
systemctl restart --no-block zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service
sleep 20
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service
```

This avoids blocking the finalizer on a service that may terminate the current gateway/session.

### 3. Canonical patch guard may fail on a new upstream even when saved local diff applies cleanly

During update, `ensure-hermes-mgs-patches.sh` can fail because canonical patch context drifted. If a pre-update local diff was saved, test and apply it before declaring the update failed:

```bash
if ! /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh; then
  if [[ -s "$LOCAL_PATCH" ]] && git -C "$REPO" apply --check "$LOCAL_PATCH"; then
    git -C "$REPO" apply "$LOCAL_PATCH"
    /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
  else
    exit 1
  fi
fi
```

Always compile after patch restoration:

```bash
/root/.hermes/hermes-agent/venv/bin/python -m py_compile \
  /root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py \
  /root/.hermes/hermes-agent/gateway/run.py \
  /root/.hermes/hermes-agent/gateway/config.py \
  /root/.hermes/hermes-agent/tools/send_message_tool.py \
  /root/.hermes/hermes-agent/tools/discord_tool.py
```

### 4. `npm install` can dirty `package-lock.json`; clean it unless intentionally changing dependencies

After update maintenance, inspect `package-lock.json`. If `npm install` only introduced lockfile metadata churn and no dependency change was intended, revert it:

```bash
git -C /root/.hermes/hermes-agent checkout -- package-lock.json
```

### 5. "No alerts received" does not prove crons are broken

When Rodolfo asks whether crons/alerts are functioning after silence, validate both scheduler execution and alert conditions:

```bash
systemctl is-active cron
crontab -l
journalctl -u cron --since '12 hours ago' --no-pager | tail -120
hermes -p zeus cron list
```

Then inspect key alert logs, not just crontab entries:

```bash
tail -20 /root/mgs-agent/logs/monitor-service-restarts.log
tail -20 /root/mgs-agent/logs/monitor-cron-stale-logs.log
tail -20 /root/mgs-agent/logs/monitor-hermes-updates.log
tail -20 /root/mgs-agent/logs/check-pending-reports.log
tail -20 /root/mgs-agent/logs/monitor-tool-loops.log
```

Report the difference clearly:

```text
Crons funcionando?        Sim/Não, based on cron journal + log mtimes
Alertas quebrados?        Sim/Não, based on delivery/log evidence
Por que sem alertas?      No condition triggered / delivery failure / stale logs
Gap identificado?         E.g. planned/manual restarts may not trigger current NRestarts thresholds
```

Important nuance: `monitor-service-restarts.sh` primarily watches systemd `NRestarts` thresholds. A controlled/manual `systemctl restart` can leave `NRestarts=0`, so it may not alert even though `ActiveEnterTimestamp` changed. If Rodolfo expects notification for planned/manual restarts, extend the monitor to detect `ActiveEnterTimestamp` changes with anti-spam and a controlled-vs-unexpected distinction.
