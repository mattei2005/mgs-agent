#!/usr/bin/env bash
set -Eeuo pipefail
LOG="$1"
{
  printf '[%s] finalizer start\n' "$(date -Iseconds)"
  systemctl restart --no-block zeus-gateway.service atena-gateway.service ares-gateway.service
  sleep 35
  printf '[%s] services active\n' "$(date -Iseconds)"
  systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service cron.service || true
  printf '[%s] services show\n' "$(date -Iseconds)"
  systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
  printf '[%s] patch guard\n' "$(date -Iseconds)"
  /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh || true
  printf '[%s] version\n' "$(date -Iseconds)"
  hermes --version 2>&1 | sed -n '1,8p' || true
  printf '[%s] finalizer done\n' "$(date -Iseconds)"
} >> "$LOG" 2>&1
