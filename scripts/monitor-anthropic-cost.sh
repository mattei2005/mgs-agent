#!/bin/bash
# Monitor diário de gasto Anthropic API
# Roda via cron diário
# Posta em #alerts-infra se gasto > threshold

set -e

# === Config ===
THRESHOLD_INFO=5     # Abaixo: postar resumo verde
THRESHOLD_WARN=15    # Acima: warning
THRESHOLD_ALERT=30   # Acima: alerta crítico

# === Carregar credenciais ===
set -a
source /root/mgs-agent/.env
set +a

# === Buscar Admin Key (com retry para 504) ===
ADMIN_KEY=""
for i in 1 2 3; do
  ADMIN_KEY=$(op item get "Anthropic Admin API Key" --vault "MGS Conteúdo" --fields label=monitorcoastkey --reveal 2>/dev/null)
  if [[ "$ADMIN_KEY" == sk-ant-admin* ]]; then
    break
  fi
  sleep 5
done

if [[ "$ADMIN_KEY" != sk-ant-admin* ]]; then
  # Fallback: cache local
  ADMIN_KEY=$(cat /root/.anthropic-admin-key 2>/dev/null)
fi

if [[ "$ADMIN_KEY" != sk-ant-admin* ]]; then
  echo "ERROR: Não conseguiu Admin Key" >&2
  exit 1
fi

# === Webhook Discord ===
WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=password --reveal 2>/dev/null)

# === Período: últimas 24h ===
YESTERDAY=$(date -u -d '1 day ago' +%Y-%m-%dT00:00:00Z)
TODAY=$(date -u +%Y-%m-%dT00:00:00Z)

# === Buscar gasto ===
RAW_AMOUNT=$(curl -s -H "x-api-key: $ADMIN_KEY" \
     -H "anthropic-version: 2023-06-01" \
     "https://api.anthropic.com/v1/organizations/cost_report?starting_at=${YESTERDAY}&ending_at=${TODAY}&bucket_width=1d" \
     | jq -r '.data[0].results[0].amount // "0"')

# === Aplicar divisor (Cost API retorna em centavos × 100) ===
DIVISOR=88
COST=$(echo "scale=2; $RAW_AMOUNT / $DIVISOR" | bc)

# === Buscar tokens (validação cruzada) ===
USAGE_JSON=$(curl -s -H "x-api-key: $ADMIN_KEY" \
     -H "anthropic-version: 2023-06-01" \
     "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=${YESTERDAY}&ending_at=${TODAY}&bucket_width=1d")

CACHE_READ=$(echo "$USAGE_JSON" | jq -r '.data[0].results[0].cache_read_input_tokens // 0')
OUTPUT=$(echo "$USAGE_JSON" | jq -r '.data[0].results[0].output_tokens // 0')

# === Determinar nível e cor ===
COST_INT=$(echo "$COST" | cut -d. -f1)

if (( COST_INT >= THRESHOLD_ALERT )); then
  EMOJI="🔴"
  COLOR=15158332  # Vermelho
  STATUS="ALERTA — Gasto MUITO ALTO"
  MENTION="<@344196393512075265>"
elif (( COST_INT >= THRESHOLD_WARN )); then
  EMOJI="🟡"
  COLOR=15844367  # Amarelo
  STATUS="WARN — Gasto acima do normal"
  MENTION=""
elif (( COST_INT >= THRESHOLD_INFO )); then
  EMOJI="🟢"
  COLOR=3066993  # Verde
  STATUS="OK — Gasto saudável"
  MENTION=""
else
  EMOJI="🟢"
  COLOR=3066993
  STATUS="OK — Gasto baixo"
  MENTION=""
fi

# === Saldo atual (estimativa baseada em auto-reload) ===
SALDO_INFO="Auto-reload ativo: recarrega para \$20 quando atinge \$10"

# === Montar mensagem ===
TITLE="${EMOJI} [ANTHROPIC API] Gasto últimas 24h: \$${COST}"

DESCRIPTION="**Status:** ${STATUS}\n"
DESCRIPTION+="**Cache reads:** $(echo "scale=1; $CACHE_READ / 1000000" | bc)M tokens\n"
DESCRIPTION+="**Output:** $(echo "scale=1; $OUTPUT / 1000000" | bc)M tokens\n"
DESCRIPTION+="**Período:** ${YESTERDAY} até ${TODAY}\n"
DESCRIPTION+="**Saldo:** ${SALDO_INFO}"

if [ -n "$MENTION" ]; then
  CONTENT="${MENTION} verificar logs Zeus/Atena por loops"
else
  CONTENT=""
fi

# === Postar Discord ===
PAYLOAD=$(jq -n \
  --arg content "$CONTENT" \
  --arg title "$TITLE" \
  --arg desc "$DESCRIPTION" \
  --argjson color "$COLOR" \
  '{
    content: $content,
    embeds: [{
      title: $title,
      description: $desc,
      color: $color
    }]
  }')

curl -s -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK" \
  -o /dev/null -w "HTTP: %{http_code}\n"

echo "Monitor executado: \$${COST} (status: ${STATUS})"
