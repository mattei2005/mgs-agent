#!/bin/bash
# monitor-service-restarts.sh
# Detecta restarts inesperados de services Hermes e alerta em #alerts-infra
# Cron: */5 * * * *
# Thresholds: INFO >= 3, WARN >= 5 (dentro de 24h)
# Anti-spam: não realerta mesmo nível por 12h por service
set -euo pipefail

BASE_DIR="/root/mgs-agent"
STATE_FILE="${MGS_SERVICE_RESTART_STATE_FILE:-${BASE_DIR}/data/service-restart-state.json}"
LOG_PREFIX="[monitor-service-restarts]"

set -a
# Token do bot Zeus local; o monitor não depende mais do 1Password/webhook.
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a

LOG_DIR="${MGS_SERVICE_RESTART_LOG_DIR:-/var/log/mgs-agent}"
FAILED_ALERTS_LOG="${LOG_DIR}/monitor-service-restarts-failed-alerts.log"
PENDING_ALERTS_DIR="${LOG_DIR}/pending-alerts"
DISCORD_CHANNEL_ID="${MGS_DISCORD_CHANNEL_ID_OVERRIDE:-1498132022634483894}"
DISCORD_API_URL="${MGS_DISCORD_API_URL_OVERRIDE:-https://discord.com/api/v10/channels/${DISCORD_CHANNEL_ID}/messages}"
BOT_TOKEN="${MGS_DISCORD_BOT_TOKEN_OVERRIDE:-${DISCORD_BOT_TOKEN:-}}"
EXIT_CODE=0

record_failed_alert() {
  local payload="$1" reason="$2"
  local ts file
  ts=$(date -Iseconds)
  mkdir -p "$PENDING_ALERTS_DIR" || return 2
  file="${PENDING_ALERTS_DIR}/monitor-service-restarts-$(date +%Y%m%d-%H%M%S)-$$.json"
  printf '%s reason=%s file=%s\n' "$ts" "$reason" "$file" >> "$FAILED_ALERTS_LOG" || return 2
  printf '%s\n' "$payload" > "$file" || return 2
  return 0
}

post_alert_payload() {
  local payload="$1" reason="${2:-alert}" http_status attempt
  if [[ "${MGS_FORCE_DISCORD_AUTH_FAIL:-0}" == "1" ]]; then
    record_failed_alert "$payload" "discord_auth_forced:${reason}" || return 2
    return 2
  fi
  if [[ -z "$BOT_TOKEN" ]]; then
    record_failed_alert "$payload" "discord_bot_token_missing:${reason}" || return 2
    return 2
  fi
  if [[ "${MGS_DRY_RUN:-0}" == "1" ]]; then
    echo "$(date -Iseconds) ${LOG_PREFIX} DRY_RUN: would post bot alert channel=${DISCORD_CHANNEL_ID} (${reason})"
    return 0
  fi
  for attempt in 1 2; do
    http_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
      -X POST \
      -H "Authorization: Bot ${BOT_TOKEN}" \
      -H "Content-Type: application/json" \
      -H "User-Agent: MGS-Zeus/1.0" \
      -d "$payload" \
      "$DISCORD_API_URL" 2>/dev/null || echo "000")
    if [[ "$http_status" =~ ^2 ]]; then
      return 0
    fi
    sleep 2
  done
  record_failed_alert "$payload" "discord_api_failed:${reason}:http=${http_status}" || return 2
  return 2
}

infer_restart_cause() {
  local svc="$1" current_start="$2" epoch start end window
  epoch=$(date -d "$current_start" +%s 2>/dev/null || true)
  if [[ -z "$epoch" ]]; then
    printf 'Causa não identificada automaticamente: timestamp do start não parseável.'
    return 0
  fi
  start=$(date -d "@$((epoch - 120))" '+%Y-%m-%d %H:%M:%S')
  end=$(date -d "@$((epoch + 60))" '+%Y-%m-%d %H:%M:%S')
  window=$(journalctl --since "$start" --until "$end" --no-pager -o short-iso 2>/dev/null | grep -Ei 'monarx|apt-get install|needrestart|systemctl|Stopping .*gateway|Started .*gateway' | head -80 || true)
  if grep -Eiq 'monarx-agent|monarx-update|apt-get install.*monarx' <<<"$window"; then
    printf 'Monarx weekly package update (/etc/cron.d/monarx-update) detectado na janela do restart. Classificar como manutenção conhecida se ocorrer terça 04:20 EDT.'
    return 0
  fi
  if grep -Eiq 'needrestart|apt-get|unattended-upgrade|packagekit' <<<"$window"; then
    printf 'Atualização de pacote/needrestart detectada na janela; validar se era manutenção planejada.'
    return 0
  fi
  printf 'Causa não identificada automaticamente; investigar journal do serviço e eventos do sistema.'
}

