#!/usr/bin/env bash
# Daily closed-day Smart Bidding SMS revenue -> creditoparaveiculo WordPress.
set -euo pipefail
BASE=/root/mgs-agent
LOG="$BASE/logs/sync-sb-sms-revenue-daily.log"
mkdir -p "$BASE/logs" "$BASE/work"
exec >>"$LOG" 2>&1

set -a
# shellcheck source=/dev/null
source "$BASE/.env" 2>/dev/null || true
# shellcheck source=/dev/null
source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
set +a
export TZ=America/New_York
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

printf '[%s] sync-sb-sms-revenue-daily START args=%q\n' "$(date -Iseconds)" "$*"
set +e
xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python "$BASE/scripts/sync-sb-sms-revenue-daily.py" "$@"
rc=$?
set -e
printf '[%s] sync-sb-sms-revenue-daily END rc=%s\n' "$(date -Iseconds)" "$rc"
exit "$rc"
