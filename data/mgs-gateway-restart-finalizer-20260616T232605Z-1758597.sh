#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/mgs-gateway-restart-finalizer-20260616T232605Z-1758597.log"
AUDIT="/root/mgs-agent/logs/events-audit.jsonl"
REASON="validation-no-execute"
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-finalizer","reason":"%s","detail":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$REASON" "$2" >> "$AUDIT"; }
log "START detached gateway restart finalizer agents=atena ares hera zeus reason=$REASON"
audit "gateway_restart_finalizer_started" "agents=atena ares hera zeus log=$LOG"
for agent in atena ares hera zeus; do
  svc="${agent}-gateway.service"
  log "restart $svc"
  systemctl restart --no-block "$svc"
done
log "Validation is intentionally file-only; no foreground Discord/tool polling."
systemctl show atena-gateway.service ares-gateway.service hera-gateway.service zeus-gateway.service  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
for agent in atena ares hera zeus; do
  log "recent markers $agent"
  grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' "/root/.hermes/profiles/$agent/logs/agent.log" 2>/dev/null | tail -8 || true
done
audit "gateway_restart_finalizer_finished" "agents=atena ares hera zeus log=$LOG"
log "DONE detached gateway restart finalizer"
