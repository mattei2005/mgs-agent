#!/bin/bash
# monitor-gpt55-oauth-cost.sh — Monitor de volume/uso hipotético GPT-5.5 via OAuth
#
# Com OAuth (openai-codex), custo real é ZERO (incluso na assinatura).
# Este script calcula USO HIPOTÉTICO se fosse pay-per-token, apenas para
# visibilidade operacional de volume. Não representa cobrança real.
#
# Modos:
#   --dry-run   calcula e imprime payload resumido, sem webhook
#   normal      posta embed no #alerts-infra conforme thresholds

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [--dry-run]"
  exit 0
elif [[ -n "${1:-}" ]]; then
  echo "ERROR: argumento desconhecido: $1" >&2
  echo "Usage: $0 [--dry-run]" >&2
  exit 2
fi

set -a
# shellcheck source=/dev/null
source /root/mgs-agent/.env 2>/dev/null || true
set +a

LOG_DIR="/root/.hermes/profiles"
PROFILES=(zeus atena ares hera)

THRESHOLD_INFO=5
THRESHOLD_WARN=15
THRESHOLD_ALERT=30

# Pricing hipotético GPT-5.5 (USD / 1M tokens) — somente referência interna.
PRICE_INPUT=7.00
PRICE_OUTPUT=21.00

YESTERDAY=$(date -u -d '1 day ago' '+%Y-%m-%d %H:%M:%S')

count_api_calls_since() {
  local logfile="$1"
  local since="$2"
  if [[ ! -f "$logfile" ]]; then echo 0; return; fi
  awk -v since="$since" '
    /response ready/ {
      ts = substr($0, 1, 19)
      if (ts >= since) {
        match($0, /api_calls=[0-9]+/)
        if (RSTART) {
          calls = substr($0, RSTART+10, RLENGTH-10)
          total += calls + 0
        }
      }
    }
    END { print (total ? total : 0) }
  ' "$logfile"
}

TOTAL_CALLS=0
CALLS_DETAIL=()
for profile in "${PROFILES[@]}"; do
  calls=$(count_api_calls_since "${LOG_DIR}/${profile}/logs/agent.log" "$YESTERDAY")
  TOTAL_CALLS=$((TOTAL_CALLS + calls))
  CALLS_DETAIL+=("${profile^} ${calls}")
done

AVG_INPUT_PER_CALL=2000
AVG_OUTPUT_PER_CALL=500
TOTAL_INPUT=$((TOTAL_CALLS * AVG_INPUT_PER_CALL))
TOTAL_OUTPUT=$((TOTAL_CALLS * AVG_OUTPUT_PER_CALL))
HYPOTHETICAL_USD=$(awk -v inp="$TOTAL_INPUT" -v out="$TOTAL_OUTPUT" \
  -v pi="$PRICE_INPUT" -v po="$PRICE_OUTPUT" \
  'BEGIN { printf "%.2f", (inp * pi + out * po) / 1000000 }')
TOTAL_INPUT_K=$((TOTAL_INPUT / 1000))
TOTAL_OUTPUT_K=$((TOTAL_OUTPUT / 1000))
USAGE_INT=$(echo "$HYPOTHETICAL_USD" | cut -d. -f1)
CALLS_JOINED=$(IFS=' | '; echo "${CALLS_DETAIL[*]}")

if [ "$USAGE_INT" -ge "$THRESHOLD_ALERT" ]; then
  COLOR=15158332
  STATUS="ALERTA — volume muito alto"
  MENTION="<@344196393512075265>"
elif [ "$USAGE_INT" -ge "$THRESHOLD_WARN" ]; then
  COLOR=15844367
  STATUS="WARN — volume acima do normal"
  MENTION=""
else
  COLOR=3066993
  STATUS="OK — volume normal"
  MENTION=""
fi

TITLE="GPT-5.5 OAuth — uso hipotético 24h"
SUMMARY="Uso hipotético: \$${HYPOTHETICAL_USD} se fosse pay-per-token; custo real: \$0.00"
CONTENT=""
if [ -n "$MENTION" ]; then
  CONTENT="${MENTION} alerta de volume GPT-5.5 OAuth"
fi

PAYLOAD=$(jq -n \
  --arg c "$CONTENT" \
  --arg t "$TITLE" \
  --arg s "$SUMMARY" \
  --arg status "$STATUS" \
  --arg real "\$0.00 — OAuth incluso na assinatura" \
  --arg hypothetical "\$${HYPOTHETICAL_USD} — simulação se fosse pay-per-token" \
  --arg calls "${TOTAL_CALLS} total | ${CALLS_JOINED}" \
  --arg tokens "~${TOTAL_INPUT_K}K input | ~${TOTAL_OUTPUT_K}K output" \
  --arg pricing "GPT-5.5 \$${PRICE_INPUT}/\$${PRICE_OUTPUT} por 1M — estimativa" \
  --arg note "Valores hipotéticos; não representam cobrança real." \
  --argjson col "$COLOR" \
  '{content:$c, embeds:[{title:$t, description:$s, color:$col, fields:[{name:"Status", value:$status, inline:false}, {name:"Custo real", value:$real, inline:true}, {name:"Uso hipotético", value:$hypothetical, inline:true}, {name:"API calls", value:$calls, inline:false}, {name:"Tokens estimados", value:$tokens, inline:false}, {name:"Referência", value:$pricing, inline:false}, {name:"Nota", value:$note, inline:false}]}]}')

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY-RUN: ${TITLE} | ${SUMMARY} | calls=${TOTAL_CALLS} (${CALLS_JOINED})"
  exit 0
fi

WEBHOOK=""
for _attempt in 1 2 3; do
  WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=webhook_url --reveal 2>/dev/null || true)
  [[ "$WEBHOOK" == https://* ]] && break
  sleep 3
done

if [[ "$WEBHOOK" != https://* ]]; then
  echo "ERROR: Webhook not available" >&2
  exit 1
fi

HTTP_CODE=$(curl -s --max-time 15 -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK" \
  -o /tmp/discord-response.txt -w "%{http_code}")

echo "Monitor: uso hipotético \$${HYPOTHETICAL_USD} | API calls: ${TOTAL_CALLS} | HTTP: ${HTTP_CODE}"
echo "${CALLS_JOINED}"

if [ "$HTTP_CODE" != "204" ] && [ "$HTTP_CODE" != "200" ]; then
  echo "Discord error response:"
  sed -n '1,20p' /tmp/discord-response.txt
fi
