#!/usr/bin/env bash
set -euo pipefail

THREAD_ID="1513546246055268585"
BASE="/root/mgs-agent"
REPO="/root/.hermes/hermes-agent"
LOG="$BASE/logs/post-reboot-health-20260609-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

log(){ printf '[%s] %s\n' "$(date -Is)" "$*"; }

send_report(){
  local title="$1"
  local body="$2"
  set +u
  set -a
  source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
  set +a
  set -u
  [[ -n "${DISCORD_BOT_TOKEN:-}" ]] || { log "WARN missing DISCORD_BOT_TOKEN; cannot post report"; return 0; }
  python3 - "$THREAD_ID" "$title" "$body" <<'PY'
import json, os, sys, urllib.request
thread_id, title, body = sys.argv[1:4]
token = os.environ.get('DISCORD_BOT_TOKEN', '')
content = f"{title}\n\n{body}"[:1900]
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{thread_id}/messages",
    method="POST",
    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "Hermes-Agent"},
    data=json.dumps({"content": content}, ensure_ascii=False).encode(),
)
urllib.request.urlopen(req, timeout=20).read()
PY
}

cleanup_unit(){
  systemctl disable mgs-post-reboot-health-20260609.service >/dev/null 2>&1 || true
  rm -f /etc/systemd/system/mgs-post-reboot-health-20260609.service
  systemctl daemon-reload >/dev/null 2>&1 || true
}
trap cleanup_unit EXIT

log "START post reboot health"
# Give network/gateways a little time after boot.
sleep 45

services_raw="$(systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service cron 2>&1 || true)"
services_csv="$(printf '%s\n' "$services_raw" | paste -sd ',')"
log "services=$services_csv"

# Allow a second service settle window if any agent is not active yet.
if [[ "$services_csv" != "active,active,active,active,active" ]]; then
  sleep 30
  services_raw="$(systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service cron 2>&1 || true)"
  services_csv="$(printf '%s\n' "$services_raw" | paste -sd ',')"
  log "services_after_wait=$services_csv"
fi

hermes_version="$(hermes --version 2>&1 | sed -n '1p' || true)"
node_version="$(node -v 2>/dev/null || true)"
npm_version="$(npm -v 2>/dev/null || true)"
codex_version="$(npx --yes @openai/codex --version 2>/dev/null || true)"
corepack_version="$(corepack --version 2>/dev/null || true)"
head="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || true)"
origin="$(git -C "$REPO" rev-parse --short origin/main 2>/dev/null || true)"
behind="$(git -C "$REPO" rev-list --count HEAD..origin/main 2>/dev/null || true)"
reboot_required="no"
if [[ -f /var/run/reboot-required ]]; then reboot_required="yes"; fi
kernel="$(uname -r)"
boot_time="$(uptime -s 2>/dev/null || true)"
disk="$(df -h / | awk 'NR==2{print $4 " livres / " $5 " usado"}')"
cron_summary="$(tail -1 /root/mgs-agent/logs/monitor-cron-stale-logs.log 2>/dev/null | cut -c1-180 || true)"
oauth_summary="$(tail -1 /root/mgs-agent/logs/sync-codex-oauth.log 2>/dev/null | cut -c1-180 || true)"

patch_status="FAIL"
if /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh >/tmp/post-reboot-patch-guard.log 2>&1; then
  patch_status="OK"
fi
cat /tmp/post-reboot-patch-guard.log || true

py_status="FAIL"
py="$REPO/venv/bin/python"; [[ -x "$py" ]] || py=python3
if "$py" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/config.py" \
  "$REPO/tools/send_message_tool.py" \
  "$REPO/tools/discord_tool.py"; then
  py_status="OK"
fi

if [[ "$services_csv" == "active,active,active,active,active" && "$patch_status" == "OK" && "$py_status" == "OK" && "$reboot_required" == "no" ]]; then
  title="✅ Reboot VPS concluído e validado"
else
  title="⚠️ Reboot VPS concluído com pendência"
fi

body="\`\`\`text
Boot: $boot_time
Kernel: $kernel
Reboot required: $reboot_required
Serviços zeus/atena/ares/autocommit/cron: $services_csv
Hermes: $hermes_version
HEAD/origin/behind: $head / $origin / $behind
Node/npm/Codex/Corepack: $node_version / $npm_version / $codex_version / $corepack_version
Patch guard: $patch_status
py_compile: $py_status
Disco: $disk
Cron stale: ${cron_summary:-sem linha}
OAuth sync: ${oauth_summary:-sem linha}
Log: $LOG
\`\`\`"

send_report "$title" "$body" || true
log "DONE"
