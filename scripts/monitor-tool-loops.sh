#!/bin/bash
# Detector de loops de tool_calls em sessions ativas
# Roda via cron a cada 5 minutos
# Alerta quando 5+ erros consecutivos da mesma tool
set -euo pipefail

THRESHOLD=5
COOLDOWN_MINUTES=30
STATE_FILE="/root/mgs-agent/data/tool-loops-state.json"
BASE_DIR="/root/mgs-agent"
DISCORD_CHANNEL_ID="1498132022634483894"
DISCORD_POSTER="${BASE_DIR}/scripts/discord-bot-post.py"

LOG_DIR="/var/log/mgs-agent"
FAILED_ALERTS_LOG="${LOG_DIR}/monitor-tool-loops-failed-alerts.log"
PENDING_ALERTS_DIR="${LOG_DIR}/pending-alerts"
EXIT_CODE=0

record_failed_alert() {
  local payload="$1" reason="$2"
  local ts file
  ts=$(date -Iseconds)
  mkdir -p "$PENDING_ALERTS_DIR" || return 2
  file="${PENDING_ALERTS_DIR}/monitor-tool-loops-$(date +%Y%m%d-%H%M%S)-$$.json"
  printf '%s reason=%s file=%s\n' "$ts" "$reason" "$file" >> "$FAILED_ALERTS_LOG" || return 2
  printf '%s\n' "$payload" > "$file" || return 2
  return 0
}

post_alert_payload() {
  local payload="$1" reason="${2:-alert}"
  if [[ "${MGS_DRY_RUN:-0}" == "1" ]]; then
    printf '%s' "$payload" | "$DISCORD_POSTER" --channel-id "$DISCORD_CHANNEL_ID" --dry-run >/dev/null
    echo "DRY_RUN: would post monitor-tool-loops alert via Zeus bot (${reason})"
    return 0
  fi
  if printf '%s' "$payload" | "$DISCORD_POSTER" --channel-id "$DISCORD_CHANNEL_ID" >/dev/null; then
    return 0
  fi
  record_failed_alert "$payload" "zeus_bot_failed:${reason}" || return 2
  return 2
}

# Garantir state válido
if [ ! -f "$STATE_FILE" ] || ! jq empty "$STATE_FILE" 2>/dev/null; then
  echo '{}' > "$STATE_FILE"
fi

NOW=$(date +%s)
COOLDOWN_SECONDS=$((COOLDOWN_MINUTES * 60))

ALERTS_SENT=0

