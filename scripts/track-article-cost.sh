#!/bin/bash
#
# track-article-cost.sh — Calcula custo Anthropic por artigo publicado
#
# Lê /root/mgs-agent/logs/publish-wordpress.log buscando "create-post OK".
# Para cada post não rastreado:
#   1. Detecta started_at (inbound message anterior no agent.log)
#   2. Coleta metadados (site, session_id, api_calls, response_chars, topic)
#   3. Consulta Anthropic Admin API pra hora correspondente
#   4. Calcula custo proporcional
#   5. Grava SQLite (idempotente — IGNORE se post_id existe)
#
# Modo:
#   ./track-article-cost.sh           # processa todos pendentes
#   ./track-article-cost.sh <post_id> # força reprocessar post específico
#
# Custo: ZERO tokens (apenas Admin API + parsing local)
# Frequência: cron */15min
#
set -e

# === Config ===
PUB_LOG="/root/mgs-agent/logs/publish-wordpress.log"
AGENT_LOG="/root/.hermes/profiles/atena/logs/agent.log"
DB="/root/mgs-agent/data/article-tracker.db"
SCRIPT_LOG="/root/mgs-agent/logs/track-article-cost.log"
ATENA_API_KEY_ID="apikey_012LYMZh6h8LfeiiLBU16MWh"

# Sonnet 4.6 pricing (USD per million tokens)
PRICE_UNCACHED=3.00
PRICE_CACHE_5M=3.75
PRICE_CACHE_READ=0.30
PRICE_OUTPUT=15.00

mkdir -p "$(dirname "$SCRIPT_LOG")"

log() {
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*" | tee -a "$SCRIPT_LOG"
}

# === Get Admin Key ===
get_admin_key() {
  local key=""
  for i in 1 2 3; do
    key=$(op item get "Anthropic Admin API Key" --vault "MGS Conteúdo" --fields label=monitorcoastkey --reveal 2>/dev/null)
    [[ "$key" == sk-ant-admin* ]] && echo "$key" && return 0
    sleep 3
  done
  log "ERROR: failed to get admin key from 1Password"
  return 1
}

# === Get target post_id (or process all pending) ===
TARGET_POST_ID="${1:-}"

# === Find pending publications ===
log "═══ track-article-cost.sh start ═══"

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

PUB_COUNT=$(echo "$PUBLICATIONS" | grep -c "create-post OK" || echo 0)
log "Pending publications: $PUB_COUNT"

[[ "$PUB_COUNT" -eq 0 ]] && log "Nothing to process. Exit." && exit 0

