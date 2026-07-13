#!/usr/bin/env bash
# dtr-sb-daily-match-audit.sh — auditoria diária read-only DTR x Dash SB.
set -euo pipefail
BASE_DIR=/root/mgs-agent
LOG="${BASE_DIR}/logs/dtr-sb-daily-match-audit-cron.log"
mkdir -p "${BASE_DIR}/logs" "${BASE_DIR}/reports" "${BASE_DIR}/data"
exec >> "$LOG" 2>&1

log() { printf '[%s] dtr-sb-daily-match-audit: %s\n' "$(TZ=America/New_York date -Iseconds)" "$*"; }

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

log "START args=$*"
cd "$BASE_DIR"
set +e
xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python "${BASE_DIR}/scripts/dtr-sb-daily-match-audit.py" "$@"
rc=$?
set -e
log "END rc=${rc}"
exit "$rc"
