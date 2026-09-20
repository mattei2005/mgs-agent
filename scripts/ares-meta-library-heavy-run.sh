#!/usr/bin/env bash
# Serialize and resource-isolate Ares Meta Library/background-heavy work.
# Deliberately NOT used by campaign creation, direct-traffic or BOT lanes.
set -euo pipefail

LOCK_FILE="${ARES_META_LIBRARY_HEAVY_LOCK_FILE:-/run/lock/mgs-ares-meta-library-heavy.lock}"
LOCK_TIMEOUT="${ARES_META_LIBRARY_HEAVY_LOCK_TIMEOUT:-7200}"
CPU_QUOTA="${ARES_META_LIBRARY_HEAVY_CPU_QUOTA:-180%}"
MEMORY_HIGH="${ARES_META_LIBRARY_HEAVY_MEMORY_HIGH:-5G}"
NICE_LEVEL="${ARES_META_LIBRARY_HEAVY_NICE:-10}"
IO_PRIORITY="${ARES_META_LIBRARY_HEAVY_IO_PRIORITY:-7}"
SYSTEMD_RUN="${ARES_META_LIBRARY_HEAVY_SYSTEMD_RUN:-/usr/bin/systemd-run}"
LABEL="job"

usage() {
  cat <<'EOF'
Usage: ares-meta-library-heavy-run.sh [--label NAME] -- COMMAND [ARG...]

Queues only Meta Library/reference collection, country scans, browser-heavy
quality checks and their packaging. Campaign creation must never use this
wrapper.
EOF
}

while (($#)); do
  case "$1" in
    --label)
      (($# >= 2)) || { echo "--label requires a value" >&2; exit 64; }
      LABEL="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

(($#)) || { echo "Missing command after --" >&2; usage >&2; exit 64; }
[[ "$LABEL" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,47}$ ]] || {
  echo "Invalid label: use 1-48 characters from [A-Za-z0-9_.-]" >&2
  exit 64
}
[[ "$LOCK_TIMEOUT" =~ ^[0-9]+$ ]] || { echo "Invalid lock timeout" >&2; exit 64; }
[[ "$CPU_QUOTA" =~ ^[0-9]+%$ ]] || { echo "Invalid CPU quota" >&2; exit 64; }
[[ "$MEMORY_HIGH" =~ ^[0-9]+[KMGT]$|^infinity$ ]] || { echo "Invalid MemoryHigh" >&2; exit 64; }
[[ "$NICE_LEVEL" =~ ^-?[0-9]+$ ]] || { echo "Invalid nice level" >&2; exit 64; }
[[ "$IO_PRIORITY" =~ ^[0-7]$ ]] || { echo "Invalid IO priority" >&2; exit 64; }
[[ -x "$SYSTEMD_RUN" ]] || { echo "systemd-run unavailable: $SYSTEMD_RUN" >&2; exit 69; }

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"

queued_at=$(date +%s)
echo "META_LIBRARY_QUEUE waiting label=$LABEL" >&2
if ! flock -w "$LOCK_TIMEOUT" 9; then
  echo "META_LIBRARY_QUEUE timeout label=$LABEL waited=${LOCK_TIMEOUT}s" >&2
  exit 75
fi
waited=$(( $(date +%s) - queued_at ))
unit="ares-meta-library-${LABEL//[^a-zA-Z0-9_.-]/-}-$(date +%s)-$$"
echo "META_LIBRARY_QUEUE acquired label=$LABEL waited=${waited}s unit=$unit" >&2

set +e
"$SYSTEMD_RUN" \
  --quiet \
  --wait \
  --pipe \
  --collect \
  --service-type=exec \
  --unit="$unit" \
  --working-directory="$PWD" \
  --property="CPUQuota=$CPU_QUOTA" \
  --property="MemoryHigh=$MEMORY_HIGH" \
  --property="Nice=$NICE_LEVEL" \
  --property=IOSchedulingClass=best-effort \
  --property="IOSchedulingPriority=$IO_PRIORITY" \
  --property=CPUAccounting=yes \
  --property=MemoryAccounting=yes \
  -- "$@"
rc=$?
set -e

echo "META_LIBRARY_QUEUE finished label=$LABEL rc=$rc" >&2
exit "$rc"
