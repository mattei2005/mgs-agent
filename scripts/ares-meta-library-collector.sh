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

export ARES_META_LIBRARY_PROFILE="${ARES_META_LIBRARY_PROFILE:-$PROFILE_DIR}"
export ARES_META_LIBRARY_OUTPUT="${ARES_META_LIBRARY_OUTPUT:-$OUTPUT_DIR}"

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
