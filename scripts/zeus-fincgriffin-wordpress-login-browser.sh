#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/root/mgs-agent"
DISPLAY_NUM="${FINCG_WP_DISPLAY:-96}"
DISPLAY_ADDR=":${DISPLAY_NUM}"
VNC_PORT="${FINCG_WP_VNC_PORT:-5904}"
NOVNC_PORT="${FINCG_WP_NOVNC_PORT:-6084}"
PROFILE_DIR="${FINCG_WP_PROFILE:-/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium}"
LOCK_FILE="/root/.hermes/profiles/zeus/browser-profiles/.fincgriffin-wordpress.lock"
LOG_DIR="/root/.hermes/profiles/zeus/logs"
ARTIFACT_DIR="/root/.hermes/profiles/zeus/artifacts"
TOOL_DIR="${BASE_DIR}/tools/fincgriffin-wordpress-browser"
STATUS_PATH="${ARTIFACT_DIR}/fincgriffin-wordpress-login-status.json"
URL="${1:-https://fincgriffin.com/wp-admin/}"

for command in Xvfb x11vnc websockify node flock fuser; do
  command -v "$command" >/dev/null 2>&1 || { echo "Dependência ausente: $command" >&2; exit 69; }
done

mkdir -p "$PROFILE_DIR" "$LOG_DIR" "$ARTIFACT_DIR" "$(dirname "$LOCK_FILE")"
chmod 700 "$PROFILE_DIR" "$LOG_DIR" "$ARTIFACT_DIR" "$(dirname "$LOCK_FILE")"

exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
  echo "O perfil Fincgriffin WordPress já está em uso." >&2
  exit 75
fi

cleanup_stale_listener() {
  local port="$1" expected="$2" pids pid comm
  pids="$(fuser "${port}/tcp" 2>/dev/null || true)"
  for pid in $pids; do
    comm="$(ps -p "$pid" -o comm= 2>/dev/null | xargs || true)"
    if [[ "$comm" == "$expected" ]]; then
      kill "$pid" 2>/dev/null || true
    else
      echo "Porta ${port} ocupada por processo inesperado (${comm:-desconhecido}, PID ${pid})." >&2
      exit 76
    fi
  done
}

cleanup_stale_listener "$VNC_PORT" x11vnc
cleanup_stale_listener "$NOVNC_PORT" websockify

cleanup() {
  set +e
  [[ -n "${BROWSER_PID:-}" ]] && kill -TERM "$BROWSER_PID" 2>/dev/null
  [[ -n "${X11VNC_PID:-}" ]] && kill "$X11VNC_PID" 2>/dev/null
  [[ -n "${NOVNC_PID:-}" ]] && kill "$NOVNC_PID" 2>/dev/null
  [[ -n "${XVFB_PID:-}" ]] && kill "$XVFB_PID" 2>/dev/null
  wait "${BROWSER_PID:-}" "${X11VNC_PID:-}" "${NOVNC_PID:-}" "${XVFB_PID:-}" 2>/dev/null
}
trap cleanup EXIT INT TERM

Xvfb "$DISPLAY_ADDR" -screen 0 1365x900x24 -ac >"$LOG_DIR/fincgriffin-wordpress-xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
x11vnc -display "$DISPLAY_ADDR" -localhost -nopw -forever -shared -rfbport "$VNC_PORT" >"$LOG_DIR/fincgriffin-wordpress-x11vnc.log" 2>&1 &
X11VNC_PID=$!
websockify --web=/usr/share/novnc/ "127.0.0.1:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" >"$LOG_DIR/fincgriffin-wordpress-novnc.log" 2>&1 &
NOVNC_PID=$!

sleep 1
kill -0 "$XVFB_PID" "$X11VNC_PID" "$NOVNC_PID"

export DISPLAY="$DISPLAY_ADDR"
export FINCG_WP_PROFILE="$PROFILE_DIR"
export FINCG_WP_STATUS="$STATUS_PATH"

printf 'READY novnc=127.0.0.1:%s profile=%s\n' "$NOVNC_PORT" "$PROFILE_DIR"
node "$TOOL_DIR/login-browser.js" "$URL" >"$LOG_DIR/fincgriffin-wordpress-browser.log" 2>&1 &
BROWSER_PID=$!
wait "$BROWSER_PID"
