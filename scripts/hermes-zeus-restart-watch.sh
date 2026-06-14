#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="/root/mgs-agent/logs/hermes-zeus-restart-watch-${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1
log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
log "START Zeus restart watch"
for i in {1..60}; do
  state=$(systemctl show zeus-gateway.service -p ActiveState -p SubState -p MainPID --value --no-pager | tr '\n' ' ')
  log "zeus state: $state"
  if systemctl is-active --quiet zeus-gateway.service; then
    break
  fi
  sleep 2
done
log "Final service details"
systemctl show zeus-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStartTimestamp --no-pager || true
log "Recent Zeus connection markers"
tail -160 /root/.hermes/profiles/zeus/logs/agent.log 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' | tail -12 || true
log "DONE Zeus restart watch log=$LOG"
