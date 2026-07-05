#!/usr/bin/env bash
set -euo pipefail
LOG=/root/mgs-agent/logs/repair-gateway-collision-20260705-0215.log
AUDIT=/root/mgs-agent/logs/events-audit.jsonl
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"zeus","detail":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$AUDIT"; }
log 'START repair gateway collision after Hermes update; scope=atena ares hera only; zeus untouched'
audit 'gateway_collision_repair_started' 'scope=atena ares hera after hermes update 20260705'
for svc in atena-gateway.service ares-gateway.service hera-gateway.service; do
  log "stop $svc"
  systemctl stop "$svc" || true
done
sleep 3
log 'gateway pids before targeted kill'
ps -fp 245784,245797,245836 2>/dev/null || true
for pid in 245784 245797 245836; do
  if ps -p "$pid" -o args= 2>/dev/null | grep -Eq 'hermes_cli\.main --profile (ares|atena|hera) gateway run --replace'; then
    log "TERM orphan pid=$pid cmd=$(ps -p "$pid" -o args=)"
    kill -TERM "$pid" || true
  fi
done
sleep 8
for pid in 245784 245797 245836; do
  if ps -p "$pid" >/dev/null 2>&1; then
    log "KILL orphan pid=$pid cmd=$(ps -p "$pid" -o args=)"
    kill -KILL "$pid" || true
  fi
done
for svc in atena-gateway.service ares-gateway.service hera-gateway.service; do
  systemctl reset-failed "$svc" || true
done
for svc in ares-gateway.service hera-gateway.service atena-gateway.service; do
  log "start $svc"
  systemctl start "$svc"
done
sleep 12
log 'systemctl final state'
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus --no-pager || true
audit 'gateway_collision_repair_finished' "log=$LOG"
log 'DONE repair gateway collision'
