#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/mgs-gateway-restart-finalizer-20260617T000932Z-1767784.log"
AUDIT="/root/mgs-agent/logs/events-audit.jsonl"
REASON="urgent-discord-loop-fix-no-content-notice-extension"
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-finalizer","reason":"%s","detail":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$REASON" "$2" >> "$AUDIT"; }
log "START detached gateway restart finalizer agents=ares hera reason=$REASON"
audit "gateway_restart_finalizer_started" "agents=ares hera log=$LOG"
for agent in ares hera; do
  [[ "$agent" == "zeus" ]] && continue
  svc="${agent}-gateway.service"
  log "restart $svc (detached finalizer, blocking inside external job)"
  systemctl restart "$svc"
done
if [[ " ares hera " == *" zeus "* ]]; then
  log "restart zeus-gateway.service last (--no-block so this finalizer is not killed by its own caller)"
  systemctl restart --no-block zeus-gateway.service
fi
log "Validation is intentionally file-only; no foreground Discord/tool polling."
systemctl show ares-gateway.service hera-gateway.service  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
for agent in ares hera; do
  log "recent markers $agent"
  grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' "/root/.hermes/profiles/$agent/logs/agent.log" 2>/dev/null | tail -8 || true
done
audit "gateway_restart_finalizer_finished" "agents=ares hera log=$LOG"
log "DONE detached gateway restart finalizer"
