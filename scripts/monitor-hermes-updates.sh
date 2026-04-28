#!/bin/bash
# Monitor de updates do Hermes Agent (NousResearch upstream)
# Frequência: 1×/dia (8 AM EST/EDT via cron — servidor está em America/New_York)
# Custo: ZERO tokens (apenas git fetch + Discord webhook)
# Canal destino: Alerts Infra Channel
# Estado: /root/mgs-agent/data/hermes-version-state.json
# Log: /root/mgs-agent/logs/monitor-hermes-updates.log

set -e
set -a
source /root/mgs-agent/.env 2>/dev/null || true
set +a

LOG="/root/mgs-agent/logs/monitor-hermes-updates.log"
STATE="/root/mgs-agent/data/hermes-version-state.json"
HERMES_DIR="/root/.hermes/hermes-agent"

mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE")"

log() {
  echo "[$(date -Iseconds)] $*" >> "$LOG"
}

# 1. Buscar webhook via 1Password (mesmo padrão dos outros monitores)
WEBHOOK=""
for i in 1 2 3; do
  WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" \
    --vault "MGS Conteúdo" \
    --fields label=webhook_url --reveal 2>/dev/null)
  [[ "$WEBHOOK" == https://* ]] && break
  sleep 2
done

if [[ "$WEBHOOK" != https://* ]]; then
  log "ERROR: webhook unavailable after 3 retries"
  exit 1
fi

# 2. Verificar se Hermes é git repo válido
if [[ ! -d "$HERMES_DIR/.git" ]]; then
  log "ERROR: $HERMES_DIR is not a git repository"
  exit 1
fi

cd "$HERMES_DIR"

# 3. Fetch upstream (silencioso)
git fetch origin --tags --quiet 2>/dev/null || {
  log "ERROR: git fetch failed"
  exit 1
}

# 4. Estado atual
CURRENT_LOCAL=$(git rev-parse HEAD)
CURRENT_UPSTREAM=$(git rev-parse origin/main)
LOCAL_SHORT=$(git rev-parse --short HEAD)
UPSTREAM_SHORT=$(git rev-parse --short origin/main)

# 5. Ler último commit notificado
LAST_NOTIFIED=""
if [[ -f "$STATE" ]]; then
  LAST_NOTIFIED=$(jq -r '.last_notified_upstream // ""' "$STATE" 2>/dev/null)
fi

# 6. Se não mudou desde última notificação, sair silenciosamente
if [[ "$CURRENT_UPSTREAM" == "$LAST_NOTIFIED" ]]; then
  log "OK no_changes upstream=$UPSTREAM_SHORT (last_notified=${LAST_NOTIFIED:0:7})"
  exit 0
fi

# 7. Já está no último? Atualiza state e sai
if [[ "$CURRENT_LOCAL" == "$CURRENT_UPSTREAM" ]]; then
  log "OK already_uptodate local=$LOCAL_SHORT"
  jq -n --arg u "$CURRENT_UPSTREAM" --arg t "$(date -Iseconds)" \
    '{last_notified_upstream: $u, last_check: $t, status: "up-to-date"}' > "$STATE"
  exit 0
fi

# 8. Há diferença real — calcular detalhes
COMMITS_BEHIND=$(git rev-list --count "$CURRENT_LOCAL..origin/main" 2>/dev/null || echo "?")

# Pegar última tag publicada
LATEST_TAG=$(git describe --tags --abbrev=0 origin/main 2>/dev/null || echo "n/a")

# Verificar breaking changes nos commit messages
BREAKING_COUNT=$(git log "$CURRENT_LOCAL..origin/main" --grep="BREAKING" --oneline 2>/dev/null | wc -l)
BREAKING_FLAG=""
[[ "$BREAKING_COUNT" -gt 0 ]] && BREAKING_FLAG=" ⚠️ **$BREAKING_COUNT BREAKING CHANGE(S)**"

# Sample de últimos 3 commits novos
RECENT_COMMITS=$(git log "$CURRENT_LOCAL..origin/main" --oneline -3 2>/dev/null | sed 's/^/• /')

# 9. Montar mensagem Discord (markdown)
MESSAGE=$(cat <<MSG
🔔 **Hermes Agent — Update disponível**$BREAKING_FLAG

📦 **Upstream:** \`$LATEST_TAG\` ($UPSTREAM_SHORT)
📍 **Sua versão:** \`$LOCAL_SHORT\`
📊 **Você está $COMMITS_BEHIND commits atrás**

**Últimos commits:**
\`\`\`
$RECENT_COMMITS
\`\`\`

🔗 https://github.com/NousResearch/hermes-agent/releases/tag/$LATEST_TAG

⚠️ Antes de atualizar: verificar conflito com patch local em \`/root/mgs-agent/patches/hermes/\`
MSG
)

# 10. Enviar webhook
PAYLOAD=$(jq -n --arg c "$MESSAGE" '{content: $c}')
HTTP_CODE=$(curl -s -o /tmp/hermes-monitor-response.json -w '%{http_code}' \
  -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

if [[ "$HTTP_CODE" =~ ^2 ]]; then
  log "OK notified upstream=$UPSTREAM_SHORT local=$LOCAL_SHORT behind=$COMMITS_BEHIND breaking=$BREAKING_COUNT"
  
  # 11. Atualizar state (não notificar de novo)
  jq -n --arg u "$CURRENT_UPSTREAM" --arg l "$CURRENT_LOCAL" --arg t "$(date -Iseconds)" \
        --arg tag "$LATEST_TAG" --argjson b "$COMMITS_BEHIND" --argjson br "$BREAKING_COUNT" \
    '{last_notified_upstream: $u, last_local: $l, last_check: $t, latest_tag: $tag, commits_behind: $b, breaking_changes: $br}' \
    > "$STATE"
else
  log "ERROR webhook_failed http=$HTTP_CODE response=$(cat /tmp/hermes-monitor-response.json | head -c 200)"
  exit 1
fi
