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

# 1. Buscar webhook via 1Password
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

# 2. Validar git repo
if [[ ! -d "$HERMES_DIR/.git" ]]; then
  log "ERROR: $HERMES_DIR is not a git repository"
  exit 1
fi

cd "$HERMES_DIR"

# 3. Fetch upstream
git fetch origin --tags --quiet 2>/dev/null || {
  log "ERROR: git fetch failed"
  exit 1
}

# 4. Estado atual
CURRENT_LOCAL=$(git rev-parse HEAD)
CURRENT_UPSTREAM=$(git rev-parse origin/main)
LOCAL_SHORT=$(git rev-parse --short HEAD)
UPSTREAM_SHORT=$(git rev-parse --short origin/main)
LOCAL_DATE=$(git log -1 --format='%ad' --date=short HEAD)
UPSTREAM_DATE=$(git log -1 --format='%ad' --date=short origin/main)

# 5. Ler último commit notificado
LAST_NOTIFIED=""
if [[ -f "$STATE" ]]; then
  LAST_NOTIFIED=$(jq -r '.last_notified_upstream // ""' "$STATE" 2>/dev/null)
fi

# 6. Sem mudanças desde última notificação
if [[ "$CURRENT_UPSTREAM" == "$LAST_NOTIFIED" ]]; then
  log "OK no_changes upstream=$UPSTREAM_SHORT (last_notified=${LAST_NOTIFIED:0:7})"
  exit 0
fi

# 7. Já atualizado
if [[ "$CURRENT_LOCAL" == "$CURRENT_UPSTREAM" ]]; then
  log "OK already_uptodate local=$LOCAL_SHORT"
  jq -n --arg u "$CURRENT_UPSTREAM" --arg t "$(date -Iseconds)" \
    '{last_notified_upstream: $u, last_check: $t, status: "up-to-date"}' > "$STATE"
  exit 0
fi

# 8. Calcular diferenças
COMMITS_BEHIND=$(git rev-list --count "$CURRENT_LOCAL..origin/main" 2>/dev/null || echo "?")
DAYS_BEHIND=$(( ($(date +%s) - $(git log -1 --format='%ct' "$CURRENT_LOCAL")) / 86400 ))

# Tags entre local e upstream
LOCAL_TAG=$(git describe --tags --abbrev=0 "$CURRENT_LOCAL" 2>/dev/null || echo "n/a")
LATEST_TAG=$(git describe --tags --abbrev=0 origin/main 2>/dev/null || echo "n/a")

# Tags intermediárias (até 5)
INTERMEDIATE_TAGS=$(git tag --sort=creatordate --contains "$CURRENT_LOCAL" 2>/dev/null | \
  grep -v "$(git describe --tags --abbrev=0 "$CURRENT_LOCAL" 2>/dev/null)" | head -5 | sed 's/^/• /')

# 9. Categorizar commits por tipo (conventional commits)
COMMIT_RANGE="$CURRENT_LOCAL..origin/main"

FEAT_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^feat" -E 2>/dev/null | wc -l)
FIX_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^fix" -E 2>/dev/null | wc -l)
BREAKING_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="BREAKING\|!:" -E 2>/dev/null | wc -l)
PERF_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^perf" -E 2>/dev/null | wc -l)
SECURITY_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="security\|sec(" -iE 2>/dev/null | wc -l)

# Top 5 features
TOP_FEATURES=$(git log "$COMMIT_RANGE" --oneline --grep="^feat" -E 2>/dev/null | head -5 | \
  sed -E 's/^[a-f0-9]+ //; s/feat(\([^)]+\))?: //; s/^/• /')

# Top 5 fixes (excluindo chore/docs/test)
TOP_FIXES=$(git log "$COMMIT_RANGE" --oneline --grep="^fix" -E 2>/dev/null | head -5 | \
  sed -E 's/^[a-f0-9]+ //; s/fix(\([^)]+\))?: //; s/^/• /')

# Breaking changes (se houver)
BREAKING_LIST=""
if [[ "$BREAKING_COUNT" -gt 0 ]]; then
  BREAKING_LIST=$(git log "$COMMIT_RANGE" --oneline --grep="BREAKING\|!:" -E 2>/dev/null | head -5 | \
    sed -E 's/^[a-f0-9]+ //; s/^/• /')
