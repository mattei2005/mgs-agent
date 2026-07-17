#!/usr/bin/env bash
set -euo pipefail

# Temporary noVNC session for logging Ares's persistent Chromium profile into YouTube.
# Security: binds VNC/noVNC to 127.0.0.1 only. Access via SSH tunnel; no public port.

DISPLAY_NUM="${ARES_YT_DISPLAY:-94}"
DISPLAY=":${DISPLAY_NUM}"
VNC_PORT="${ARES_YT_VNC_PORT:-5901}"
NOVNC_PORT="${ARES_YT_NOVNC_PORT:-6081}"
PROFILE_DIR="${ARES_YOUTUBE_PROFILE:-/root/.hermes/profiles/ares/browser-profiles/youtube-chromium}"
LOG_DIR="/root/mgs-agent/logs"
STOP_FILE="/tmp/ares-youtube-login-browser.stop"
PID_FILE="/tmp/ares-youtube-login-browser.pid"
mkdir -p "$LOG_DIR" "$PROFILE_DIR"
rm -f "$STOP_FILE"

if [[ "${1:-}" == "stop" ]]; then
  if [[ -f "$PID_FILE" ]]; then
    while read -r pid; do
      [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  pkill -f "Xvfb ${DISPLAY}" 2>/dev/null || true
  pkill -f "x11vnc .*${DISPLAY}" 2>/dev/null || true
  pkill -f "websockify .*${NOVNC_PORT}" 2>/dev/null || true
  touch "$STOP_FILE"
  echo "stopped"
  exit 0
fi

# Stop any stale instance first.
"$0" stop >/dev/null 2>&1 || true
rm -f "$STOP_FILE"

Xvfb "$DISPLAY" -screen 0 1365x900x24 -ac >"$LOG_DIR/ares-youtube-xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
x11vnc -display "$DISPLAY" -localhost -nopw -forever -shared -rfbport "$VNC_PORT" >"$LOG_DIR/ares-youtube-x11vnc.log" 2>&1 &
X11VNC_PID=$!
websockify --web=/usr/share/novnc/ "127.0.0.1:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" >"$LOG_DIR/ares-youtube-novnc.log" 2>&1 &
NOVNC_PID=$!

DISPLAY="$DISPLAY" PROFILE_DIR="$PROFILE_DIR" STOP_FILE="$STOP_FILE" python3 - <<'PY' >"/root/mgs-agent/logs/ares-youtube-login-browser.log" 2>&1 &
import os, time
from pathlib import Path
from playwright.sync_api import sync_playwright
profile=Path(os.environ['PROFILE_DIR']); profile.mkdir(parents=True, exist_ok=True)
stop=Path(os.environ['STOP_FILE'])
with sync_playwright() as p:
    ctx=p.chromium.launch_persistent_context(
        str(profile),
        headless=False,
        viewport={"width":1365,"height":900},
        locale="en-US",
        timezone_id="America/New_York",
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        args=["--disable-blink-features=AutomationControlled","--no-sandbox","--disable-dev-shm-usage"]
    )
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    page.goto('https://www.youtube.com/shorts/PCdygSACl_4', wait_until='domcontentloaded', timeout=60000)
    while not stop.exists():
        time.sleep(2)
    ctx.close()
PY
BROWSER_PID=$!

printf '%s\n%s\n%s\n%s\n' "$XVFB_PID" "$X11VNC_PID" "$NOVNC_PID" "$BROWSER_PID" > "$PID_FILE"

echo "started"
echo "novnc=http://127.0.0.1:${NOVNC_PORT}/vnc.html?host=127.0.0.1&port=${NOVNC_PORT}&autoconnect=true&resize=scale"
echo "profile=$PROFILE_DIR"
echo "stop=$0 stop"
