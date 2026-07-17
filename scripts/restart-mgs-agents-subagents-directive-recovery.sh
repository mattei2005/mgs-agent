#!/usr/bin/env bash
set -euo pipefail
TS="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG="/root/mgs-agent/logs/restart-mgs-agents-subagents-directive-recovery-${TS}.log"
AUDIT="/root/mgs-agent/logs/events-audit.jsonl"
exec >>"$LOG" 2>&1

echo "ts_start=$(date -u --iso-8601=seconds)"
echo "purpose=verify_or_recover_zeus_after_self_restart"
sleep 35

state=$(systemctl is-active zeus-gateway.service || true)
echo "zeus_state_initial=$state"
if [ "$state" != "active" ]; then
  echo "zeus not active; resetting failed/starting"
  systemctl reset-failed zeus-gateway.service || true
  systemctl start zeus-gateway.service || systemctl restart zeus-gateway.service || true
  sleep 20
fi

printf 'final_states:\n'
systemctl is-active atena-gateway.service ares-gateway.service zeus-gateway.service || true

python3 - <<PY
import json, datetime, subprocess
services=["atena-gateway.service","ares-gateway.service","zeus-gateway.service"]
states={}
for s in services:
    p=subprocess.run(["systemctl","is-active",s], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    states[s]=p.stdout.strip()
entry={
  "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "mgs_agents_restart_recovery_verification",
  "actor": "zeus_external_finalizer",
  "reason": "verify runtime load of subagents/background directive after Zeus self-restart",
  "states": states,
  "result": "all_active" if all(v=="active" for v in states.values()) else "attention_required",
  "credentials_touched": False,
  "log": "$LOG",
}
with open("$AUDIT","a") as f:
    f.write(json.dumps(entry, ensure_ascii=False)+"\n")
print(entry)
PY

echo "ts_end=$(date -u --iso-8601=seconds)"
