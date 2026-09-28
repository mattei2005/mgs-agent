#!/usr/bin/env bash
# Daily actual SMS Funnel send cost -> creditoparaveiculo WordPress.
set -euo pipefail
BASE=/root/mgs-agent
LOG="$BASE/logs/sync-smsfunnel-cost-daily.log"
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

printf '[%s] sync-smsfunnel-cost-daily START args=%q\n' "$(date -Iseconds)" "$*"
max_attempts="${MGS_SMS_COST_RETRY_ATTEMPTS:-2}"
retry_delay_seconds="${MGS_SMS_COST_RETRY_DELAY_SECONDS:-300}"
if ! [[ "$max_attempts" =~ ^[1-9][0-9]*$ && "$retry_delay_seconds" =~ ^[0-9]+$ ]]; then
  printf '[%s] invalid retry configuration attempts=%q delay=%q\n' "$(date -Iseconds)" "$max_attempts" "$retry_delay_seconds"
  exit 2
fi

python_bin="${MGS_SMS_COST_PYTHON_BIN:-/usr/bin/python3}"
sync_script="${MGS_SMS_COST_SCRIPT_PATH:-$BASE/scripts/sync-smsfunnel-cost-daily.py}"
attempt=1
rc=1
while (( attempt <= max_attempts )); do
  printf '[%s] sync-smsfunnel-cost-daily ATTEMPT %s/%s\n' "$(date -Iseconds)" "$attempt" "$max_attempts"
  set +e
  "$python_bin" "$sync_script" "$@"
  rc=$?
  set -e
  if (( rc == 0 || attempt == max_attempts )); then
    break
  fi
  printf '[%s] sync-smsfunnel-cost-daily RETRY_SCHEDULED after=%ss previous_rc=%s\n' "$(date -Iseconds)" "$retry_delay_seconds" "$rc"
  sleep "$retry_delay_seconds"
  ((attempt += 1))
done
printf '[%s] sync-smsfunnel-cost-daily END rc=%s attempts=%s\n' "$(date -Iseconds)" "$rc" "$attempt"
exit "$rc"
