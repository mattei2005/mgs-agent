#!/usr/bin/env bash
set -euo pipefail
BASE_DIR=/root/mgs-agent
LOG_DIR="${BASE_DIR}/logs"
PAUSE_FLAG="${BASE_DIR}/data/utility-canary-loop.paused"
LOCK_FILE=/tmp/utility-canary-3h-runner.lock
LOG_FILE="${LOG_DIR}/utility-canary-3h-runner-$(date +%Y%m%d-%H%M%S).log"
INTERVAL_SECONDS=${INTERVAL_SECONDS:-600}
MAX_SECONDS=${MAX_SECONDS:-21600}

mkdir -p "$LOG_DIR" "${BASE_DIR}/data"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -Is) runner already active" >> "$LOG_FILE"
  exit 0
fi

set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a
cd "$BASE_DIR"

rm -f "$PAUSE_FLAG"
start_epoch=$(date +%s)
deadline=$((start_epoch + MAX_SECONDS))

echo "$(date -Is) Utility canary 3h runner started interval=${INTERVAL_SECONDS}s max=${MAX_SECONDS}s" >> "$LOG_FILE"

while [ "$(date +%s)" -lt "$deadline" ]; do
  cycle_ts=$(date +%Y%m%d-%H%M%S)
  cycle_log="${LOG_DIR}/utility-canary-cycle-${cycle_ts}.log"
  echo "$(date -Is) cycle start" >> "$LOG_FILE"

  # The loop script itself has the duplicate-visible-TEXT guard and blocks bad POSTs.
  if "${BASE_DIR}/scripts/utility-canary-approval-loop.sh" > "$cycle_log" 2>&1; then
    cat "$cycle_log" >> "$LOG_FILE"
    if grep -q 'TODOS VERDES' "$cycle_log"; then
      echo "$(date -Is) all green detected; pausing runner early" >> "$LOG_FILE"
      printf 'Paused %s: all canary templates reached 20/20 green before 3h deadline. Log: %s\n' "$(date -Is)" "$LOG_FILE" > "$PAUSE_FLAG"
      exit 0
    fi
  else
    rc=$?
    echo "$(date -Is) cycle failed rc=${rc}; see ${cycle_log}" >> "$LOG_FILE"
    cat "$cycle_log" >> "$LOG_FILE" || true
  fi

  now=$(date +%s)
  next=$((now + INTERVAL_SECONDS))
  if [ "$next" -ge "$deadline" ]; then
    break
  fi
  sleep "$INTERVAL_SECONDS"
done

printf 'Paused %s: 3h Utility canary runner deadline reached. Log: %s\n' "$(date -Is)" "$LOG_FILE" > "$PAUSE_FLAG"
echo "$(date -Is) deadline reached; runner paused" >> "$LOG_FILE"
