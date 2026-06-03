#!/usr/bin/env bash
# monitor-webshare-status.sh — alerta #alerts-infra quando status.webshare.io entra em manutenção
# Cron: */10 * * * *
# Estado: /root/mgs-agent/data/webshare-status-state.json
# Log: /root/mgs-agent/logs/monitor-webshare-status.log
set -euo pipefail

BASE_DIR="/root/mgs-agent"
STATE_FILE="${BASE_DIR}/data/webshare-status-state.json"
STATUS_URL="https://status.webshare.io/"
FAILED_ALERTS_LOG="/var/log/mgs-agent/monitor-webshare-status-failed-alerts.log"
PENDING_ALERTS_DIR="/var/log/mgs-agent/pending-alerts"
WEBHOOK_URL=""
WEBHOOK_FETCHED=0

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

log() {
  echo "[$(date -Iseconds)] monitor-webshare-status: $*"
}

record_failed_alert() {
  local payload="$1" reason="$2" ts file
  ts=$(date -Iseconds)
  mkdir -p "$PENDING_ALERTS_DIR" || return 2
  file="${PENDING_ALERTS_DIR}/monitor-webshare-status-$(date +%Y%m%d-%H%M%S)-$$.json"
  printf '%s reason=%s file=%s\n' "$ts" "$reason" "$file" >> "$FAILED_ALERTS_LOG" || return 2
  printf '%s\n' "$payload" > "$file" || return 2
  return 0
}

