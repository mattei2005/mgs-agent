#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="/root/mgs-agent/logs/hermes-post-update-restart-${STAMP}.log"
REPO="/root/.hermes/hermes-agent"
exec > >(tee -a "$LOG") 2>&1
log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
log "START Hermes post-update restart finalizer"
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
log "Pre services"
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service || true
log "Restarting gateways: atena ares zeus"
systemctl restart atena-gateway.service ares-gateway.service
systemctl restart --no-block zeus-gateway.service
sleep 25
log "Post services active states"
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service || true
log "Service details"
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
log "Hermes version"
/root/.hermes/profiles/zeus/home/.local/bin/hermes --version 2>&1 | sed -n '1,12p' || hermes --version 2>&1 | sed -n '1,12p' || true
log "Patch guard"
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh 2>&1 | sed -n '1,80p'
log "Recent gateway log connection markers"
for p in zeus atena ares; do
  echo "--- $p ---"
  tail -120 "/root/.hermes/profiles/$p/logs/agent.log" 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' | tail -8 || true
done
log "DONE Hermes post-update restart finalizer log=$LOG"
