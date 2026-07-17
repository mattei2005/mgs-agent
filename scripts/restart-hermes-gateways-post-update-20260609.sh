#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/hermes-gateway-restart-post-update-20260609-$(date +%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
printf '[%s] START post-update gateway restart\n' "$(date -Is)"
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
sleep 20
printf '[%s] SERVICES\n' "$(date -Is)"
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager
printf '[%s] RECENT CONNECT LOGS\n' "$(date -Is)"
for p in zeus atena ares; do
  printf '\n== %s ==\n' "$p"
  tail -120 "/root/.hermes/profiles/$p/logs/agent.log" 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready as' | tail -8 || true
done
printf '[%s] DONE post-update gateway restart log=%s\n' "$(date -Is)" "$LOG"
