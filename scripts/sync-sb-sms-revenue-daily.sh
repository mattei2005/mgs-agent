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

max_attempts="${MGS_SB_RETRY_ATTEMPTS:-2}"
retry_delay_seconds="${MGS_SB_RETRY_DELAY_SECONDS:-300}"
if ! [[ "$max_attempts" =~ ^[1-9][0-9]*$ && "$retry_delay_seconds" =~ ^[0-9]+$ ]]; then
  printf '[%s] invalid retry configuration attempts=%q delay=%q\n' "$(date -Iseconds)" "$max_attempts" "$retry_delay_seconds"
  exit 2
fi

python_bin="${MGS_SB_PYTHON_BIN:-/root/.local/share/mgs/sb-venv/bin/python}"
sync_script="${MGS_SB_SCRIPT_PATH:-$BASE/scripts/sync-sb-sms-revenue-daily.py}"
original_args=("$@")
has_no_alert=0
for arg in "${original_args[@]}"; do
  [[ "$arg" == "--no-alert" ]] && has_no_alert=1
done

attempt=1
rc=1
while (( attempt <= max_attempts )); do
  call_args=("${original_args[@]}")
  if (( attempt < max_attempts && has_no_alert == 0 )); then
    call_args+=(--defer-retryable-alert)
  fi
  printf '[%s] sync-sb-sms-revenue-daily ATTEMPT %s/%s\n' "$(date -Iseconds)" "$attempt" "$max_attempts"
  set +e
  xvfb-run -a "$python_bin" "$sync_script" "${call_args[@]}"
  rc=$?
  set -e
  if (( rc == 0 || rc != 75 || attempt == max_attempts )); then
    break
  fi
  printf '[%s] sync-sb-sms-revenue-daily RETRY_SCHEDULED after=%ss previous_rc=%s\n' "$(date -Iseconds)" "$retry_delay_seconds" "$rc"
  sleep "$retry_delay_seconds"
  ((attempt += 1))
done

printf '[%s] sync-sb-sms-revenue-daily END rc=%s attempts=%s\n' "$(date -Iseconds)" "$rc" "$attempt"
exit "$rc"