SERVICES=("zeus-gateway" "atena-gateway" "ares-gateway" "hera-gateway" "mgs-autocommit")
THRESHOLD_INFO=3
THRESHOLD_WARN=5
ANTI_SPAM_HOURS=12
WINDOW_HOURS=24
NOW=$(date +%s)

# Inicializar state file se não existir
if [[ ! -f "${STATE_FILE}" ]]; then
  echo "$(date -Iseconds) ${LOG_PREFIX} State file ausente — inicializando..."
  python3 - <<PYEOF
import json, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
state = {
  "_meta": {
    "description": "Estado do monitor service-restart-watcher",
    "created": now,
    "thresholds": {"info": ${THRESHOLD_INFO}, "warn": ${THRESHOLD_WARN}},
    "window_hours": ${WINDOW_HOURS},
    "anti_spam_hours": ${ANTI_SPAM_HOURS}
  },
  "services": {}
}
for svc in ["zeus-gateway", "atena-gateway", "mgs-autocommit"]:
  state["services"][svc] = {
    "baseline_nrestarts": 0,
    "baseline_timestamp": now,
    "window_start": now,
    "last_alert_sent": None,
    "last_alert_level": None
  }
with open("${STATE_FILE}", "w") as f:
  json.dump(state, f, indent=2)
print("State file criado.")
PYEOF
fi

RESTART_EVENTS_FILE="$(mktemp)"
trap 'rm -f "$RESTART_EVENTS_FILE"' EXIT

# Processar cada service
for SVC in "${SERVICES[@]}"; do
  # Obter NRestarts atual e timestamp real do último start ativo
  NRESTARTS_RAW=$(systemctl show "${SVC}.service" -p NRestarts 2>/dev/null || echo "NRestarts=0")
  CURRENT_N=$(echo "${NRESTARTS_RAW}" | cut -d= -f2)
  ACTIVE_ENTER_RAW=$(systemctl show "${SVC}.service" -p ActiveEnterTimestamp --value 2>/dev/null || true)

  # Calcular delta, verificar thresholds e detectar restart limpo/manual via ActiveEnterTimestamp
  ALERT=$(python3 - <<PYEOF
import json, datetime, sys

STATE_FILE = "${STATE_FILE}"
SVC = "${SVC}"
CURRENT_N = int("${CURRENT_N}")
CURRENT_ACTIVE_ENTER = """${ACTIVE_ENTER_RAW}""".strip()
THRESHOLD_INFO = ${THRESHOLD_INFO}
THRESHOLD_WARN = ${THRESHOLD_WARN}
ANTI_SPAM_HOURS = ${ANTI_SPAM_HOURS}
WINDOW_HOURS = ${WINDOW_HOURS}
NOW_TS = ${NOW}

with open(STATE_FILE) as f:
  state = json.load(f)

svc_state = state["services"].get(SVC, {
  "baseline_nrestarts": 0,
  "baseline_timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
  "window_start": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
  "last_alert_sent": None,
  "last_alert_level": None
})

previous_active_enter = svc_state.get("last_active_enter_timestamp")
restart_changed = bool(previous_active_enter and CURRENT_ACTIVE_ENTER and previous_active_enter != CURRENT_ACTIVE_ENTER)
restart_previous = previous_active_enter or "baseline_initialized"
if CURRENT_ACTIVE_ENTER:
  svc_state["last_active_enter_timestamp"] = CURRENT_ACTIVE_ENTER
  if restart_changed:
    svc_state["last_restart_detected_at"] = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

baseline = svc_state.get("baseline_nrestarts", 0)
window_start_str = svc_state.get("window_start", datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z")
window_start = datetime.datetime.fromisoformat(window_start_str.replace("Z",""))
window_age_hours = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - window_start).total_seconds() / 3600

# Reset janela de 24h
if window_age_hours >= WINDOW_HOURS:
  baseline = CURRENT_N
  window_start = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
  svc_state["baseline_nrestarts"] = baseline
  svc_state["baseline_timestamp"] = window_start.isoformat() + "Z"
  svc_state["window_start"] = window_start.isoformat() + "Z"

delta = max(0, CURRENT_N - baseline)

# Determinar nível de alerta
level = None
if delta >= THRESHOLD_WARN:
  level = "warn"
elif delta >= THRESHOLD_INFO:
  level = "info"

alert_needed = False
if level:
  last_alert_str = svc_state.get("last_alert_sent")
  last_level = svc_state.get("last_alert_level")
  if last_alert_str and last_level == level:
    last_alert_dt = datetime.datetime.fromisoformat(last_alert_str.replace("Z",""))
    hours_since = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - last_alert_dt).total_seconds() / 3600
    if hours_since < ANTI_SPAM_HOURS:
      level = None  # anti-spam ativo

