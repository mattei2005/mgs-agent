#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/hermes-agents-restart-validate-a8-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
printf '[%s] restarting Zeus/Atena/Ares gateways after Hermes a8 update\n' "$(date -Iseconds)"
systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service
sleep 20
printf '[%s] service active checks\n' "$(date -Iseconds)"
for s in zeus-gateway.service atena-gateway.service ares-gateway.service; do
  systemctl is-active --quiet "$s"
done
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
printf '[%s] connected markers\n' "$(date -Iseconds)"
for p in zeus atena ares; do
  echo "--- $p agent markers ---"
  tail -160 "/root/.hermes/profiles/$p/logs/agent.log" 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Starting gateway|Gateway started' | tail -10 || true
done
printf '[%s] recent timestamped errors\n' "$(date -Iseconds)"
for p in zeus atena ares; do
  echo "--- $p errors recent ---"
  grep -E '^2026-06-10 (16:3[8-9]|16:[4-5][0-9]|17:)' "/root/.hermes/profiles/$p/logs/errors.log" 2>/dev/null | tail -20 || true
done
printf '[%s] DONE restart validation log=%s\n' "$(date -Iseconds)" "$LOG"
