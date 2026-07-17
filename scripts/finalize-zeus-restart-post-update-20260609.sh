#!/usr/bin/env bash
set -euo pipefail
THREAD_ID="1513546246055268585"
LOG="/root/mgs-agent/logs/hermes-zeus-restart-finalizer-20260609-$(date +%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
log(){ printf '[%s] %s\n' "$(date -Is)" "$*"; }
send_report(){
  local body="$1"
  set +u; set -a; source /root/.hermes/profiles/zeus/.env 2>/dev/null || true; set +a; set -u
  [[ -n "${DISCORD_BOT_TOKEN:-}" ]] || return 0
  python3 - "$THREAD_ID" "$body" <<'PY'
import json, os, sys, urllib.request
thread_id, body = sys.argv[1:3]
token = os.environ.get('DISCORD_BOT_TOKEN','')
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{thread_id}/messages",
    method="POST",
    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent":"Hermes-Agent"},
    data=json.dumps({"content": body[:1900]}, ensure_ascii=False).encode(),
)
urllib.request.urlopen(req, timeout=15).read()
PY
}
log "START zeus finalizer"
sleep 6
state=$(systemctl show zeus-gateway.service -p ActiveState --value || true)
sub=$(systemctl show zeus-gateway.service -p SubState --value || true)
log "zeus pre state=$state sub=$sub"
if [[ "$state:$sub" == "deactivating:stop-sigterm" || "$state" == "deactivating" ]]; then
  log "Zeus stuck deactivating; killing old service cgroup"
  systemctl kill -s KILL zeus-gateway.service || true
  sleep 3
fi
systemctl reset-failed zeus-gateway.service || true
systemctl start zeus-gateway.service
sleep 18
log "SERVICE STATUS"
systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager
repo=/root/.hermes/hermes-agent
head=$(git -C "$repo" rev-parse --short HEAD)
origin=$(git -C "$repo" rev-parse --short origin/main)
behind=$(git -C "$repo" rev-list --count HEAD..origin/main)
services=$(systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service | paste -sd ',')
if [[ "$services" == "active,active,active,active" ]]; then
  status="✅ Hermes update finalizado"
else
  status="⚠️ Hermes update com pendência"
fi
body="$status

\`\`\`text
HEAD: $head
origin/main: $origin
behind: $behind
Serviços: $services
Backup: /root/hermes-profiles-backup-20260609-091938.tar.gz
Logs:
- /root/mgs-agent/logs/hermes-update-controlled-20260609-092231.log
- $LOG
\`\`\`
Observação: Zeus precisou de finalizer externo porque o processo antigo ficou preso em deactivating durante o restart da própria sessão."
send_report "$body" || true
log "DONE"
