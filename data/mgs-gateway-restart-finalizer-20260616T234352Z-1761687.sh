#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/mgs-gateway-restart-finalizer-20260616T234352Z-1761687.log"
AUDIT="/root/mgs-agent/logs/events-audit.jsonl"
REASON="Ares allowed_channels inclui canal Hera para responder a mentions em threads Hera; free-response permanece só no canal Ares"
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-finalizer","reason":"%s","detail":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$REASON" "$2" >> "$AUDIT"; }
log "START detached gateway restart finalizer agents=ares reason=$REASON"
audit "gateway_restart_finalizer_started" "agents=ares log=$LOG"
for agent in ares; do
  [[ "$agent" == "zeus" ]] && continue
  svc="${agent}-gateway.service"
  log "restart $svc (detached finalizer, blocking inside external job)"
  systemctl restart "$svc"
done
if [[ " ares " == *" zeus "* ]]; then
  log "restart zeus-gateway.service last (--no-block so this finalizer is not killed by its own caller)"
  systemctl restart --no-block zeus-gateway.service
fi
log "Validation is intentionally file-only; no foreground Discord/tool polling."
systemctl show ares-gateway.service  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
for agent in ares; do
  log "recent markers $agent"
  grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' "/root/.hermes/profiles/$agent/logs/agent.log" 2>/dev/null | tail -8 || true
done
audit "gateway_restart_finalizer_finished" "agents=ares log=$LOG"
log "DONE detached gateway restart finalizer"
