#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
LOG="/root/mgs-agent/logs/restart-all-gateways-notify-20260705T060036Z.log"
THREAD_ID="1523205067396747394"
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
json_escape(){ python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])'; }
post_discord(){
  local msg="$1" token=""
  set -a
  source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
  source /root/mgs-agent/.env 2>/dev/null || true
  set +a
  token="${DISCORD_BOT_TOKEN:-${ZEUS_DISCORD_BOT_TOKEN:-}}"
  if [[ -z "$token" ]]; then log "WARN no discord token available; cannot notify"; return 0; fi
  local payload http
  payload=$(jq -n --arg content "$msg" '{content:$content, allowed_mentions:{parse:[]}}')
  http=$(curl -sS -o /tmp/restart-notify-discord.response -w '%{http_code}' \
    -X POST "https://discord.com/api/v10/channels/'"$THREAD_ID"'/messages" \
    -H "Authorization: Bot $token" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    --max-time 15 || true)
  log "discord_notify_http=$http"
  if [[ "$http" != "200" && "$http" != "201" ]]; then cat /tmp/restart-notify-discord.response || true; fi
}
status_line(){
  for a in atena ares hera zeus; do
    printf '%s=%s ' "$a" "$(systemctl is-active ${a}-gateway.service 2>/dev/null || true)"
  done
}
log "START restart all gateways with notify"
printf '{"ts":"%s","event":"gateway_restart_requested","actor":"zeus","requester":"Rodolfo Mattei","reason":"Rodolfo pediu reiniciar todos os agentes e avisar quando ativos","log":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LOG" >> "$BASE/logs/events-audit.jsonl"
log "before $(status_line)"
for a in atena ares hera; do
  log "restart ${a}-gateway.service"
  systemctl restart "${a}-gateway.service"
done
log "restart zeus-gateway.service last --no-block"
systemctl restart --no-block zeus-gateway.service
# Poll externally; this process is not the Zeus gateway.
deadline=$((SECONDS+180))
while (( SECONDS < deadline )); do
  all=1
  for a in atena ares hera zeus; do
    [[ "$(systemctl is-active ${a}-gateway.service 2>/dev/null || true)" == "active" ]] || all=0
  done
  log "poll $(status_line)"
  (( all == 1 )) && break
  sleep 5
done
states="$(status_line)"
log "final $states"
if [[ "$states" == *"atena=active"* && "$states" == *"ares=active"* && "$states" == *"hera=active"* && "$states" == *"zeus=active"* ]]; then
  post_discord "Gateways reiniciados e ativos novamente: Zeus/Atena/Ares/Hera. Log: $LOG"
  event="gateway_restart_completed_all_active"
else
  post_discord "Restart executado, mas nem todos voltaram active: $states Log: $LOG"
  event="gateway_restart_completed_with_warning"
fi
printf '{"ts":"%s","event":"%s","actor":"restart-all-gateways-notify","detail":"%s","log":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$event" "$states" "$LOG" >> "$BASE/logs/events-audit.jsonl"
log "DONE"