if level:
  alert_needed = True
  svc_state["last_alert_sent"] = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
  svc_state["last_alert_level"] = level

# Atualizar state
state["services"][SVC] = svc_state
with open(STATE_FILE, "w") as f:
  json.dump(state, f, indent=2)

if alert_needed:
  print(f"{level}|{delta}|{int(restart_changed)}|{restart_previous}|{CURRENT_ACTIVE_ENTER}")
else:
  print(f"ok|{delta}|{int(restart_changed)}|{restart_previous}|{CURRENT_ACTIVE_ENTER}")
PYEOF
  )

  ALERT_LEVEL=$(echo "${ALERT}" | cut -d'|' -f1)
  DELTA=$(echo "${ALERT}" | cut -d'|' -f2)
  RESTART_CHANGED=$(echo "${ALERT}" | cut -d'|' -f3)
  RESTART_PREVIOUS=$(echo "${ALERT}" | cut -d'|' -f4)
  RESTART_CURRENT=$(echo "${ALERT}" | cut -d'|' -f5-)

  echo "$(date -Iseconds) ${LOG_PREFIX} ${SVC}: NRestarts=${CURRENT_N} delta=${DELTA} level=${ALERT_LEVEL} active_enter_changed=${RESTART_CHANGED}"

  if [[ "${ALERT_LEVEL}" == "info" ]]; then
    PAYLOAD=$(jq -n \
      --arg svc "${SVC}" \
      --arg delta "${DELTA}x" \
      --arg window "${WINDOW_HOURS}h" \
      '{content:"", embeds:[{title:"Service reiniciando acima do normal", color:15844367, fields:[{name:"Service", value:("`"+$svc+"`"), inline:true}, {name:"Reinícios", value:$delta, inline:true}, {name:"Janela", value:$window, inline:true}, {name:"Ação", value:"Acompanhar; investigar se subir para WARN.", inline:false}]}]}')
    if post_alert_payload "$PAYLOAD" "${SVC}:info"; then
      echo "$(date -Iseconds) ${LOG_PREFIX} INFO alert enviado para ${SVC}"
    else
      EXIT_CODE=2
      echo "$(date -Iseconds) ${LOG_PREFIX} FAILED_ALERT INFO para ${SVC}" >&2
    fi
  elif [[ "${ALERT_LEVEL}" == "warn" ]]; then
    PAYLOAD=$(jq -n \
      --arg svc "${SVC}" \
      --arg delta "${DELTA}x" \
      --arg window "${WINDOW_HOURS}h" \
      '{content:"", embeds:[{title:"Service reiniciando em excesso", color:15158332, fields:[{name:"Service", value:("`"+$svc+"`"), inline:true}, {name:"Reinícios", value:$delta, inline:true}, {name:"Janela", value:$window, inline:true}, {name:"Ação", value:"Investigar logs e causa do restart.", inline:false}]}]}')
    if post_alert_payload "$PAYLOAD" "${SVC}:warn"; then
      echo "$(date -Iseconds) ${LOG_PREFIX} WARN alert enviado para ${SVC}"
    else
      EXIT_CODE=2
      echo "$(date -Iseconds) ${LOG_PREFIX} FAILED_ALERT WARN para ${SVC}" >&2
    fi
  fi

  if [[ "${RESTART_CHANGED}" == "1" ]]; then
    RESTART_CAUSE=$(infer_restart_cause "${SVC}" "${RESTART_CURRENT}")
    if [[ "${RESTART_CAUSE}" == Monarx* ]]; then
      RESTART_ACTION="Manutenção conhecida detectada. Validar se ficou restrita à janela esperada; investigar apenas se repetir fora da terça 04:20 EDT ou gerar loop."
    else
      RESTART_ACTION="Restart detectado por ActiveEnterTimestamp. Verificar se foi planejado; se não, investigar journal do serviço."
    fi
    jq -nc \
      --arg svc "${SVC}" \
      --arg curr "${RESTART_CURRENT}" \
      --arg cause "${RESTART_CAUSE}" \
      --arg action "${RESTART_ACTION}" \
      '{service:$svc,current:$curr,cause:$cause,action:$action}' >> "$RESTART_EVENTS_FILE"
    echo "$(date -Iseconds) ${LOG_PREFIX} RESTART queued para ${SVC} cause=${RESTART_CAUSE}"
  fi