fetch_webhook_once() {
  if [[ "$WEBHOOK_FETCHED" == "1" ]]; then
    [[ "$WEBHOOK_URL" == https://* ]]
    return $?
  fi
  WEBHOOK_FETCHED=1
  if [[ -n "${MGS_WEBHOOK_URL_OVERRIDE:-}" ]]; then
    WEBHOOK_URL="$MGS_WEBHOOK_URL_OVERRIDE"
  else
    WEBHOOK_URL=$(op item get 'Discord Webhook - Alerts Infra Channel' --vault 'MGS Conteúdo' --fields label=webhook_url --reveal 2>/dev/null || true)
  fi
  [[ "$WEBHOOK_URL" == https://* ]]
}

post_alert_payload() {
  local payload="$1" reason="${2:-alert}" http_status attempt
  if ! fetch_webhook_once; then
    record_failed_alert "$payload" "op_unavailable:${reason}" || return 2
    return 2
  fi
  if [[ "${MGS_DRY_RUN:-0}" == "1" ]]; then
    log "DRY_RUN: would post Discord alert (${reason})"
    return 0
  fi
  for attempt in 1 2; do
    http_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -X POST -H "Content-Type: application/json" -d "$payload" "$WEBHOOK_URL" 2>/dev/null || echo "000")
    if [[ "$http_status" =~ ^2 ]]; then
      return 0
    fi
    sleep 2
  done
  record_failed_alert "$payload" "curl_failed:${reason}:http=${http_status}" || return 2
  return 2
}

mkdir -p "$(dirname "$STATE_FILE")"
if [[ ! -f "$STATE_FILE" ]]; then
  jq -n --arg ts "$(date -Iseconds)" '{_meta:{description:"Estado do monitor Webshare status page", created:$ts, url:"https://status.webshare.io/"}, last_check:null, last_mode:"unknown", active_since:null, last_alert_sent:null, last_resolution_sent:null, last_summary:null}' > "$STATE_FILE"
fi

log "START check url=${STATUS_URL}"
TMP_HTML=$(mktemp)
TMP_RESULT=$(mktemp)
cleanup() { rm -f "$TMP_HTML" "$TMP_RESULT"; }
trap cleanup EXIT

HTTP_CODE=$(curl -sSL --max-time 25 -A 'MGS-Infra-Monitor/1.0' -o "$TMP_HTML" -w '%{http_code}' "$STATUS_URL" || echo "000")
if [[ ! "$HTTP_CODE" =~ ^2 ]]; then
  log "ERROR fetch_failed http=${HTTP_CODE}"
  exit 1
fi

python3 - "$TMP_HTML" > "$TMP_RESULT" <<'PY'
import html, json, re, sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text(errors="ignore")
# Next/React flight payload carries JSON-like data escaped inside the HTML.
text = html.unescape(raw).replace('\\"', '"').replace('\\/', '/')

status_values = {"operational", "under_maintenance", "degraded_performance", "partial_outage", "full_outage"}

# Components are listed once with id/name and status appears separately in affected_components/component_impacts.
id_to_name = {}
for m in re.finditer(r'\{[^{}]{0,700}"id":"([^"]+)"[^{}]{0,700}"name":"([^"]+)"[^{}]{0,700}"status_page_id"', text):
    id_to_name[m.group(1)] = m.group(2)

component_status = {}
for m in re.finditer(r'"component_id":"([^"]+)"[^{}]{0,500}"(?:current_status|status)":"([a-z_]+)"', text):
    cid, status = m.group(1), m.group(2)
    if status in status_values:
        # Prefer the most severe/latest observed status over operational.
        old = component_status.get(cid)
        priority = {"operational": 0, "degraded_performance": 1, "partial_outage": 2, "full_outage": 3, "under_maintenance": 4}
        if old is None or priority.get(status, 0) >= priority.get(old, 0):
            component_status[cid] = status

components = []
for cid, status in component_status.items():
    components.append({"name": id_to_name.get(cid, cid), "status": status})
components.sort(key=lambda c: c["name"])

maintenance_components = [c for c in components if c["status"] == "under_maintenance"]
maintenance_status_hits = bool(re.search(r'"status":"maintenance_in_progress"', text))
scheduled_nonempty = bool(re.search(r'"scheduled_maintenances":\s*\[\s*\{', text))

mode = "maintenance" if maintenance_components or maintenance_status_hits else "normal"
if maintenance_components:
    reason = "component_under_maintenance"
elif maintenance_status_hits:
    reason = "maintenance_in_progress"
elif scheduled_nonempty:
    reason = "scheduled_maintenance_present_not_in_progress"
else:
    reason = "no_active_maintenance"

# Keep summary short for Discord/logs.
summary_components = components[:8]
print(json.dumps({
    "mode": mode,
    "reason": reason,
    "components": summary_components,
    "maintenance_components": maintenance_components[:8],
    "scheduled_maintenance_present": scheduled_nonempty,
}, ensure_ascii=False))
PY

RESULT_JSON=$(cat "$TMP_RESULT")
MODE=$(jq -r '.mode' <<< "$RESULT_JSON")
REASON=$(jq -r '.reason' <<< "$RESULT_JSON")
LAST_MODE=$(jq -r '.last_mode // "unknown"' "$STATE_FILE")
NOW_ISO=$(date -Iseconds)

log "STATUS mode=${MODE} reason=${REASON} previous=${LAST_MODE}"

# Persistir state antes da ação externa para evitar loop de alerta em caso de falha de webhook.
if [[ "$MODE" == "maintenance" ]]; then
  ACTIVE_SINCE=$(jq -r --arg now "$NOW_ISO" '.active_since // $now' "$STATE_FILE")
  jq --arg ts "$NOW_ISO" --arg mode "$MODE" --arg active "$ACTIVE_SINCE" --argjson summary "$RESULT_JSON" \
    '.last_check=$ts | .last_mode=$mode | .active_since=$active | .last_summary=$summary' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if [[ "$LAST_MODE" != "maintenance" ]]; then
    COMPONENT_FIELD=$(jq -r '[.maintenance_components[]? | "• " + .name + " — " + .status] | if length == 0 then "Status page marcou manutenção em andamento, sem componente extraído." else join("\n") end' <<< "$RESULT_JSON")
    PAYLOAD=$(jq -n \
      --arg url "$STATUS_URL" \
      --arg reason "$REASON" \
      --arg components "$COMPONENT_FIELD" \
      --arg checked "$NOW_ISO" \
      '{content:"<@344196393512075265> Webshare em manutenção", embeds:[{title:"Webshare status em manutenção", color:15844367, fields:[{name:"Status page", value:$url, inline:false}, {name:"Motivo detectado", value:("`"+$reason+"`"), inline:true}, {name:"Checado em", value:$checked, inline:true}, {name:"Componentes", value:("```text\n"+$components[:900]+"\n```"), inline:false}, {name:"Impacto operacional", value:"Evitar iniciar jobs dependentes de proxy até normalizar.", inline:false}]}]}')
    if post_alert_payload "$PAYLOAD" "maintenance-start"; then
      jq --arg ts "$NOW_ISO" '.last_alert_sent=$ts' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      log "ALERT sent maintenance-start"
    else
      log "FAILED_ALERT maintenance-start"
      exit 2
    fi
  fi
else
  jq --arg ts "$NOW_ISO" --arg mode "$MODE" --argjson summary "$RESULT_JSON" \
    '.last_check=$ts | .last_mode=$mode | .active_since=null | .last_summary=$summary' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if [[ "$LAST_MODE" == "maintenance" ]]; then
    PAYLOAD=$(jq -n \
      --arg url "$STATUS_URL" \
      --arg checked "$NOW_ISO" \
      '{content:"", embeds:[{title:"Webshare status normalizado", color:3066993, fields:[{name:"Status page", value:$url, inline:false}, {name:"Checado em", value:$checked, inline:true}, {name:"Estado", value:"Sem manutenção ativa detectada.", inline:false}]}]}')
    if post_alert_payload "$PAYLOAD" "maintenance-resolved"; then
      jq --arg ts "$NOW_ISO" '.last_resolution_sent=$ts' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      log "RESOLVED sent maintenance-resolved"
    else
      log "FAILED_ALERT maintenance-resolved"
      exit 2
    fi
  fi
fi

log "OK completed mode=${MODE}"
