#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/hermes-agents-restart-validate-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
printf '[%s] restarting Zeus/Atena/Ares gateways\n' "$(date -Iseconds)"
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
sleep 20
printf '[%s] service active checks\n' "$(date -Iseconds)"
systemctl is-active --quiet zeus-gateway.service
systemctl is-active --quiet atena-gateway.service
systemctl is-active --quiet ares-gateway.service
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
printf '[%s] recent errors after restart marker\n' "$(date -Iseconds)"
for p in zeus atena ares; do
  echo "--- $p errors recent ---"
  if [[ -f "/root/.hermes/profiles/$p/logs/errors.log" ]]; then
    tail -40 "/root/.hermes/profiles/$p/logs/errors.log" | sed -n '1,40p'
  else
    echo "no errors.log"
  fi
done
printf '[%s] connected markers\n' "$(date -Iseconds)"
for p in zeus atena ares; do
  echo "--- $p agent markers ---"
  tail -120 "/root/.hermes/profiles/$p/logs/agent.log" 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Starting gateway|Gateway started' | tail -10 || true
done
printf '[%s] DONE restart validation log=%s\n' "$(date -Iseconds)" "$LOG"
