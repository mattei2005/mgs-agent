#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR="${FINCG_WP_PROFILE:-/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium}"
LOCK_FILE="/root/.hermes/profiles/zeus/browser-profiles/.fincgriffin-wordpress.lock"
TOOL_DIR="/root/mgs-agent/tools/fincgriffin-wordpress-browser"
ARTIFACT_DIR="/root/.hermes/profiles/zeus/artifacts"

mkdir -p "$PROFILE_DIR" "$ARTIFACT_DIR" "$(dirname "$LOCK_FILE")"
chmod 700 "$PROFILE_DIR" "$ARTIFACT_DIR" "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
  echo "O perfil Fincgriffin WordPress está em uso pela sessão visual." >&2
  exit 75
fi

export FINCG_WP_PROFILE="$PROFILE_DIR"
export FINCG_WP_PROBE_STATUS="${ARTIFACT_DIR}/fincgriffin-wordpress-probe-status.json"
node "$TOOL_DIR/probe.js"
