#!/usr/bin/env bash
# dtr-sb-restricted-sync.sh — aplica DTR #2022 em SmartBidding RESTRICTED_UNTIL
set -euo pipefail

BASE_DIR=/root/mgs-agent
PY=/root/mgs-agent/scripts/dtr-sb-restricted-sync.py
LOG=/root/mgs-agent/logs/dtr-sb-restricted-sync.log

mkdir -p "$(dirname "$LOG")" "${BASE_DIR}/data"

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

export TZ=America/New_York
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

echo "[$(date -Iseconds)] dtr-sb-restricted-sync.sh START args=$*" >> "$LOG"

if [[ ! -x /tmp/sb-venv/bin/python ]]; then
  echo "[$(date -Iseconds)] ERROR /tmp/sb-venv/bin/python não encontrado" >> "$LOG"
  exit 1
fi

xvfb-run -a /tmp/sb-venv/bin/python "$PY" "$@" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}

echo "[$(date -Iseconds)] dtr-sb-restricted-sync.sh END rc=$rc" >> "$LOG"
exit "$rc"
