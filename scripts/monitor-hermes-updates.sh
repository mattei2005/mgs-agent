#!/bin/bash
# Monitor de updates do Hermes Agent (NousResearch upstream)
# Frequência: 1×/dia (8 AM EST/EDT via cron — servidor está em America/New_York)
# Custo: ZERO tokens no monitor (git fetch + Discord Bot API); explicação roda no cron hermes-news-explainer
# Canal destino: #alerts-hermes-news (via Zeus Bot API)
# Estado: /root/mgs-agent/data/hermes-version-state.json
# Log: /root/mgs-agent/logs/monitor-hermes-updates.log

set -euo pipefail
set -a
# shellcheck source=/dev/null
source /root/mgs-agent/.env 2>/dev/null || true
set +a

LOG="/root/mgs-agent/logs/monitor-hermes-updates.log"
STATE="/root/mgs-agent/data/hermes-version-state.json"
HERMES_DIR="/root/.hermes/hermes-agent"
TARGET_CHANNEL_ID="1505609056771899644"  # #alerts-hermes-news
ZEUS_PROFILE_ENV="/root/.hermes/profiles/zeus/.env"

mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE")"

log() {
  echo "[$(date -Iseconds)] $*" >> "$LOG"
}

trap 'rc=$?; log "ERROR unexpected_exit rc=$rc line=$LINENO"' ERR

log "START monitor-hermes-updates"

# 1. Buscar token do Zeus Bot para postar no canal Hermes updates
DISCORD_TOKEN="${DISCORD_BOT_TOKEN:-}"
if [[ -z "$DISCORD_TOKEN" && -f "$ZEUS_PROFILE_ENV" ]]; then
  DISCORD_TOKEN=$(grep -E '^DISCORD_BOT_TOKEN=' "$ZEUS_PROFILE_ENV" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
fi

if [[ -z "$DISCORD_TOKEN" ]]; then
  log "ERROR: Discord bot token unavailable"
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
LOCAL_BASE_TAG="$(git describe --tags --abbrev=0 "$CURRENT_LOCAL" 2>/dev/null || true)"
INTERMEDIATE_TAGS=$(git tag --sort=creatordate --contains "$CURRENT_LOCAL" 2>/dev/null | \
  { if [[ -n "$LOCAL_BASE_TAG" ]]; then grep -v -- "$LOCAL_BASE_TAG" || true; else cat; fi; } | \
  head -5 | sed 's/^/• /')

# 9. Categorizar commits por tipo (conventional commits)
COMMIT_RANGE="$CURRENT_LOCAL..origin/main"

FEAT_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^feat" -E 2>/dev/null | wc -l)
FIX_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^fix" -E 2>/dev/null | wc -l)
BREAKING_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="BREAKING\|!:" -E 2>/dev/null | wc -l)
PERF_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="^perf" -E 2>/dev/null | wc -l)
SECURITY_COUNT=$(git log "$COMMIT_RANGE" --oneline --grep="security|sec" --regexp-ignore-case --extended-regexp 2>/dev/null | wc -l)

# Top 5 features
TOP_FEATURES=$( { git log "$COMMIT_RANGE" --oneline --grep="^feat" -E 2>/dev/null | head -5 | \
  sed -E 's/^[a-f0-9]+ //; s/feat(\([^)]+\))?: //; s/^/• /'; } || true )

# Top 5 fixes (excluindo chore/docs/test)
TOP_FIXES=$( { git log "$COMMIT_RANGE" --oneline --grep="^fix" -E 2>/dev/null | head -5 | \
  sed -E 's/^[a-f0-9]+ //; s/fix(\([^)]+\))?: //; s/^/• /'; } || true )

# Breaking changes (se houver)
BREAKING_LIST=""
if [[ "$BREAKING_COUNT" -gt 0 ]]; then
  BREAKING_LIST=$( { git log "$COMMIT_RANGE" --oneline --grep="BREAKING\|!:" -E 2>/dev/null | head -5 | \
    sed -E 's/^[a-f0-9]+ //; s/^/• /'; } || true )
fi

# 10. Montar payload Discord estruturado
BREAKING_HEADER=""
[[ "$BREAKING_COUNT" -gt 0 ]] && BREAKING_HEADER="${BREAKING_COUNT} breaking change(s)"

FEATURES_FIELD="${TOP_FEATURES:-nenhuma feature relevante listada}"
FIXES_FIELD="${TOP_FIXES:-nenhum fix relevante listado}"
BREAKING_FIELD="${BREAKING_LIST:-nenhum}"
TAGS_FIELD="${INTERMEDIATE_TAGS:-nenhuma tag intermediária listada}"
DIFF_URL="https://github.com/NousResearch/hermes-agent/compare/${LOCAL_SHORT}...${UPSTREAM_SHORT}"
RELEASE_URL="https://github.com/NousResearch/hermes-agent/releases/tag/${LATEST_TAG}"

PAYLOAD=$(jq -n \
  --arg title "Hermes Agent — update disponível" \
  --arg upstream "${LATEST_TAG} (${UPSTREAM_SHORT}) — ${UPSTREAM_DATE}" \
  --arg local "${LOCAL_TAG} (${LOCAL_SHORT}) — ${LOCAL_DATE}" \
  --arg lag "${DAYS_BEHIND} dias / ${COMMITS_BEHIND} commits atrás" \
  --arg summary "Features ${FEAT_COUNT} | Fixes ${FIX_COUNT} | Perf ${PERF_COUNT} | Security ${SECURITY_COUNT} | Breaking ${BREAKING_COUNT}" \
  --arg breaking "$BREAKING_HEADER" \
  --arg features "$FEATURES_FIELD" \
  --arg fixes "$FIXES_FIELD" \
  --arg breaking_list "$BREAKING_FIELD" \
  --arg tags "$TAGS_FIELD" \
  --arg diff "$DIFF_URL" \
  --arg releases "$RELEASE_URL" \
  '{content:"", embeds:[{title:$title, color:3447003, fields:[{name:"Upstream", value:$upstream, inline:true}, {name:"Versão local", value:$local, inline:true}, {name:"Atraso", value:$lag, inline:false}, {name:"Resumo", value:$summary, inline:false}, {name:"Breaking", value:($breaking_list | if . == "nenhum" then "nenhum" else "```text\n"+.[:900]+"\n```" end), inline:false}, {name:"Top features", value:("```text\n"+$features[:900]+"\n```"), inline:false}, {name:"Top fixes", value:("```text\n"+$fixes[:900]+"\n```"), inline:false}, {name:"Releases", value:$tags, inline:false}, {name:"Links", value:("[Diff completo]("+$diff+") | [Release notes]("+$releases+")"), inline:false}, {name:"Antes de atualizar", value:"Verificar conflito com patch local em `/root/mgs-agent/patches/hermes/`.", inline:false}]}]}')

HTTP_CODE=$(curl -s -o /tmp/hermes-monitor-response.json -w '%{http_code}' \
  --max-time 15 \
  -X POST "https://discord.com/api/v10/channels/${TARGET_CHANNEL_ID}/messages" \
  -H "Authorization: Bot ${DISCORD_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" || true)

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
  log "ERROR discord_post_failed http=$HTTP_CODE response=$(head -c 200 /tmp/hermes-monitor-response.json)"
  exit 1
fi
