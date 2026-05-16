#!/bin/bash
#
# track-article-cost.sh — Calcula custo hipotético GPT-5.5 por artigo publicado
#
# Com OAuth openai-codex, o custo REAL é zero (incluso na assinatura).
# Este script calcula o custo SIMULADO por artigo para métricas internas:
#
#   1. Lê publish-wordpress.log buscando "create-post OK"
#   2. Para cada post não rastreado:
#      a. Detecta started_at/ended_at (via agent.log)
#      b. Coleta api_calls e response_chars (via agent.log)
#      c. Estima tokens: input = api_calls * AVG_INPUT, output = api_calls * AVG_OUTPUT
#      d. Calcula custo hipotético com pricing GPT-5.5
#      e. Grava SQLite (idempotente — REPLACE se post_id existe)
#
# Modo:
#   ./track-article-cost.sh           # processa todos pendentes
#   ./track-article-cost.sh <post_id> # força reprocessar post específico
#
# Custo: ZERO tokens (parsing local apenas — sem chamada LLM ou API)
# Frequência: cron */15min
#
set -euo pipefail

# === Config ===
PUB_LOG="/root/mgs-agent/logs/publish-wordpress.log"
AGENT_LOG="/root/.hermes/profiles/atena/logs/agent.log"
DB="/root/mgs-agent/data/article-tracker.db"
SCRIPT_LOG="/root/mgs-agent/logs/track-article-cost.log"

# GPT-5.5 pricing hipotético (USD / 1M tokens)
# ⚠️  SINGLE SOURCE OF TRUTH: skills/content-generate-rec/references/pricing.md
# Sem pricing oficial — estimativa baseada em modelos similares OpenAI
# Ajustar quando OpenAI publicar pricing oficial do gpt-5.5
# Se atualizar aqui, atualizar TAMBÉM em monitor-gpt55-oauth-cost.sh
PRICE_INPUT=7.00
PRICE_OUTPUT=21.00

# Estimativa de tokens por api_call (médias empíricas REC Atena)
# Input: ~2000 tokens/call (system prompt + histórico + contexto)
# Output: ~500 tokens/call (resposta + tool calls)
# Calibrar conforme dados acumularem
AVG_INPUT_PER_CALL=2000
AVG_OUTPUT_PER_CALL=500

mkdir -p "$(dirname "$SCRIPT_LOG")"

log() {
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*" | tee -a "$SCRIPT_LOG"
}

# === Get target post_id (or process all pending) ===
TARGET_POST_ID="${1:-}"

# === Find pending publications ===
log "═══ track-article-cost.sh start (GPT-5.5 OAuth mode) ═══"

if [[ -n "$TARGET_POST_ID" ]]; then
  log "Mode: SINGLE post_id=$TARGET_POST_ID"
  PUBLICATIONS=$(grep "create-post OK" "$PUB_LOG" | grep "id=${TARGET_POST_ID}\b")
else
  log "Mode: ALL pending"
  ALL=$(grep "create-post OK" "$PUB_LOG")
  PUBLICATIONS=""
  while IFS= read -r line; do
    pid=$(echo "$line" | grep -oE 'id=[0-9]+' | cut -d= -f2)
    [[ -z "$pid" ]] && continue
    exists=$(sqlite3 "$DB" "SELECT post_id FROM article_publications WHERE post_id=$pid;")
    [[ -z "$exists" ]] && PUBLICATIONS+="$line"$'\n'
  done <<< "$ALL"
fi

# grep -c prints 0 but exits 1 when there are no matches; do not append a second "0".
PUB_COUNT=$(printf "%s" "$PUBLICATIONS" | grep -c "create-post OK" || true)
PUB_COUNT="${PUB_COUNT:-0}"
log "Pending publications: $PUB_COUNT"

[[ "$PUB_COUNT" -eq 0 ]] && log "Nothing to process. Exit." && exit 0