done

if [[ -s "$RESTART_EVENTS_FILE" ]]; then
  COUNT_RESTARTS=$(wc -l < "$RESTART_EVENTS_FILE" | tr -d ' ')
  RESTART_FIELDS=$(python3 - "$RESTART_EVENTS_FILE" "$COUNT_RESTARTS" <<'PY'
import json
import sys

path = sys.argv[1]
count = sys.argv[2]
fields = [
    {"name": "Serviços afetados", "value": str(count), "inline": True},
    {"name": "Formato", "value": "Resumo por serviço; sem tabela quebrada no mobile.", "inline": True},
]
for line in open(path, encoding='utf-8'):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    svc = (r.get('service') or 'service')[:80]
    current = (r.get('current') or 'desconhecido').replace(' EDT', ' EDT')
    cause = ' '.join((r.get('cause') or 'Causa não identificada automaticamente.').split())
    action = ' '.join((r.get('action') or 'Verificar se foi planejado; se não, investigar journal.').split())
    if len(cause) > 170:
        cause = cause[:167] + '...'
    if len(action) > 150:
        action = action[:147] + '...'
    value = f"Start: `{current}`\nCausa: {cause}\nAção: {action}"
    fields.append({"name": svc, "value": value[:1000], "inline": False})
fields.append({
    "name": "Decisão operacional",
    "value": "Investigar só se não foi manutenção planejada ou se repetir. Mensagem agrupada e silenciosa.",
    "inline": False,
})
print(json.dumps(fields, ensure_ascii=False))
PY
  )
  PAYLOAD=$(jq -n \
    --argjson fields "$RESTART_FIELDS" \
    '{content:"", embeds:[{title:"Restarts de serviços detectados", color:3447003, fields:$fields}]}')
  if post_alert_payload "$PAYLOAD" "service-restarts:active_enter_batch"; then
    echo "$(date -Iseconds) ${LOG_PREFIX} RESTART batch alert enviado count=${COUNT_RESTARTS}"
  else
    EXIT_CODE=2
    echo "$(date -Iseconds) ${LOG_PREFIX} FAILED_ALERT RESTART batch" >&2
  fi
fi

if [[ "${MGS_FORCE_SERVICE_RESTART_ALERT:-0}" == "1" ]]; then
  PAYLOAD=$(jq -n \
    --arg c "" \
    '{content:$c, embeds:[{title:"Service reiniciando em excesso", color:15158332, fields:[{name:"Service", value:"`synthetic-service`", inline:true}, {name:"Reinícios", value:"5x", inline:true}, {name:"Janela", value:"24h", inline:true}, {name:"Ação", value:"Teste local do caminho de alerta.", inline:false}]}]}')
  if post_alert_payload "$PAYLOAD" "synthetic"; then
    echo "$(date -Iseconds) ${LOG_PREFIX} WARN alert enviado para synthetic-service"
  else
    EXIT_CODE=2
    echo "$(date -Iseconds) ${LOG_PREFIX} FAILED_ALERT WARN para synthetic-service" >&2
  fi
fi

echo "$(date -Iseconds) ${LOG_PREFIX} OK"
exit "$EXIT_CODE"
