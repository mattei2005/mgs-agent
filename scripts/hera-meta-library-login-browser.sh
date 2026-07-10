#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${HERA_META_DISPLAY:-95}"
DISPLAY_ADDR=":${DISPLAY_NUM}"
VNC_PORT="${HERA_META_VNC_PORT:-5903}"
NOVNC_PORT="${HERA_META_NOVNC_PORT:-6083}"
PROFILE_DIR="${HERA_META_LIBRARY_PROFILE:-/root/.hermes/profiles/hera/browser-profiles/meta-library-chromium}"
LOCK_FILE="/root/.hermes/profiles/hera/browser-profiles/.meta-library-collector.lock"
LOG_DIR="/root/.hermes/profiles/hera/logs"
TOOL_DIR="/root/mgs-agent/tools/meta-library-collector"
URL="${1:-https://www.facebook.com/ads/library/}"

mkdir -p "$PROFILE_DIR" "$LOG_DIR" "$(dirname "$LOCK_FILE")"
chmod 700 "$PROFILE_DIR" "$LOG_DIR"

exec 9>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
  echo "O perfil Meta Library já está em uso por outro browser/coletor." >&2
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
      echo "Porta ${port} ocupada por processo inesperado (${comm:-desconhecido}, PID ${pid}); sessão visual não iniciada." >&2
      exit 76
    fi
  done
}

# Se uma sessão anterior morreu sem executar o trap, limpe apenas listeners
# conhecidos. O lock já foi adquirido, então não há sessão canônica ativa.
cleanup_stale_listener "$VNC_PORT" x11vnc
cleanup_stale_listener "$NOVNC_PORT" websockify
sleep 1

cleanup() {
  set +e
  [[ -n "${X11VNC_PID:-}" ]] && kill "$X11VNC_PID" 2>/dev/null
  [[ -n "${NOVNC_PID:-}" ]] && kill "$NOVNC_PID" 2>/dev/null
  [[ -n "${XVFB_PID:-}" ]] && kill "$XVFB_PID" 2>/dev/null
  wait "${X11VNC_PID:-}" "${NOVNC_PID:-}" "${XVFB_PID:-}" 2>/dev/null
}
trap cleanup EXIT INT TERM

Xvfb "$DISPLAY_ADDR" -screen 0 1365x900x24 -ac >"$LOG_DIR/meta-library-login-xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
x11vnc -display "$DISPLAY_ADDR" -localhost -nopw -forever -shared -rfbport "$VNC_PORT" >"$LOG_DIR/meta-library-login-x11vnc.log" 2>&1 &
X11VNC_PID=$!
websockify --web=/usr/share/novnc/ "127.0.0.1:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" >"$LOG_DIR/meta-library-login-novnc.log" 2>&1 &
NOVNC_PID=$!

export DISPLAY="$DISPLAY_ADDR"
export HERA_META_LIBRARY_PROFILE="$PROFILE_DIR"

echo "READY novnc=127.0.0.1:${NOVNC_PORT} profile=${PROFILE_DIR}"
node "$TOOL_DIR/login-browser.js" "$URL"
