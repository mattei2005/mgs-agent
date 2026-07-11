#!/usr/bin/env bash
# monitor-sb-restricted-pages.sh — alerta dedicado de páginas Messenger restritas na SB
# Canal: 1522442220903337984
set -euo pipefail

BASE_DIR=/root/mgs-agent
LOG=/root/mgs-agent/logs/monitor-sb-restricted-pages.log
PY=/root/mgs-agent/scripts/monitor-sb-restricted-pages.py

mkdir -p "$(dirname "$LOG")" "${BASE_DIR}/data"

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

export TZ=America/New_York
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

echo "[$(date -Iseconds)] monitor-sb-restricted-pages.sh START args=$*"

if [[ ! -x /root/.local/share/mgs/sb-venv/bin/python ]]; then
  echo "[$(date -Iseconds)] ERROR /root/.local/share/mgs/sb-venv/bin/python não encontrado" >&2
  exit 1
fi

xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python "$PY" "$@"
rc=$?

echo "[$(date -Iseconds)] monitor-sb-restricted-pages.sh END rc=$rc"
exit "$rc"