# === Process each publication ===
echo "$PUBLICATIONS" | grep "create-post OK" | while IFS= read -r LINE; do
  # Parse line: [2026-04-28T09:09:51-04:00] create-post OK http=201 site=eggbev id=62026
  TIMESTAMP_LOCAL=$(echo "$LINE" | grep -oE '\[[^]]+\]' | tr -d '[]')
  SITE=$(echo "$LINE" | grep -oE 'site=[a-z0-9_-]+' | cut -d= -f2)
  POST_ID=$(echo "$LINE" | grep -oE 'id=[0-9]+' | cut -d= -f2)

  log "─── Processing post_id=$POST_ID site=$SITE ts=$TIMESTAMP_LOCAL ───"

  # Convert local timestamp to UTC
  ENDED_AT_UTC=$(date -u -d "$TIMESTAMP_LOCAL" '+%Y-%m-%dT%H:%M:%SZ')
  log "  ended_at (UTC): $ENDED_AT_UTC"

  # Find started_at: last "inbound message" from agent.log BEFORE this timestamp
  TS_FOR_GREP=$(date -d "$TIMESTAMP_LOCAL" '+%Y-%m-%d %H:%M:%S')

  STARTED_LOCAL=$(awk -v cutoff="$TS_FOR_GREP" '
    /inbound message/ {
      ts = substr($0, 1, 19)
      if (ts < cutoff) last = $0
    }
    END { print last }
  ' "$AGENT_LOG")

  if [[ -z "$STARTED_LOCAL" ]]; then
    log "  WARN: no inbound message found before $TS_FOR_GREP — using ended_at - 5min as fallback"
    STARTED_AT_UTC=$(date -u -d "$TIMESTAMP_LOCAL - 5 minutes" '+%Y-%m-%dT%H:%M:%SZ')
    TOPIC=""
  else
    STARTED_TS=$(echo "$STARTED_LOCAL" | awk '{print $1, $2}' | sed 's/,.*$//')
    STARTED_AT_UTC=$(date -d "TZ=\"America/New_York\" $STARTED_TS" -u '+%Y-%m-%dT%H:%M:%SZ')
    TOPIC=$(echo "$STARTED_LOCAL" | grep -oE "msg='[^']+'" | sed "s/^msg='//; s/'$//" | head -c 200)
    log "  started_at (UTC): $STARTED_AT_UTC"
    log "  topic: $TOPIC"
  fi

  # Calculate duration
  EPOCH_START=$(date -u -d "$STARTED_AT_UTC" '+%s')
  EPOCH_END=$(date -u -d "$ENDED_AT_UTC" '+%s')
  DURATION_SEC=$((EPOCH_END - EPOCH_START))

  # Cap duration at 2h
  if [[ "$DURATION_SEC" -gt 7200 ]]; then
    log "  WARN: detected duration ${DURATION_SEC}s > 7200s cap — capping"
    EPOCH_START=$((EPOCH_END - 7200))
    STARTED_AT_UTC=$(date -u -d "@$EPOCH_START" '+%Y-%m-%dT%H:%M:%SZ')
    DURATION_SEC=7200
  fi

  log "  duration_sec: $DURATION_SEC"

  # Find api_calls and response_chars from agent.log
  CUTOFF_AFTER=$(date -d "$TIMESTAMP_LOCAL + 5 minutes" '+%Y-%m-%d %H:%M:%S')

  RESPONSE_LINE=$(awk -v start="$TS_FOR_GREP" -v end="$CUTOFF_AFTER" '
    /response ready/ {
      ts = substr($0, 1, 19)
      if (ts >= start && ts <= end) { print; exit }
    }
  ' "$AGENT_LOG")

  API_CALLS=0
  RESPONSE_CHARS=0
  if [[ -n "$RESPONSE_LINE" ]]; then
    API_CALLS=$(echo "$RESPONSE_LINE" | grep -oE 'api_calls=[0-9]+' | cut -d= -f2)
    RESPONSE_CHARS=$(echo "$RESPONSE_LINE" | grep -oE 'response=[0-9]+' | cut -d= -f2)
    log "  api_calls=$API_CALLS  response_chars=$RESPONSE_CHARS"
  fi

  # Find session_id
  SESSION_ID=$(awk -v start="$TS_FOR_GREP" -v end="$CUTOFF_AFTER" '
    {
      ts = substr($0, 1, 19)
      if (ts >= start && ts <= end) {
        if (match($0, /\[[0-9]{8}_[0-9]{6}_[a-f0-9]+\]/)) {
          sid = substr($0, RSTART+1, RLENGTH-2)
          print sid; exit
        }
      }
    }
  ' "$AGENT_LOG")
  log "  session_id: $SESSION_ID"

  # === Estimar tokens via api_calls ===
  # Sem Admin API — usamos médias empíricas por api_call
  if [[ "$API_CALLS" -gt 0 ]]; then
    EST_INPUT=$(( API_CALLS * AVG_INPUT_PER_CALL ))
    EST_OUTPUT=$(( API_CALLS * AVG_OUTPUT_PER_CALL ))
    METHOD="api_calls_estimated"
  elif [[ "$DURATION_SEC" -gt 0 ]]; then
    # Fallback: estimar api_calls pela duração (média ~60s/call)
    EST_CALLS=$(( DURATION_SEC / 60 ))
    [[ "$EST_CALLS" -lt 1 ]] && EST_CALLS=1
    EST_INPUT=$(( EST_CALLS * AVG_INPUT_PER_CALL ))
    EST_OUTPUT=$(( EST_CALLS * AVG_OUTPUT_PER_CALL ))
    API_CALLS="$EST_CALLS"
    METHOD="duration_estimated"
  else
    EST_INPUT=0
    EST_OUTPUT=0
    METHOD="unknown"
  fi

  log "  est_input_tokens=$EST_INPUT  est_output_tokens=$EST_OUTPUT  method=$METHOD"

  # Custo hipotético GPT-5.5
  COST=$(awk -v inp="$EST_INPUT" -v out="$EST_OUTPUT" \
    -v pi="$PRICE_INPUT" -v po="$PRICE_OUTPUT" \
    'BEGIN { printf "%.6f", (inp * pi + out * po) / 1000000 }')

  log "  Article cost (simulated): \$$COST  method=$METHOD"

  # Build raw_log_excerpt
  EXCERPT=$(printf 'pub_log: %s\nresp_log: %s' "$LINE" "${RESPONSE_LINE:-NONE}")

  # === Insert into SQLite ===
  CALCULATED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  sqlite3 "$DB" <<EOF
INSERT OR REPLACE INTO article_publications (
  post_id, site, topic, session_id,
  started_at, ended_at, duration_sec,
  api_calls, response_chars,
  uncached_tokens, cache_5m_tokens, cache_read_tokens, output_tokens,
  cost_usd_estimated, cost_calc_method, cost_calculated_at,
  raw_log_excerpt
) VALUES (
  $POST_ID, '$SITE', '$(echo "$TOPIC" | sed "s/'/''/g")', '$SESSION_ID',
  '$STARTED_AT_UTC', '$ENDED_AT_UTC', $DURATION_SEC,
  $API_CALLS, $RESPONSE_CHARS,
  $EST_INPUT, 0, 0, $EST_OUTPUT,
  $COST, '$METHOD', '$CALCULATED_AT',
  '$(echo "$EXCERPT" | sed "s/'/''/g")'
);
EOF
  log "  ✅  Saved post_id=$POST_ID cost=\$$COST (simulated — OAuth, no real charge)"
done

log "═══ track-article-cost.sh end ═══"
