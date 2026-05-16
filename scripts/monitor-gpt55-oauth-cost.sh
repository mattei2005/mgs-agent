#!/bin/bash
# monitor-gpt55-oauth-cost.sh — Monitor de volume/custo simulado GPT-5.5 via OAuth
#
# Com OAuth (openai-codex), o custo real é ZERO (incluso na assinatura).
# Este script calcula o custo HIPOTÉTICO com base nos tokens logados no
# agent.log do Zeus e da Atena — para referência interna apenas.
#
# Fonte de tokens: agent.log (campos session_input_tokens / output_tokens
# não aparecem no "response ready" — usamos api_calls como proxy de volume).
#
# Pricing referência GPT-5.5 (hipotético, sem cobrança real):
#   Input:  $7.00 / 1M tokens (estimativa — modelo novo sem pricing oficial)
#   Output: $21.00 / 1M tokens
#   Fonte: https://openai.com/api/pricing/
#
# ATENÇÃO: valores são SIMULADOS. OAuth não gera custo real por token.

set -e

set -a
source /root/mgs-agent/.env
set +a

ZEUS_LOG="/root/.hermes/profiles/zeus/logs/agent.log"
ATENA_LOG="/root/.hermes/profiles/atena/logs/agent.log"

THRESHOLD_INFO=5
THRESHOLD_WARN=15
THRESHOLD_ALERT=30

# GPT-5.5 pricing hipotético (USD / 1M tokens)
# Sem pricing oficial ainda — usando estimativa baseada em o3 ($10/$40)
# e gpt-4o ($2.50/$10). Ajustar quando OpenAI publicar.
PRICE_INPUT=7.00
PRICE_OUTPUT=21.00

# Webhook Discord
WEBHOOK=""
for i in 1 2 3; do
  WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=webhook_url --reveal 2>/dev/null)
  if [[ "$WEBHOOK" == https://* ]]; then
    break
  fi
  sleep 3
done

if [[ "$WEBHOOK" != https://* ]]; then
  echo "ERROR: Webhook not available" >&2
  exit 1
fi

YESTERDAY=$(date -u -d '1 day ago' '+%Y-%m-%d %H:%M:%S')

# Contar api_calls nas últimas 24h em cada log
# Cada api_call ≈ ~2000 tokens input + ~500 tokens output (estimativa média REC)
# Calibrar conforme dados reais acumularem
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

ZEUS_CALLS=$(count_api_calls_since "$ZEUS_LOG" "$YESTERDAY")
ATENA_CALLS=$(count_api_calls_since "$ATENA_LOG" "$YESTERDAY")
TOTAL_CALLS=$((ZEUS_CALLS + ATENA_CALLS))

# Estimativa de tokens por api_call (médias empíricas)
# Input: ~2000 tokens/call (contexto + system prompt + histórico)
# Output: ~500 tokens/call (resposta média)
AVG_INPUT_PER_CALL=2000
AVG_OUTPUT_PER_CALL=500

TOTAL_INPUT=$((TOTAL_CALLS * AVG_INPUT_PER_CALL))
TOTAL_OUTPUT=$((TOTAL_CALLS * AVG_OUTPUT_PER_CALL))

# Custo hipotético
COST=$(awk -v inp="$TOTAL_INPUT" -v out="$TOTAL_OUTPUT" \
  -v pi="$PRICE_INPUT" -v po="$PRICE_OUTPUT" \
  'BEGIN { printf "%.2f", (inp * pi + out * po) / 1000000 }')

TOTAL_INPUT_K=$((TOTAL_INPUT / 1000))
TOTAL_OUTPUT_K=$((TOTAL_OUTPUT / 1000))

COST_INT=$(echo "$COST" | cut -d. -f1)

if [ "$COST_INT" -ge "$THRESHOLD_ALERT" ]; then
  EMOJI="🔴"
  COLOR=15158332
  STATUS="ALERTA — Volume MUITO ALTO"
  MENTION="<@344196393512075265>"
elif [ "$COST_INT" -ge "$THRESHOLD_WARN" ]; then
  EMOJI="🟡"
  COLOR=15844367
  STATUS="WARN — Volume acima do normal"
  MENTION=""
elif [ "$COST_INT" -ge "$THRESHOLD_INFO" ]; then
  EMOJI="🟢"
  COLOR=3066993
  STATUS="OK — Volume saudável"
  MENTION=""
else
  EMOJI="🟢"
  COLOR=3066993
  STATUS="OK — Volume baixo"
  MENTION=""
fi

TITLE="GPT-5.5 OAuth — volume 24h"

if [ "$COST_INT" -ge "$THRESHOLD_ALERT" ]; then
  SUMMARY="🔴 ALERTA — custo simulado \$${COST}"
elif [ "$COST_INT" -ge "$THRESHOLD_WARN" ]; then
  SUMMARY="🟡 WARN — custo simulado \$${COST}"
else
  SUMMARY="🟢 OK — custo simulado \$${COST}"
fi

if [ -n "$MENTION" ]; then
  CONTENT="${MENTION} alerta de volume GPT-5.5 OAuth"
else
  CONTENT=""
fi

PAYLOAD=$(jq -n \
  --arg c "$CONTENT" \
  --arg t "$TITLE" \
  --arg s "$SUMMARY" \
  --arg status "$STATUS" \
  --arg real "\$0.00 — OAuth incluso na assinatura" \
  --arg simulated "\$${COST} — se fosse pay-per-token" \
  --arg calls "${TOTAL_CALLS} total | Zeus ${ZEUS_CALLS} | Atena ${ATENA_CALLS}" \
  --arg tokens "~${TOTAL_INPUT_K}K input | ~${TOTAL_OUTPUT_K}K output" \
  --arg pricing "GPT-5.5 \\$${PRICE_INPUT}/\\$${PRICE_OUTPUT} por 1M — estimativa" \
  --arg note "Valores simulados; não representa cobrança real." \
  --argjson col "$COLOR" \
  '{
    content: $c,
    embeds: [{
      title: $t,
      description: $s,
      color: $col,
      fields: [
        {name: "Status", value: $status, inline: false},
        {name: "Custo real", value: $real, inline: true},
        {name: "Custo hipotético", value: $simulated, inline: true},
        {name: "API calls", value: $calls, inline: false},
        {name: "Tokens estimados", value: $tokens, inline: false},
        {name: "Referência", value: $pricing, inline: false},
        {name: "Nota", value: $note, inline: false}
      ]
    }]
  }')

HTTP_CODE=$(curl -s --max-time 15 -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK" \
  -o /tmp/discord-response.txt -w "%{http_code}")

echo "Monitor: \$${COST} simulado | API calls: ${TOTAL_CALLS} | HTTP: ${HTTP_CODE}"
echo "Zeus: ${ZEUS_CALLS} calls | Atena: ${ATENA_CALLS} calls"

if [ "$HTTP_CODE" != "204" ] && [ "$HTTP_CODE" != "200" ]; then
  echo "Discord error response:"
  cat /tmp/discord-response.txt
fi
