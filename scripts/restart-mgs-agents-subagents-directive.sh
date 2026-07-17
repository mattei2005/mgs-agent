#!/usr/bin/env bash
set -euo pipefail

TS="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG="/root/mgs-agent/logs/restart-mgs-agents-subagents-directive-${TS}.log"
AUDIT="/root/mgs-agent/logs/events-audit.jsonl"
exec >>"$LOG" 2>&1

echo "ts_start=$(date -u --iso-8601=seconds)"
echo "reason=subagents_background_directive_runtime_reload"
echo "services=atena-gateway.service ares-gateway.service zeus-gateway.service"

echo "before:"
systemctl is-active atena-gateway.service ares-gateway.service zeus-gateway.service || true

python3 - <<PY
import json, datetime
entry={
  "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "mgs_agents_restart_started",
  "actor": "rodolfo/zeus",
  "reason": "load subagents/background directive in runtime",
  "services": ["atena-gateway.service","ares-gateway.service","zeus-gateway.service"],
  "restart_method": "systemd-run external finalizer; zeus last; no credentials touched",
  "log": "$LOG",
}
with open("$AUDIT","a") as f:
    f.write(json.dumps(entry, ensure_ascii=False)+"\n")
PY

# Give Zeus a moment to return control before services restart.
sleep 8

for svc in atena-gateway.service ares-gateway.service; do
  echo "restarting=$svc ts=$(date -u --iso-8601=seconds)"
  systemctl restart "$svc"
  sleep 5
  state=$(systemctl is-active "$svc" || true)
  echo "state_after $svc=$state"
  if [ "$state" != "active" ]; then
    echo "ERROR: $svc not active after restart"
    systemctl status "$svc" --no-pager -n 20 || true
    exit 1
  fi
done

echo "restarting=zeus-gateway.service ts=$(date -u --iso-8601=seconds)"
systemctl restart --no-block zeus-gateway.service
sleep 18
zeus_state=$(systemctl is-active zeus-gateway.service || true)
echo "state_after zeus-gateway.service=$zeus_state"
if [ "$zeus_state" != "active" ]; then
  echo "ERROR: zeus-gateway.service not active after restart"
  systemctl status zeus-gateway.service --no-pager -n 30 || true
  exit 1
fi

echo "after:"
systemctl is-active atena-gateway.service ares-gateway.service zeus-gateway.service || true

python3 - <<PY
import json, datetime
entry={
  "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "mgs_agents_restart_completed",
  "actor": "zeus",
  "reason": "load subagents/background directive in runtime",
  "services": ["atena-gateway.service","ares-gateway.service","zeus-gateway.service"],
  "result": "all_active",
  "credentials_touched": False,
  "log": "$LOG",
}
with open("$AUDIT","a") as f:
    f.write(json.dumps(entry, ensure_ascii=False)+"\n")
PY

echo "ts_end=$(date -u --iso-8601=seconds)"
echo "DONE all_active"
