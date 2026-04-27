#!/bin/bash
set -e

THRESHOLD_INFO=5
THRESHOLD_WARN=15
THRESHOLD_ALERT=30

set -a
source /root/mgs-agent/.env
set +a

ADMIN_KEY=""
for i in 1 2 3; do
  ADMIN_KEY=$(op item get "Anthropic Admin API Key" --vault "MGS Conteúdo" --fields label=monitorcoastkey --reveal 2>/dev/null)
  if [[ "$ADMIN_KEY" == sk-ant-admin* ]]; then
    break
  fi
  sleep 5
done

if [[ "$ADMIN_KEY" != sk-ant-admin* ]]; then
  ADMIN_KEY=$(cat /root/.anthropic-admin-key 2>/dev/null)
fi

if [[ "$ADMIN_KEY" != sk-ant-admin* ]]; then
  echo "ERROR: Admin Key not available" >&2
  exit 1
fi

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

YESTERDAY=$(date -u -d '1 day ago' +%Y-%m-%dT00:00:00Z)
TODAY=$(date -u +%Y-%m-%dT00:00:00Z)

RAW_AMOUNT=$(curl -s -H "x-api-key: $ADMIN_KEY" \
     -H "anthropic-version: 2023-06-01" \
     "https://api.anthropic.com/v1/organizations/cost_report?starting_at=${YESTERDAY}&ending_at=${TODAY}&bucket_width=1d" \
     | jq -r '.data[0].results[0].amount // "0"')

DIVISOR=88
COST=$(echo "scale=2; $RAW_AMOUNT / $DIVISOR" | bc)

USAGE_JSON=$(curl -s -H "x-api-key: $ADMIN_KEY" \
     -H "anthropic-version: 2023-06-01" \
     "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=${YESTERDAY}&ending_at=${TODAY}&bucket_width=1d")

CACHE_READ=$(echo "$USAGE_JSON" | jq -r '.data[0].results[0].cache_read_input_tokens // 0')
OUTPUT=$(echo "$USAGE_JSON" | jq -r '.data[0].results[0].output_tokens // 0')

CACHE_READ_M=$(echo "scale=1; $CACHE_READ / 1000000" | bc)
OUTPUT_M=$(echo "scale=1; $OUTPUT / 1000000" | bc)

COST_INT=$(echo "$COST" | cut -d. -f1)

if [ "$COST_INT" -ge "$THRESHOLD_ALERT" ]; then
  EMOJI="🔴"
  COLOR=15158332
  STATUS="ALERTA — Gasto MUITO ALTO"
  MENTION="<@344196393512075265>"
elif [ "$COST_INT" -ge "$THRESHOLD_WARN" ]; then
  EMOJI="🟡"
  COLOR=15844367
  STATUS="WARN — Gasto acima do normal"
  MENTION=""
elif [ "$COST_INT" -ge "$THRESHOLD_INFO" ]; then
  EMOJI="🟢"
  COLOR=3066993
  STATUS="OK — Gasto saudavel"
  MENTION=""
else
  EMOJI="🟢"
  COLOR=3066993
  STATUS="OK — Gasto baixo"
  MENTION=""
fi

TITLE="${EMOJI} [ANTHROPIC API] Gasto 24h: \$${COST}"
DESC="**Status:** ${STATUS}\n**Cache reads:** ${CACHE_READ_M}M tokens\n**Output:** ${OUTPUT_M}M tokens\n**Auto-reload:** Ativo (\$10 -> \$20)"

if [ -n "$MENTION" ]; then
  CONTENT="${MENTION} verificar logs Zeus/Atena"
else
  CONTENT=""
fi

PAYLOAD=$(jq -n \
  --arg c "$CONTENT" \
  --arg t "$TITLE" \
  --arg d "$DESC" \
  --argjson col "$COLOR" \
  '{content: $c, embeds: [{title: $t, description: $d, color: $col}]}')

HTTP_CODE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK" \
  -o /tmp/discord-response.txt -w "%{http_code}")

echo "Monitor: \$${COST} | Status: ${STATUS} | HTTP: ${HTTP_CODE}"

if [ "$HTTP_CODE" != "204" ] && [ "$HTTP_CODE" != "200" ]; then
  echo "Discord error response:"
  cat /tmp/discord-response.txt
fi
