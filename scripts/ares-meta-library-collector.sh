#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/root/mgs-agent"
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a
TOOL_DIR="${BASE_DIR}/tools/meta-library-collector"
PROFILE_DIR="/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium"
OUTPUT_DIR="/root/.hermes/profiles/ares/artifacts/meta-library"
LOCK_FILE="/root/.hermes/profiles/ares/browser-profiles/.meta-library-collector.lock"
HEAVY_RUNNER="${BASE_DIR}/scripts/ares-meta-library-heavy-run.sh"

export ARES_META_LIBRARY_PROFILE="${ARES_META_LIBRARY_PROFILE:-$PROFILE_DIR}"
export ARES_META_LIBRARY_OUTPUT="${ARES_META_LIBRARY_OUTPUT:-$OUTPUT_DIR}"

# Only Meta Library work enters this queue. Campaign/direct-traffic/BOT
# executors do not call this wrapper and retain their independent parallel lanes.
if [[ "${ARES_META_LIBRARY_RESOURCE_GUARDED:-0}" != "1" ]]; then
  [[ -x "$HEAVY_RUNNER" ]] || {
    echo "Guard de recursos Meta Library ausente em ${HEAVY_RUNNER}" >&2
    exit 69
  }
  exec "$HEAVY_RUNNER" --label collector -- \
    env ARES_META_LIBRARY_RESOURCE_GUARDED=1 "$0" "$@"
fi

if [[ ! -f "${TOOL_DIR}/collector.js" || ! -f "${TOOL_DIR}/package.json" ]]; then
  echo "Runtime Meta Library ausente em ${TOOL_DIR}" >&2
  exit 1
fi

if [[ ! -d "${TOOL_DIR}/node_modules/playwright" ]]; then
  echo "Dependência Playwright ausente. Rode: cd ${TOOL_DIR} && npm ci" >&2
  exit 1
fi

mkdir -p "$ARES_META_LIBRARY_PROFILE" "$ARES_META_LIBRARY_OUTPUT" "$(dirname "$LOCK_FILE")"
chmod 700 "$ARES_META_LIBRARY_PROFILE" "$ARES_META_LIBRARY_OUTPUT"

exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
  echo "Coletor Meta Library já está usando o perfil persistente; tente novamente após a execução atual." >&2
  exit 75
fi

exec node "${TOOL_DIR}/collector.js" "$@"
