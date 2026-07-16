## Convenção de canal Discord por tipo de alerta

| Tipo de alerta | Canal | Webhook 1Password |
|---|---|---|
| Saúde Yoast SEO/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| Capacidade USER/MEMORY >=90% + proposta de compactação | `#limites-90` (1527401973698007060) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| REPORT-INFRA / cobrança operacional ao Zeus | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**Layout obrigatório das mensagens:** usar Discord embed com `fields` estruturados — nunca mandar alerta como texto bruto em `content`, exceto a mention necessária para push.
- `content`: vazio para info/resolução; `<@344196393512075265> alerta curto` apenas quando precisa push.
- `embeds[0].title`: título humano curto, sem prefixo poluído.
- `embeds[0].color`: vermelho `15158332`, amarelo `15844367`, verde `3066993`, azul/info `3447003`.
- `embeds[0].fields`: dados separados por assunto (`Service`, `Estado`, `Ação`, `Detalhe técnico`, etc.).
- Detalhes longos vão em campo `Detalhe técnico` com bloco ```text, truncado se necessário.
- Resoluções usam embed verde simples.

Exemplo mínimo:
```bash
PAYLOAD=$(jq -n \
  --arg service "$SERVICE" \
  --arg detail "$DETAIL" \
  '{content:"<@344196393512075265> alerta de infra", embeds:[{title:"Service com falha", color:15158332, fields:[{name:"Service", value:("`"+$service+"`"), inline:true}, {name:"Ação", value:"Investigar log e reiniciar se necessário.", inline:false}, {name:"Detalhe técnico", value:("```text\n"+$detail[:900]+"\n```"), inline:false}]}]}')
```

**NÃO usar** o webhook `#alerts-infra` para alertas de cron/monitor automatizado. Esse canal é exclusivo para conversa operacional Rodolfo ↔ Zeus e hook git de commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

---
## Estrutura do sistema

```
scripts/monitor-NOME.sh          — script principal
data/NOME-monitor.json           — state file (persiste entre execuções)
logs/monitor-NOME.log            — output do cron
crontab root                     — entrada cron (frequência ajustável)
```

---
## State file inicial

```json
{
  "_meta": {
    "description": "Estado do monitor de NOME. Atualizado a cada execução.",
    "created": "YYYY-MM-DD",
    "threshold": 3,
    "anti_spam_window_hours": 2
  },
  "last_check": null,
  "consecutive_failures": 0,
  "last_alert_sent": null,
  "last_failure_details": []
}
```

---
## Template do script monitor

Copiar e adaptar — variáveis marcadas com `ALTERAR`:

