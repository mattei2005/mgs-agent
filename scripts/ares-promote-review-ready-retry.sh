#!/usr/bin/env bash
set -euo pipefail
LOG="/root/mgs-agent/logs/ares-promote-review-ready-retry-20260615T035000Z.log"
QUEUE="/root/mgs-agent/data/ares/creative-inventory/final-organization-review/final-review-promote-to-ready-queue-20260615T031500Z.csv"
REPORT="/root/mgs-agent/data/ares/creative-inventory/final-organization-review/final-review-promote-to-ready-report-20260615T031500Z.csv"
mkdir -p "$(dirname "$LOG")"
# 1Password is currently rate-limiting this server. Retry slowly; once one read
# succeeds, the Python executor writes a chmod-600 OAuth cache and later Drive
# runs do not need to call 1Password for these client fields again.
for attempt in $(seq 1 16); do
  echo "[$(date -Is)] attempt=$attempt" >> "$LOG"
  if ARES_DRIVE_AUTH_MODE=oauth /root/mgs-agent/scripts/ares-promote-review-ready.py "$QUEUE" --report-csv "$REPORT" >> "$LOG" 2>&1; then
    echo "[$(date -Is)] promotion_done" >> "$LOG"
    exit 0
  fi
  rc=$?
  echo "[$(date -Is)] attempt_failed rc=$rc" >> "$LOG"
  sleep 1800
done
echo "[$(date -Is)] promotion_failed_after_retries" >> "$LOG"
exit 2
