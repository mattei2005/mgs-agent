#!/bin/bash
# cleanup-discord-threads.sh
# Deleta threads do Discord arquivadas há mais de N dias
# Auto-descobre canais da categoria configurada (Agents)
# Roda via cron diariamente

set -euo pipefail

LOG_FILE="/root/mgs-agent/logs/cleanup-discord-threads.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $1" | tee -a "$LOG_FILE"
}

log "═══ cleanup-discord-threads.sh start ═══"

# Configurações
# Parse robusto: pega valor após =, tira aspas se houver
DISCORD_BOT_TOKEN=$(grep "^DISCORD_BOT_TOKEN=" /root/.hermes/profiles/atena/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
GUILD_ID="1185714635991679006"
CATEGORY_ID="1496264197439230003"  # Categoria 'Agents'
DAYS_THRESHOLD=2
USER_AGENT="Hermes-Agent (https://github.com/NousResearch/hermes-agent)"

if [[ -z "$DISCORD_BOT_TOKEN" ]]; then
  log "ERROR: DISCORD_BOT_TOKEN nao encontrado"
  exit 1
fi

# Calcula timestamp limite
THRESHOLD_DATE=$(date -u -d "$DAYS_THRESHOLD days ago" +%Y-%m-%dT%H:%M:%S)
log "Threshold: archived antes de $THRESHOLD_DATE UTC ($DAYS_THRESHOLD dias atras)"
log "Categoria de auto-descoberta: $CATEGORY_ID"

# Auto-descobrir canais da categoria
CHANNELS_RESPONSE=$(curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
                         -H "User-Agent: $USER_AGENT" \
                         "https://discord.com/api/v10/guilds/$GUILD_ID/channels")

PARENT_CHANNELS=$(echo "$CHANNELS_RESPONSE" | python3 -c "
import sys, json
channels = json.load(sys.stdin)
for c in channels:
    if c.get('parent_id') == '$CATEGORY_ID' and c.get('type') == 0:
        print(f\"{c['id']}|{c.get('name', '')}\")
")

CHANNEL_COUNT=$(echo "$PARENT_CHANNELS" | grep -c "|" || true)
log "Canais auto-descobertos na categoria: $CHANNEL_COUNT"

DELETED=0
SKIPPED=0
ERRORS=0

while IFS='|' read -r PARENT_ID PARENT_NAME; do
  [[ -z "$PARENT_ID" ]] && continue
  log "─── Canal pai #$PARENT_NAME ($PARENT_ID) ───"
  
  # Buscar threads ARQUIVADAS publicas
  RESPONSE=$(curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
                  -H "User-Agent: $USER_AGENT" \
                  "https://discord.com/api/v10/channels/$PARENT_ID/threads/archived/public?limit=100")
  
  THREAD_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('threads', [])))" 2>/dev/null || echo 0)
  log "  $THREAD_COUNT threads arquivadas"
  
  while IFS='|' read -r THREAD_ID ARCHIVE_TS THREAD_NAME; do
    [[ -z "$THREAD_ID" ]] && continue
    
    ARCHIVE_DATE_TRIM=${ARCHIVE_TS:0:19}
    
    if [[ "$ARCHIVE_DATE_TRIM" < "$THRESHOLD_DATE" ]]; then
      HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
                       -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
                       -H "User-Agent: $USER_AGENT" \
                       "https://discord.com/api/v10/channels/$THREAD_ID")
      
      if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "204" ]]; then
        log "  DELETE OK [$THREAD_ID] '$THREAD_NAME' (archived $ARCHIVE_DATE_TRIM)"
        DELETED=$((DELETED+1))
      else
        log "  DELETE FAIL [$THREAD_ID] HTTP $HTTP_CODE '$THREAD_NAME'"
        ERRORS=$((ERRORS+1))
      fi
      
      sleep 0.3
    else
      log "  SKIP [$THREAD_ID] '$THREAD_NAME' (archived $ARCHIVE_DATE_TRIM, dentro de $DAYS_THRESHOLD dias)"
      SKIPPED=$((SKIPPED+1))
    fi
  done < <(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('threads', []):
    archive_ts = t.get('thread_metadata', {}).get('archive_timestamp', '')
    print(f\"{t['id']}|{archive_ts}|{t.get('name', '')[:60]}\")
" 2>/dev/null)
done <<< "$PARENT_CHANNELS"

log "Resumo: deleted=$DELETED skipped=$SKIPPED errors=$ERRORS"
log "═══ cleanup-discord-threads.sh end ═══"