```bash
#!/usr/bin/env bash
# monitor-NOME.sh — Monitor de falhas em PROCESSO
# Roda via cron. State em data/NOME-monitor.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PUSH_LOG="${BASE_DIR}/logs/NOME-DO-LOG.log"          # ALTERAR
STATE_FILE="${BASE_DIR}/data/NOME-monitor.json"       # ALTERAR
WINDOW_MINUTES="${WINDOW_MINUTES:-60}"
THRESHOLD="${THRESHOLD:-3}"
ANTI_SPAM_HOURS="${ANTI_SPAM_HOURS:-2}"

source "${BASE_DIR}/.env" 2>/dev/null || true

WEBHOOK_URL="$(op item get "Discord Webhook - MGS Alerts Channel" \
    --vault 'MGS Conteúdo' \
    --fields label=webhook_url \
    --reveal 2>/dev/null)"

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_EPOCH="$(date +%s)"
CUTOFF_EPOCH=$(( NOW_EPOCH - WINDOW_MINUTES * 60 ))

log() { echo "[$(date -Iseconds)] monitor-NOME: $*"; }

# ─── Garantir state file ──────────────────────────────────────────────────────
if [[ ! -f "$STATE_FILE" ]]; then
  cat > "$STATE_FILE" <<'EOF'
{"_meta":{},"last_check":null,"consecutive_failures":0,"last_alert_sent":null,"last_failure_details":[]}
EOF
fi

CONSECUTIVE=$(jq -r '.consecutive_failures // 0' "$STATE_FILE")
LAST_ALERT=$(jq -r '.last_alert_sent // "null"' "$STATE_FILE")

# ─── Verificar log existe ─────────────────────────────────────────────────────
if [[ ! -f "$PUSH_LOG" ]]; then
  log "WARN: log não encontrado"
  jq --arg ts "$NOW_ISO" '.last_check = $ts' "$STATE_FILE" > "${STATE_FILE}.tmp" \
    && mv "${STATE_FILE}.tmp" "$STATE_FILE"
  exit 0
fi

# ─── Filtrar janela de tempo ──────────────────────────────────────────────────
WINDOW_LINES=""
while IFS= read -r line; do
  ts="$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}')" || continue
  line_epoch="$(date -d "$ts" +%s 2>/dev/null)" || continue
  if (( line_epoch >= CUTOFF_EPOCH )); then
    WINDOW_LINES+="$line"$'\n'
  fi
done < "$PUSH_LOG"

# ─── Detectar falhas (ALTERAR padrões de START/OK) ───────────────────────────
NEW_FAILURES=()
LAST_OK_COMMIT=""
LAST_OK_TS=""

while IFS= read -r line; do
  if echo "$line" | grep -q "PROCESSO START"; then              # ALTERAR
    id="$(echo "$line" | grep -oP 'id=\K\S+')" || continue
    ts="$(echo "$line" | grep -oP '\[\K[^\]]+')" || continue
    if ! grep -q "PROCESSO OK id=${id}" "$PUSH_LOG"; then       # ALTERAR
      NEW_FAILURES+=("${ts} id=${id} [START sem OK]")
    fi
  fi
done <<< "$WINDOW_LINES"

# ─── Detectar erros explícitos ────────────────────────────────────────────────
ERROR_PATTERNS="rejected|failed|Authentication failed|fatal:|error:|timeout"  # ALTERAR
EXPLICIT_ERRORS=()
while IFS= read -r line; do
  if echo "$line" | grep -qiE "$ERROR_PATTERNS"; then
    EXPLICIT_ERRORS+=("$line")
  fi
done <<< "$WINDOW_LINES"

# ─── Último OK (para report) ──────────────────────────────────────────────────
if grep -q "PROCESSO OK" "$PUSH_LOG"; then                      # ALTERAR
  LAST_OK_LINE="$(grep "PROCESSO OK" "$PUSH_LOG" | tail -1)"   # ALTERAR
  LAST_OK_COMMIT="$(echo "$LAST_OK_LINE" | grep -oP 'id=\K\S+')" || true
  LAST_OK_TS="$(echo "$LAST_OK_LINE" | grep -oP '\[\K[^\]]+' | head -1)" || true
fi

# ─── Contabilizar ────────────────────────────────────────────────────────────
TOTAL_NEW=$(( ${#NEW_FAILURES[@]} + ${#EXPLICIT_ERRORS[@]} ))
ALL_DETAILS=("${NEW_FAILURES[@]}" "${EXPLICIT_ERRORS[@]}")
ALERT_WAS_ACTIVE=false
(( CONSECUTIVE >= THRESHOLD )) && ALERT_WAS_ACTIVE=true

# ─── Lógica de alerta ────────────────────────────────────────────────────────
send_discord() {
  local payload="$1"
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$payload" --max-time 10 >/dev/null
}

if (( TOTAL_NEW > 0 )); then
  NEW_CONSECUTIVE=$(( CONSECUTIVE + TOTAL_NEW ))
  FAILURE_JSON="$(printf '%s\n' "${ALL_DETAILS[@]}" | jq -R . | jq -s .)"
  log "FALHA: ${TOTAL_NEW} nova(s), total=${NEW_CONSECUTIVE}"

  SEND_ALERT=false
  if (( NEW_CONSECUTIVE >= THRESHOLD )); then
    if [[ "$LAST_ALERT" == "null" ]]; then
      SEND_ALERT=true
    else
      LAST_ALERT_EPOCH="$(date -d "$LAST_ALERT" +%s 2>/dev/null || echo 0)"
      (( NOW_EPOCH - LAST_ALERT_EPOCH > ANTI_SPAM_HOURS * 3600 )) && SEND_ALERT=true \
        || log "Anti-spam: suprimindo (enviado há menos de ${ANTI_SPAM_HOURS}h)"
    fi
  fi

  if [[ "$SEND_ALERT" == "true" ]]; then
    ALERT_TS="$NOW_ISO"
    LAST_DETAIL="${ALL_DETAILS[0]:-desconhecido}"
    log "Enviando alerta Discord"
    send_discord "$(jq -n \
      --arg n "$NEW_CONSECUTIVE" --arg d "$LAST_DETAIL" --arg t "${LAST_OK_TS:-nunca}" \
      '{content:"<@344196393512075265> alerta de monitor", embeds:[{title:"Processo falhando", color:15158332, fields:[{name:"Falhas consecutivas", value:$n, inline:true}, {name:"Último OK", value:$t, inline:true}, {name:"Último erro", value:("```text\n"+$d[:900]+"\n```"), inline:false}, {name:"Ação", value:"Investigar log do monitor.", inline:false}]}]}')"
  else
    ALERT_TS="$LAST_ALERT"
  fi

  jq --arg ts "$NOW_ISO" --argjson c "$NEW_CONSECUTIVE" --arg at "$ALERT_TS" --argjson fd "$FAILURE_JSON" \
    '.last_check=$ts | .consecutive_failures=$c | .last_alert_sent=$at | .last_failure_details=$fd' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

else
  if (( CONSECUTIVE > 0 )); then
    log "RESOLVIDO (anterior: ${CONSECUTIVE} falhas)"
    if [[ "$ALERT_WAS_ACTIVE" == "true" ]]; then
      send_discord "$(jq -n \
        --arg n "$CONSECUTIVE" --arg c "${LAST_OK_COMMIT:-?}" --arg t "${LAST_OK_TS:-?}" \
        '{content:"", embeds:[{title:"Processo restabelecido", color:3066993, fields:[{name:"Falhas anteriores", value:$n, inline:true}, {name:"Último OK", value:("`"+$c+"`"), inline:true}, {name:"Horário", value:$t, inline:false}]}]}')"
    fi
  else
    log "OK: zero falhas na janela de ${WINDOW_MINUTES}min"
  fi

  jq --arg ts "$NOW_ISO" '.last_check=$ts | .consecutive_failures=0 | .last_failure_details=[]' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

log "Concluído. consecutive=$(jq -r '.consecutive_failures' "$STATE_FILE") last_ok=${LAST_OK_COMMIT:-n/a}"
```

---