# Percorrer sessions ativas (modificadas nos ultimos 10 min)
for AGENT in zeus atena; do
  SESSIONS_DIR="/root/.hermes/profiles/$AGENT/sessions"
  [ ! -d "$SESSIONS_DIR" ] && continue
  
  # Sessions modificadas nos ultimos 10 minutos
  while IFS= read -r SESSION_FILE; do
    [ -z "$SESSION_FILE" ] && continue
    
    SESSION_ID=$(basename "$SESSION_FILE" .jsonl)
    KEY="${AGENT}__${SESSION_ID}"
    
    # Analisar ultimos 30 turns: contar erros consecutivos por tool
    LOOP_DETECTED=$(python3 - "$SESSION_FILE" << 'PYTHON_END'
import sys, json
from collections import defaultdict

session_file = sys.argv[1]
try:
    with open(session_file, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()[-60:]
except OSError:
    lines = []
tool_calls = []  # lista de (tool_name, has_error)

for line in lines:
    try:
        entry = json.loads(line)
    except (json.JSONDecodeError, AttributeError, TypeError):
        continue
    
    role = entry.get("role", "")
    
    # Capturar tool_call (assistant chamando tool)
    if role == "assistant":
        content = entry.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append({"name": block.get("name", "unknown"), "id": block.get("id"), "error": None})
    
    # Capturar tool_result (resposta da tool)
    if role == "tool":
        tool_id = entry.get("tool_call_id", "")
        content = entry.get("content", "")
        # Detectar erro no resultado
        is_error = False
        if isinstance(content, str):
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    if result.get("error") or result.get("exit_code", 0) != 0:
                        is_error = True
                    if "error" in str(result.get("output", "")).lower()[:200]:
                        # heuristica fraca, mas vale
                        is_error = True
            except (json.JSONDecodeError, AttributeError, TypeError):
                if "error" in content.lower()[:200] or "exception" in content.lower()[:200]:
                    is_error = True
        
        # Marcar erro no tool_call correspondente
        for tc in reversed(tool_calls):
            if tc.get("id") == tool_id:
                tc["error"] = is_error
                break

# === DETECCAO 1: Erros consecutivos por tool (deteccao original) ===
consecutive_errors_by_tool = defaultdict(int)
streak_active = defaultdict(bool)

for tc in reversed(tool_calls):
    name = tc["name"]
    if tc.get("error") is True:
        if not streak_active.get(name + "_broken", False):
            consecutive_errors_by_tool[name] += 1
    elif tc.get("error") is False:
        streak_active[name + "_broken"] = True

# === DETECCAO 2: Frequencia de tool calls (mesmo sem erro) ===
# Loops do tipo MBNA: browser_navigate em sites bloqueados retorna HTTP 200
# (pagina Cloudflare challenge), monitor original nao detectava.
# Aqui contamos a FREQUENCIA total de cada tool nos ultimos 30 turns.
FREQUENCY_THRESHOLDS = {
    "browser_navigate": 15,    # >15 navigates em 30 turns = loop suspeito
    "browser_get_images": 15,
    "web_search": 10,
    "web_fetch": 15,
}
DEFAULT_FREQUENCY = 25  # Outras tools

frequency_by_tool = defaultdict(int)
for tc in tool_calls:
    frequency_by_tool[tc["name"]] += 1

# Identificar tools acima do threshold
high_frequency = {}
for tool_name, count in frequency_by_tool.items():
    threshold = FREQUENCY_THRESHOLDS.get(tool_name, DEFAULT_FREQUENCY)
    if count >= threshold:
        high_frequency[tool_name] = count

# === DECISAO: Reportar pior caso (erros consecutivos OU frequencia alta) ===
result_tool = "none"
result_count = 0
result_kind = "none"

if consecutive_errors_by_tool:
    max_err_tool = max(consecutive_errors_by_tool, key=consecutive_errors_by_tool.get)
    max_err_count = consecutive_errors_by_tool[max_err_tool]
    result_tool = max_err_tool
    result_count = max_err_count
    result_kind = "errors"

if high_frequency:
    max_freq_tool = max(high_frequency, key=high_frequency.get)
    max_freq_count = high_frequency[max_freq_tool]
    # Frequencia alta tem prioridade se for muito acima do threshold
    threshold = FREQUENCY_THRESHOLDS.get(max_freq_tool, DEFAULT_FREQUENCY)
    if max_freq_count >= threshold * 1.5 or result_kind == "none":
        result_tool = max_freq_tool
        result_count = max_freq_count
        result_kind = "frequency"

# Output: tool|count|kind (compatibilidade backward com bash)
print(f"{result_tool}|{result_count}|{result_kind}")
PYTHON_END
)
    
    TOOL_NAME=$(echo "$LOOP_DETECTED" | cut -d'|' -f1)
    ERROR_COUNT=$(echo "$LOOP_DETECTED" | cut -d'|' -f2)
    DETECTION_KIND=$(echo "$LOOP_DETECTED" | cut -d'|' -f3)
    
    [ "$TOOL_NAME" = "none" ] && continue
    [ -z "$ERROR_COUNT" ] && continue
    
    # Threshold dinamico: 5 pra erros, 1 pra frequencia (ja foi filtrado pelo Python)
    EFFECTIVE_THRESHOLD=$THRESHOLD
    if [ "$DETECTION_KIND" = "frequency" ]; then
      EFFECTIVE_THRESHOLD=1
    fi
    
    if [ "$ERROR_COUNT" -ge "$EFFECTIVE_THRESHOLD" ]; then
      # Verificar cooldown
      LAST_ALERT=$(jq -r --arg k "$KEY" '.[$k] // 0' "$STATE_FILE")
      ELAPSED=$((NOW - LAST_ALERT))
      
      if [ "$ELAPSED" -ge "$COOLDOWN_SECONDS" ]; then
        # Postar alerta
        TITLE="Agent em possível loop"
        if [ "$DETECTION_KIND" = "frequency" ]; then
          KIND_LABEL="Frequência alta sem erros"
        else
          KIND_LABEL="Erros consecutivos"
        fi
        
        PAYLOAD=$(jq -n \
          --arg c "<@344196393512075265> alerta de loop em agent" \
          --arg t "$TITLE" \
          --arg agent "$AGENT" \
          --arg session "$SESSION_ID" \
          --arg tool "$TOOL_NAME" \
          --arg kind "$KIND_LABEL" \
          --arg count "$ERROR_COUNT" \
          --argjson col 15158332 \
          '{content:$c, embeds:[{title:$t, color:$col, fields:[{name:"Agent", value:$agent, inline:true}, {name:"Session", value:("`"+$session+"`"), inline:true}, {name:"Tool", value:("`"+$tool+"`"), inline:true}, {name:"Tipo", value:$kind, inline:true}, {name:"Contagem", value:$count, inline:true}, {name:"Ação", value:"Mandar mensagem ao agent para parar ou reorientar.", inline:false}]}]}')
        
        if post_alert_payload "$PAYLOAD" "${AGENT}/${SESSION_ID}/${TOOL_NAME}"; then
          # Atualizar state apenas após envio ou dry-run bem-sucedido
          jq --arg k "$KEY" --argjson n "$NOW" '. + {($k): $n}' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
          ALERTS_SENT=$((ALERTS_SENT + 1))
          echo "ALERT: $AGENT/$SESSION_ID - $TOOL_NAME ($ERROR_COUNT erros)"
        else
          EXIT_CODE=2
          echo "FAILED_ALERT: $AGENT/$SESSION_ID - $TOOL_NAME ($ERROR_COUNT erros)" >&2
        fi
      else
        REMAINING=$(( (COOLDOWN_SECONDS - ELAPSED) / 60 ))
        echo "COOLDOWN: $AGENT/$SESSION_ID - aguarda ${REMAINING}min"
      fi
    fi
  done < <(find "$SESSIONS_DIR" -maxdepth 1 -name "*.jsonl" -mmin -10 -type f)
done

if [[ "${MGS_FORCE_TOOL_LOOP_ALERT:-0}" == "1" ]]; then
  PAYLOAD=$(jq -n \
    --arg c "<@344196393512075265> alerta de loop em agent" \
    '{content:$c, embeds:[{title:"Agent em possível loop", color:15158332, fields:[{name:"Agent", value:"synthetic", inline:true}, {name:"Session", value:"`synthetic-test`", inline:true}, {name:"Tool", value:"`synthetic_tool`", inline:true}, {name:"Tipo", value:"Teste sintético", inline:true}, {name:"Contagem", value:"5", inline:true}, {name:"Ação", value:"Teste local do caminho de alerta.", inline:false}]}]}')
  if post_alert_payload "$PAYLOAD" "synthetic"; then
    ALERTS_SENT=$((ALERTS_SENT + 1))
    echo "ALERT: synthetic/tool-loops"
  else
    EXIT_CODE=2
    echo "FAILED_ALERT: synthetic/tool-loops" >&2
  fi
fi

echo "Loop detector: $ALERTS_SENT alertas enviados"
exit "$EXIT_CODE"
