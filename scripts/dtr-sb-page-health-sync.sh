#!/usr/bin/env bash
# dtr-sb-page-health-sync.sh — corrected DTR page-by-page -> SB sync
set -euo pipefail
BASE_DIR=/root/mgs-agent
PY=${BASE_DIR}/scripts/dtr-sb-page-health-sync.py
LOG=${BASE_DIR}/logs/dtr-sb-page-health-sync.log
mkdir -p "$(dirname "$LOG")" "${BASE_DIR}/data" "${BASE_DIR}/reports"

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

export TZ=America/New_York
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

echo "[$(date -Iseconds)] dtr-sb-page-health-sync.sh START args=$*" >> "$LOG"
if [[ ! -x /tmp/sb-venv/bin/python ]]; then
  echo "[$(date -Iseconds)] ERROR /tmp/sb-venv/bin/python não encontrado" >> "$LOG"
  exit 1
fi
xvfb-run -a /tmp/sb-venv/bin/python "$PY" "$@" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "[$(date -Iseconds)] dtr-sb-page-health-sync.sh END rc=$rc" >> "$LOG"
exit "$rc"