fi

# 10. Montar mensagem Discord
BREAKING_HEADER=""
[[ "$BREAKING_COUNT" -gt 0 ]] && BREAKING_HEADER="🚨 **$BREAKING_COUNT BREAKING CHANGE(S)**"

MESSAGE=$(cat <<MSG
🔔 **Hermes Agent — Update disponível**
$BREAKING_HEADER

📦 **Upstream:** \`$LATEST_TAG\` ($UPSTREAM_SHORT) — $UPSTREAM_DATE
📍 **Sua versão:** \`$LOCAL_TAG\` ($LOCAL_SHORT) — $LOCAL_DATE

📊 **$DAYS_BEHIND dias / $COMMITS_BEHIND commits atrás**

🆕 **Resumo de mudanças:**
🚀 Features: $FEAT_COUNT
🐛 Bug fixes: $FIX_COUNT
⚡ Performance: $PERF_COUNT
🔒 Security: $SECURITY_COUNT
⚠️ Breaking: $BREAKING_COUNT
MSG
)

# Adicionar features se houver
if [[ -n "$TOP_FEATURES" ]]; then
  MESSAGE+=$'\n\n**🚀 Top features:**\n```\n'"$TOP_FEATURES"$'\n```'
fi

# Adicionar fixes se houver
if [[ -n "$TOP_FIXES" ]]; then
  MESSAGE+=$'\n**🐛 Top fixes:**\n```\n'"$TOP_FIXES"$'\n```'
fi

# Breaking changes (priorizado)
if [[ -n "$BREAKING_LIST" ]]; then
  MESSAGE+=$'\n**🚨 Breaking changes:**\n```\n'"$BREAKING_LIST"$'\n```'
fi

# Tags intermediárias
if [[ -n "$INTERMEDIATE_TAGS" ]]; then
  MESSAGE+=$'\n**🏷️ Releases entre sua versão e upstream:**\n'"$INTERMEDIATE_TAGS"
fi

# Links
MESSAGE+=$'\n\n🔗 **Diff completo:** https://github.com/NousResearch/hermes-agent/compare/'"$LOCAL_SHORT...$UPSTREAM_SHORT"
MESSAGE+=$'\n🔗 **Release notes:** https://github.com/NousResearch/hermes-agent/releases/tag/'"$LATEST_TAG"

# Aviso patch local
MESSAGE+=$'\n\n⚠️ Antes de atualizar: verificar conflito com patch local em `/root/mgs-agent/patches/hermes/`'

# 11. Enviar webhook (Discord limita a 2000 chars — truncar se necessário)
if [[ ${#MESSAGE} -gt 1900 ]]; then
  MESSAGE="${MESSAGE:0:1850}"$'\n\n[...truncated. Ver release notes completo no link acima]'
fi

PAYLOAD=$(jq -n --arg c "$MESSAGE" '{content: $c}')
HTTP_CODE=$(curl -s -o /tmp/hermes-monitor-response.json -w '%{http_code}' \
  -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

if [[ "$HTTP_CODE" =~ ^2 ]]; then
  log "OK notified upstream=$UPSTREAM_SHORT local=$LOCAL_SHORT behind=$COMMITS_BEHIND days=$DAYS_BEHIND feat=$FEAT_COUNT fix=$FIX_COUNT breaking=$BREAKING_COUNT"
  
  # 12. Atualizar state
  jq -n --arg u "$CURRENT_UPSTREAM" --arg l "$CURRENT_LOCAL" --arg t "$(date -Iseconds)" \
        --arg tag "$LATEST_TAG" --argjson b "$COMMITS_BEHIND" --argjson d "$DAYS_BEHIND" \
        --argjson f "$FEAT_COUNT" --argjson fx "$FIX_COUNT" --argjson br "$BREAKING_COUNT" \
    '{last_notified_upstream: $u, last_local: $l, last_check: $t, latest_tag: $tag, 
      commits_behind: $b, days_behind: $d,
      breakdown: {features: $f, fixes: $fx, breaking: $br}}' \
    > "$STATE"
else
  log "ERROR webhook_failed http=$HTTP_CODE response=$(cat /tmp/hermes-monitor-response.json | head -c 200)"
  exit 1
fi
