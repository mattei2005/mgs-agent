#!/bin/bash
# Detector de loops de tool_calls em sessions ativas
# Roda via cron a cada 5 minutos
# Alerta quando 5+ erros consecutivos da mesma tool
set -e

THRESHOLD=5
COOLDOWN_MINUTES=30
STATE_FILE="/root/mgs-agent/data/tool-loops-state.json"

set -a
source /root/mgs-agent/.env
set +a

# Buscar webhook (com retry)
WEBHOOK=""
for i in 1 2 3; do
  WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=webhook_url --reveal 2>/dev/null)
  if [[ "$WEBHOOK" == https://* ]]; then
    break
  fi
  sleep 3
done

if [[ "$WEBHOOK" != https://* ]]; then
  echo "ERROR: Webhook unavailable" >&2
  exit 1
fi

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
    LOOP_DETECTED=$(tail -60 "$SESSION_FILE" 2>/dev/null | python3 << 'PYTHON_END'
import sys, json
from collections import defaultdict

lines = sys.stdin.readlines()
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
        TITLE="🔴 [LOOP DETECTADO] ${AGENT^} em loop"
        if [ "$DETECTION_KIND" = "frequency" ]; then
          KIND_LABEL="Frequencia alta (sem erros)"
        else
          KIND_LABEL="Erros consecutivos"
        fi
        DESC=$(printf "**Agent:** %s\n**Session:** %s\n**Tool:** \`%s\`\n**Tipo:** %s\n**Contagem:** %s\n**Sugestão:** mandar mensagem ao agent pra parar ou orientar" "$AGENT" "$SESSION_ID" "$TOOL_NAME" "$KIND_LABEL" "$ERROR_COUNT")
        
        PAYLOAD=$(jq -n \
          --arg c "<@344196393512075265> verificar agent" \
          --arg t "$TITLE" \
          --arg d "$DESC" \
          --argjson col 15158332 \
          '{content: $c, embeds: [{title: $t, description: $d, color: $col}]}')
        
        curl -s -X POST -H "Content-Type: application/json" \
          -d "$PAYLOAD" "$WEBHOOK" > /dev/null
        
        # Atualizar state
        jq --arg k "$KEY" --argjson n "$NOW" '. + {($k): $n}' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
        
        ALERTS_SENT=$((ALERTS_SENT + 1))
        echo "ALERT: $AGENT/$SESSION_ID - $TOOL_NAME ($ERROR_COUNT erros)"
      else
        REMAINING=$(( (COOLDOWN_SECONDS - ELAPSED) / 60 ))
        echo "COOLDOWN: $AGENT/$SESSION_ID - aguarda ${REMAINING}min"
      fi
    fi
  done < <(find "$SESSIONS_DIR" -maxdepth 1 -name "*.jsonl" -mmin -10 -type f)
done

echo "Loop detector: $ALERTS_SENT alertas enviados"
