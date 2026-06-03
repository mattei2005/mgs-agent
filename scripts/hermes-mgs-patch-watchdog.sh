#!/usr/bin/env bash
set -euo pipefail
LOG=/root/mgs-agent/logs/hermes-mgs-patch-watchdog.log
mkdir -p "$(dirname "$LOG")"
if /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh >> "$LOG" 2>&1; then
  exit 0
fi
rc=$?
echo "Hermes MGS patch guard failed (rc=$rc). Log: $LOG"
tail -40 "$LOG" || true
exit "$rc"
