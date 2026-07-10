#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/root/mgs-agent"
TOOL_DIR="${BASE_DIR}/tools/meta-library-collector"
PROFILE_DIR="/root/.hermes/profiles/hera/browser-profiles/meta-library-chromium"
OUTPUT_DIR="/root/.hermes/profiles/hera/artifacts/meta-library"

set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

export HERA_META_LIBRARY_PROFILE="${HERA_META_LIBRARY_PROFILE:-$PROFILE_DIR}"
export HERA_META_LIBRARY_OUTPUT="${HERA_META_LIBRARY_OUTPUT:-$OUTPUT_DIR}"

if [[ ! -f "${TOOL_DIR}/collector.js" || ! -f "${TOOL_DIR}/package.json" ]]; then
  echo "Runtime Meta Library ausente em ${TOOL_DIR}" >&2
  exit 1
fi

if [[ ! -d "${TOOL_DIR}/node_modules/playwright" ]]; then
  echo "Dependência Playwright ausente. Rode: cd ${TOOL_DIR} && npm ci" >&2
  exit 1
fi

mkdir -p "$HERA_META_LIBRARY_PROFILE" "$HERA_META_LIBRARY_OUTPUT"
chmod 700 "$HERA_META_LIBRARY_PROFILE" "$HERA_META_LIBRARY_OUTPUT"

exec node "${TOOL_DIR}/collector.js" "$@"
