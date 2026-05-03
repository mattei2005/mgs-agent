#!/bin/bash
# monitor-service-restarts.sh
# Detecta restarts inesperados de services Hermes e alerta em #alerts-infra
# Cron: */5 * * * *
# Thresholds: INFO >= 3, WARN >= 5 (dentro de 24h)
# Anti-spam: não realerta mesmo nível por 12h por service
set -euo pipefail

BASE_DIR="/root/mgs-agent"
STATE_FILE="${BASE_DIR}/data/service-restart-state.json"
LOG_PREFIX="[monitor-service-restarts]"

set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

# Buscar webhook do 1Password
WEBHOOK_URL=$(op item get 'Discord Webhook - Alerts Infra Channel' \
  --vault 'MGS Conteúdo' --fields label=webhook_url 2>/dev/null || true)

if [[ -z "${WEBHOOK_URL}" ]]; then
  echo "$(date -Iseconds) ${LOG_PREFIX} ERROR: webhook_url vazio (1P indisponível?)" >&2
  exit 1
fi

SERVICES=("zeus-gateway" "atena-gateway" "mgs-autocommit")
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

# Processar cada service
for SVC in "${SERVICES[@]}"; do
  # Obter NRestarts atual
  NRESTARTS_RAW=$(systemctl show "${SVC}.service" -p NRestarts 2>/dev/null || echo "NRestarts=0")
  CURRENT_N=$(echo "${NRESTARTS_RAW}" | cut -d= -f2)

  # Calcular delta e verificar thresholds via Python
  ALERT=$(python3 - <<PYEOF
import json, datetime, sys

STATE_FILE = "${STATE_FILE}"
SVC = "${SVC}"
CURRENT_N = int("${CURRENT_N}")
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
  print(f"{level}:{delta}")
else:
  print(f"ok:{delta}")
PYEOF
  )

  ALERT_LEVEL=$(echo "${ALERT}" | cut -d: -f1)
  DELTA=$(echo "${ALERT}" | cut -d: -f2)

  echo "$(date -Iseconds) ${LOG_PREFIX} ${SVC}: NRestarts=${CURRENT_N} delta=${DELTA} level=${ALERT_LEVEL}"

  if [[ "${ALERT_LEVEL}" == "info" ]]; then
    MSG="⚠️ [INFRA] [RESTART] \`${SVC}\` reiniciou ${DELTA}x nas últimas ${WINDOW_HOURS}h. Acompanhar."
    curl -s --max-time 15 -X POST "${WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"${MSG}\"}" > /dev/null
    echo "$(date -Iseconds) ${LOG_PREFIX} INFO alert enviado para ${SVC}"
  elif [[ "${ALERT_LEVEL}" == "warn" ]]; then
    MSG="🚨 [INFRA] [RESTART] \`${SVC}\` reiniciou ${DELTA}x nas últimas ${WINDOW_HOURS}h. Investigar urgente. <@344196393512075265>"
    curl -s --max-time 15 -X POST "${WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"${MSG}\"}" > /dev/null
    echo "$(date -Iseconds) ${LOG_PREFIX} WARN alert enviado para ${SVC}"
  fi
done

echo "$(date -Iseconds) ${LOG_PREFIX} OK"