# === Get Admin Key once ===
ADMIN_KEY=$(get_admin_key) || exit 1
log "Admin key: OK"

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
  
  # Find started_at: last "inbound message" from Atena agent.log BEFORE this timestamp
  # Atena agent.log uses "YYYY-MM-DD HH:MM:SS,ms" format (LOCAL TZ - America/New_York)
  TS_FOR_GREP=$(date -d "$TIMESTAMP_LOCAL" '+%Y-%m-%d %H:%M:%S')
  
  # Get last inbound message before this timestamp
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

  # Safeguard: cap duration at 2h (7200s) — evita inflar custo quando
  # detector pega inbound message nao relacionada do inicio do dia.
  if [[ "$DURATION_SEC" -gt 7200 ]]; then
    log "  WARN: detected duration ${DURATION_SEC}s > 7200s cap — using ended_at - 2h"
    EPOCH_START=$((EPOCH_END - 7200))
    STARTED_AT_UTC=$(date -u -d "@$EPOCH_START" '+%Y-%m-%dT%H:%M:%SZ')
    DURATION_SEC=7200
    log "  started_at (capped): $STARTED_AT_UTC"
  fi

  log "  duration_sec: $DURATION_SEC"
  
  # Find session_id, api_calls, response_chars from agent.log
  # Look for "response ready" line CLOSEST AFTER ended_at (within 5 minutes)
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
  
  # Find session_id (any line in window with [YYYYMMDD_HHMMSS_xxxxxx])
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
  
  # === Query Anthropic Admin API ===
  # Round to hour buckets covering started→ended
  HOUR_START=$(date -u -d "$STARTED_AT_UTC" '+%Y-%m-%dT%H:00:00Z')
  HOUR_END=$(date -u -d "$ENDED_AT_UTC + 1 hour" '+%Y-%m-%dT%H:00:00Z')
  log "  Querying Admin API: $HOUR_START → $HOUR_END"
  
  USAGE_JSON=$(curl -s -H "x-api-key: $ADMIN_KEY" \
       -H "anthropic-version: 2023-06-01" \
       "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=${HOUR_START}&ending_at=${HOUR_END}&bucket_width=1h&group_by[]=api_key_id")
  
  # Extract Atena tokens summed across buckets
  TOKENS=$(echo "$USAGE_JSON" | jq -c --arg key "$ATENA_API_KEY_ID" '
    [.data[].results[] | select(.api_key_id == $key)]
    | {
        uncached: (map(.uncached_input_tokens) | add // 0),
        cache_5m: (map(.cache_creation.ephemeral_5m_input_tokens) | add // 0),
        cache_read: (map(.cache_read_input_tokens) | add // 0),
        output: (map(.output_tokens) | add // 0)
      }')
  
  UNCACHED=$(echo "$TOKENS" | jq -r '.uncached')
  CACHE_5M=$(echo "$TOKENS" | jq -r '.cache_5m')
  CACHE_READ=$(echo "$TOKENS" | jq -r '.cache_read')
  OUTPUT=$(echo "$TOKENS" | jq -r '.output')
  
  log "  Bucket totals: uncached=$UNCACHED cache_5m=$CACHE_5M cache_read=$CACHE_READ output=$OUTPUT"
  
  # Calculate hour bucket cost (full hour total)
  BUCKET_COST=$(echo "$TOKENS" | jq -r --argjson p1 $PRICE_UNCACHED --argjson p2 $PRICE_CACHE_5M --argjson p3 $PRICE_CACHE_READ --argjson p4 $PRICE_OUTPUT '
    (.uncached * $p1 + .cache_5m * $p2 + .cache_read * $p3 + .output * $p4) / 1000000')
  log "  Bucket total cost (full window): \$$BUCKET_COST"

  # Skip if bucket is empty (likely Admin API lag — bucket not closed yet)
  if [[ "$UNCACHED" -eq 0 ]] && [[ "$CACHE_5M" -eq 0 ]] && [[ "$CACHE_READ" -eq 0 ]] && [[ "$OUTPUT" -eq 0 ]]; then
    log "  ⏳  Bucket empty (Admin API lag) — skipping save. Will retry on next cron."
    continue
  fi
  
  # === OPÇÃO B: proporção por api_calls do bucket ===
  # Sum all api_calls reported in "response ready" lines within hour bucket window
  HOUR_START_LOCAL=$(TZ=America/New_York date -d "$HOUR_START" '+%Y-%m-%d %H:%M:%S')
  HOUR_END_LOCAL=$(TZ=America/New_York date -d "$HOUR_END" '+%Y-%m-%d %H:%M:%S')
  
  BUCKET_API_CALLS=$(awk -v start="$HOUR_START_LOCAL" -v end="$HOUR_END_LOCAL" '
    /response ready/ {
      ts = substr($0, 1, 19)
      if (ts >= start && ts < end) {
        match($0, /api_calls=[0-9]+/)
        if (RSTART) {
          calls = substr($0, RSTART+10, RLENGTH-10)
          total += calls + 0
        }
      }
    }
    END { print (total ? total : 0) }
  ' "$AGENT_LOG")
  
  log "  Bucket api_calls total: $BUCKET_API_CALLS  Article api_calls: $API_CALLS"
  
  # Calculate cost via api_calls proportion
  if [[ "$BUCKET_API_CALLS" -gt 0 ]] && [[ "$API_CALLS" -gt 0 ]]; then
    COST=$(awk -v bcost="$BUCKET_COST" -v ac="$API_CALLS" -v bac="$BUCKET_API_CALLS" \
      'BEGIN { printf "%.6f", bcost * ac / bac }')
    METHOD="api_calls_proportional"
  elif [[ "$DURATION_SEC" -gt 0 ]]; then
    # Fallback to duration proportional
    BUCKET_START_EPOCH=$(date -u -d "$HOUR_START" '+%s')
    BUCKET_END_EPOCH=$(date -u -d "$HOUR_END" '+%s')
    BUCKET_TOTAL_SEC=$((BUCKET_END_EPOCH - BUCKET_START_EPOCH))
    COST=$(awk -v bcost="$BUCKET_COST" -v dur="$DURATION_SEC" -v btot="$BUCKET_TOTAL_SEC" \
      'BEGIN { printf "%.6f", bcost * dur / btot }')
    METHOD="time_proportional_fallback"
  else
    COST="0"
    METHOD="estimated"
  fi
  log "  Article cost: \$$COST  method=$METHOD"
  
  # Article-specific token allocation (same proportion as cost)
  if [[ "$BUCKET_API_CALLS" -gt 0 ]] && [[ "$API_CALLS" -gt 0 ]]; then
    ARTICLE_UNCACHED=$(awk -v t="$UNCACHED" -v ac="$API_CALLS" -v bac="$BUCKET_API_CALLS" 'BEGIN { printf "%d", t * ac / bac }')
    ARTICLE_CACHE_5M=$(awk -v t="$CACHE_5M" -v ac="$API_CALLS" -v bac="$BUCKET_API_CALLS" 'BEGIN { printf "%d", t * ac / bac }')
    ARTICLE_CACHE_READ=$(awk -v t="$CACHE_READ" -v ac="$API_CALLS" -v bac="$BUCKET_API_CALLS" 'BEGIN { printf "%d", t * ac / bac }')
    ARTICLE_OUTPUT=$(awk -v t="$OUTPUT" -v ac="$API_CALLS" -v bac="$BUCKET_API_CALLS" 'BEGIN { printf "%d", t * ac / bac }')
  else
    ARTICLE_UNCACHED="$UNCACHED"
    ARTICLE_CACHE_5M="$CACHE_5M"
    ARTICLE_CACHE_READ="$CACHE_READ"
    ARTICLE_OUTPUT="$OUTPUT"
  fi
  
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
  $ARTICLE_UNCACHED, $ARTICLE_CACHE_5M, $ARTICLE_CACHE_READ, $ARTICLE_OUTPUT,
  $COST, '$METHOD', '$CALCULATED_AT',
  '$(echo "$EXCERPT" | sed "s/'/''/g")'
);
EOF
  log "  ✅  Saved post_id=$POST_ID cost=\$$COST"
done

log "═══ track-article-cost.sh end ═══"
