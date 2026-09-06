#!/bin/bash
# Monitor de updates do Hermes Agent (NousResearch upstream)
# Frequência: 3×/dia (08:37, 14:37 e 20:37 EST/EDT — servidor em America/New_York)
# Custo: ZERO tokens no monitor (git fetch + Discord Bot API); explicação roda no cron hermes-news-explainer
# Canal destino: #alerts-hermes-news (via Zeus Bot API)
# Estado: /root/mgs-agent/data/hermes-version-state.json
# Log: /root/mgs-agent/logs/monitor-hermes-updates.log

set -euo pipefail
DRY_RUN="${HERMES_MONITOR_DRY_RUN:-0}"
SKIP_ENV_LOAD="${HERMES_MONITOR_SKIP_ENV_LOAD:-0}"
if [[ "$DRY_RUN" != "1" && "$SKIP_ENV_LOAD" != "1" ]]; then
    set -a
    # shellcheck source=/dev/null
    source /root/mgs-agent/.env 2>/dev/null || true
    set +a
fi

LOG="${HERMES_MONITOR_LOG:-/root/mgs-agent/logs/monitor-hermes-updates.log}"
STATE="${HERMES_MONITOR_STATE:-/root/mgs-agent/data/hermes-version-state.json}"
HERMES_BIN="${HERMES_MONITOR_BIN:-/root/.local/bin/hermes}"
HERMES_DIR_OVERRIDE="${HERMES_MONITOR_DIR:-}"
UPSTREAM_URL="${HERMES_MONITOR_UPSTREAM_URL:-https://github.com/NousResearch/hermes-agent.git}"
UPSTREAM_BRANCH="${HERMES_MONITOR_UPSTREAM_BRANCH:-main}"
UPSTREAM_TRACKING_REF="refs/remotes/mgs-monitor-upstream/${UPSTREAM_BRANCH}"
CURL_BIN="${HERMES_MONITOR_CURL_BIN:-curl}"
DRY_RUN_OUTPUT="${HERMES_MONITOR_DRY_RUN_OUTPUT:-}"
TARGET_CHANNEL_ID="${HERMES_MONITOR_CHANNEL_ID:-1505609056771899644}"  # #alerts-hermes-news
ZEUS_PROFILE_ENV="${HERMES_MONITOR_ZEUS_ENV:-/root/.hermes/profiles/zeus/.env}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE")"

log() {
  echo "[$(date -Iseconds)] $*" >> "$LOG"
}

resolve_active_hermes_dir() {
    local launcher shebang candidate="" version_output line

    if [[ -n "$HERMES_DIR_OVERRIDE" ]]; then
        candidate="$HERMES_DIR_OVERRIDE"
    else
        if [[ ! -e "$HERMES_BIN" ]]; then
            echo "ERROR: Hermes launcher unavailable: $HERMES_BIN" >&2
            return 1
        fi
        launcher=$(readlink -f "$HERMES_BIN")
        if [[ ! -f "$launcher" ]]; then
            echo "ERROR: resolved Hermes launcher is not a file: $launcher" >&2
            return 1
        fi

        IFS= read -r shebang < "$launcher" || true
        if [[ "$shebang" =~ ^\#\!(.+)/venv/bin/python([0-9.]*)$ ]]; then
            candidate="${BASH_REMATCH[1]}"
        fi

        if [[ -z "$candidate" ]]; then
            version_output=$("$HERMES_BIN" --version 2>/dev/null || true)
            while IFS= read -r line; do
                if [[ "$line" == "Install directory: "* ]]; then
                    candidate="${line#Install directory: }"
                    break
                fi
            done <<< "$version_output"
        fi
    fi

    if [[ -z "$candidate" ]]; then
        echo "ERROR: unable to resolve active Hermes install directory" >&2
        return 1
    fi
    candidate=$(readlink -f "$candidate")
    if [[ ! -e "$candidate/.git" ]] || ! git -C "$candidate" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "ERROR: resolved Hermes install is not a Git worktree: $candidate" >&2
        return 1
    fi
    printf '%s\n' "$candidate"
}

HERMES_DIR=$(resolve_active_hermes_dir) || {
    log "ERROR: active Hermes install resolution failed launcher=$HERMES_BIN"
    exit 1
}

if [[ ! "$UPSTREAM_BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ "$UPSTREAM_BRANCH" == -* ]] || [[ "$UPSTREAM_BRANCH" == *..* ]]; then
    log "ERROR: invalid upstream branch"
    exit 1
fi

trap 'rc=$?; log "ERROR unexpected_exit rc=$rc line=$LINENO"' ERR

log "START monitor-hermes-updates runtime_dir=$HERMES_DIR dry_run=$DRY_RUN"

# 1. Buscar token do Zeus Bot para postar no canal Hermes updates
DISCORD_TOKEN=""
if [[ "$DRY_RUN" != "1" ]]; then
    DISCORD_TOKEN="${DISCORD_BOT_TOKEN:-}"
    if [[ -z "$DISCORD_TOKEN" && -f "$ZEUS_PROFILE_ENV" ]]; then
      DISCORD_TOKEN=$(grep -E '^DISCORD_BOT_TOKEN=' "$ZEUS_PROFILE_ENV" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    fi

    if [[ -z "$DISCORD_TOKEN" ]]; then
      log "ERROR: Discord bot token unavailable"
      exit 1
    fi
fi

# 2. Validar git repo
if [[ ! -d "$HERMES_DIR/.git" ]]; then
  log "ERROR: $HERMES_DIR is not a git repository"
  exit 1
fi

cd "$HERMES_DIR"

# 3. Buscar o upstream oficial em ref dedicada. O origin do runtime pode ser
# uma cópia local congelada usada durante ports MGS e nunca é fonte de verdade
# para disponibilidade de updates.
git fetch --force --quiet "$UPSTREAM_URL" \
  "+refs/heads/${UPSTREAM_BRANCH}:${UPSTREAM_TRACKING_REF}" \
  "+refs/tags/*:refs/tags/*" 2>/dev/null || {
  log "ERROR: official upstream fetch failed branch=$UPSTREAM_BRANCH"
  exit 1
}

# 4. Estado atual
CURRENT_LOCAL=$(git rev-parse HEAD)
CURRENT_UPSTREAM=$(git rev-parse "$UPSTREAM_TRACKING_REF")
LOCAL_SHORT=$(git rev-parse --short HEAD)
UPSTREAM_SHORT=$(git rev-parse --short "$UPSTREAM_TRACKING_REF")
LOCAL_DATE=$(git log -1 --format='%ad' --date=short HEAD)
UPSTREAM_DATE=$(git log -1 --format='%ad' --date=short "$UPSTREAM_TRACKING_REF")

# 5. Ler último commit/runtime notificado
LAST_NOTIFIED=""
LAST_LOCAL=""
if [[ -f "$STATE" ]]; then
  LAST_NOTIFIED=$(jq -r '.last_notified_upstream // ""' "$STATE" 2>/dev/null)
  LAST_LOCAL=$(jq -r '.last_local // ""' "$STATE" 2>/dev/null)
fi

# 6. Sem mudanças desde última notificação. Comparar também o runtime: um
# cutover pode mudar a classificação de release mesmo com o main parado.
if [[ "$CURRENT_UPSTREAM" == "$LAST_NOTIFIED" && "$CURRENT_LOCAL" == "$LAST_LOCAL" ]]; then
  log "OK no_changes upstream=$UPSTREAM_SHORT local=$LOCAL_SHORT"
  exit 0
fi

# 7. Já atualizado. Um runtime MGS pode conter origin/main e ainda ter commits
# locais de port/customização no topo; igualdade de HEAD não é obrigatória.
if git merge-base --is-ancestor "$CURRENT_UPSTREAM" "$CURRENT_LOCAL"; then
  log "OK already_contains_upstream local=$LOCAL_SHORT upstream=$UPSTREAM_SHORT"
  if [[ "$DRY_RUN" != "1" ]]; then
    jq -n --arg u "$CURRENT_UPSTREAM" --arg t "$(date -Iseconds)" \
      --arg l "$CURRENT_LOCAL" \
      '{last_notified_upstream: $u, last_local: $l, last_check: $t, status: "up-to-date-custom-runtime"}' > "$STATE"
  else
    printf 'DRY_RUN runtime_dir=%s upstream=%s local=%s contains_upstream=true discord_post=false state_unchanged=true\n' \
      "$HERMES_DIR" "$UPSTREAM_SHORT" "$LOCAL_SHORT"
  fi
  exit 0
fi

COMPARE_BASE=$(git merge-base "$CURRENT_LOCAL" "$CURRENT_UPSTREAM" 2>/dev/null || true)
if [[ -z "$COMPARE_BASE" ]]; then
  log "ERROR: active runtime has no common base with upstream local=$LOCAL_SHORT upstream=$UPSTREAM_SHORT"
  exit 1
fi
COMPARE_BASE_SHORT=$(git rev-parse --short "$COMPARE_BASE")

# 8. Classificar release estável separadamente do main móvel.
# O main pode ter milhares de commits pós-release; isso é desenvolvimento,
# não uma atualização estável pendente no runtime MGS.
LOCAL_TAG=$(git describe --tags --abbrev=0 "$CURRENT_LOCAL" 2>/dev/null || true)
LATEST_TAG=$(git describe --tags --abbrev=0 "$CURRENT_UPSTREAM" 2>/dev/null || true)
if [[ -z "$LOCAL_TAG" || -z "$LATEST_TAG" ]]; then
  log "ERROR: unable to resolve release tags local=$LOCAL_SHORT upstream=$UPSTREAM_SHORT"
  exit 1
fi

LATEST_RELEASE_COMMIT=$(git rev-list -n 1 "$LATEST_TAG")
LATEST_RELEASE_SHORT=$(git rev-parse --short "$LATEST_RELEASE_COMMIT")
LATEST_RELEASE_DATE=$(git log -1 --format='%ad' --date=short "$LATEST_RELEASE_COMMIT")

STABLE_UPDATE_AVAILABLE=false
STABLE_COMMITS_PENDING=0
STABLE_DAYS_PENDING=0
if ! git merge-base --is-ancestor "$LATEST_RELEASE_COMMIT" "$CURRENT_LOCAL"; then
  if ! git merge-base --is-ancestor "$COMPARE_BASE" "$LATEST_RELEASE_COMMIT"; then
    log "ERROR: latest release is not reachable from runtime base local=$LOCAL_SHORT base=$COMPARE_BASE_SHORT release=$LATEST_RELEASE_SHORT"
    exit 1
  fi
  STABLE_UPDATE_AVAILABLE=true
  STABLE_COMMITS_PENDING=$(git rev-list --count "$COMPARE_BASE..$LATEST_RELEASE_COMMIT")
  STABLE_DAYS_PENDING=$(( ($(date +%s) - $(git log -1 --format='%ct' "$LATEST_RELEASE_COMMIT")) / 86400 ))
fi

MAIN_POST_RELEASE_COUNT=$(git rev-list --count "$LATEST_RELEASE_COMMIT..$CURRENT_UPSTREAM")

NEW_SINCE_LAST="indisponível (base anterior não ancestral)"
NEW_SINCE_LAST_COUNT=-1
if [[ -n "$LAST_NOTIFIED" ]] \
  && git cat-file -e "${LAST_NOTIFIED}^{commit}" 2>/dev/null \
  && git merge-base --is-ancestor "$LAST_NOTIFIED" "$CURRENT_UPSTREAM"; then
  NEW_SINCE_LAST_COUNT=$(git rev-list --count "$LAST_NOTIFIED..$CURRENT_UPSTREAM")
  NEW_SINCE_LAST="${NEW_SINCE_LAST_COUNT} commits"
elif [[ -z "$LAST_NOTIFIED" ]]; then
  NEW_SINCE_LAST="primeiro alerta desta instalação"
fi

# Tags intermediárias (até 5)
LOCAL_BASE_TAG="$(git describe --tags --abbrev=0 "$CURRENT_LOCAL" 2>/dev/null || true)"
INTERMEDIATE_TAGS=$(git tag --sort=creatordate --contains "$COMPARE_BASE" 2>/dev/null | \
  { if [[ -n "$LOCAL_BASE_TAG" ]]; then grep -v -- "$LOCAL_BASE_TAG" || true; else cat; fi; } | \
  head -5 | sed 's/^/• /')

# 9. Categorizar o conjunto correto: release pendente quando houver; caso
# contrário, somente o desenvolvimento pós-release, explicitamente rotulado.
if [[ "$STABLE_UPDATE_AVAILABLE" == "true" ]]; then
  STABLE_COMMIT_WORD="commits"
  [[ "$STABLE_COMMITS_PENDING" == "1" ]] && STABLE_COMMIT_WORD="commit"
  COMMIT_RANGE="$COMPARE_BASE..$LATEST_RELEASE_COMMIT"
  ALERT_TITLE="Hermes Agent — atualização estável disponível"
  STABLE_STATUS="Disponível: ${STABLE_COMMITS_PENDING} ${STABLE_COMMIT_WORD} até ${LATEST_TAG} (${LATEST_RELEASE_SHORT})"
  SUMMARY_LABEL="Resumo da atualização estável"
  DIFF_BASE_SHORT="$COMPARE_BASE_SHORT"
  DIFF_TARGET_SHORT="$LATEST_RELEASE_SHORT"
  ACTION_TEXT="Atualização estável disponível. Antes de executar, verificar patches MGS, backup e rollback."
else
  COMMIT_RANGE="$LATEST_RELEASE_COMMIT..$UPSTREAM_TRACKING_REF"
  ALERT_TITLE="Hermes Agent — novidades em desenvolvimento"
  STABLE_STATUS="Nenhuma — o runtime já contém ${LATEST_TAG} (${LATEST_RELEASE_SHORT})"
  SUMMARY_LABEL="Resumo do main pós-release"
  DIFF_BASE_SHORT="$LATEST_RELEASE_SHORT"
  DIFF_TARGET_SHORT="$UPSTREAM_SHORT"
  ACTION_TEXT="Nenhuma atualização estável pendente. Não promover o main de desenvolvimento sem pedido explícito do Rodolfo."
fi

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
DIFF_URL="https://github.com/NousResearch/hermes-agent/compare/${DIFF_BASE_SHORT}...${DIFF_TARGET_SHORT}"
RELEASE_URL="https://github.com/NousResearch/hermes-agent/releases/tag/${LATEST_TAG}"
MAIN_COMMIT_WORD="commits"
[[ "$MAIN_POST_RELEASE_COUNT" == "1" ]] && MAIN_COMMIT_WORD="commit"
MAIN_STATUS="${MAIN_POST_RELEASE_COUNT} ${MAIN_COMMIT_WORD} no grafo após ${LATEST_TAG}; desenvolvimento ainda sem release"
MAIN_FIELD="${UPSTREAM_SHORT} — ${UPSTREAM_DATE}"$'\n'"${MAIN_STATUS}"

PAYLOAD=$(jq -n \
  --arg title "$ALERT_TITLE" \
  --arg release "${LATEST_TAG} (${LATEST_RELEASE_SHORT}) — ${LATEST_RELEASE_DATE}" \
  --arg local "${LOCAL_TAG} (${LOCAL_SHORT}) — ${LOCAL_DATE}" \
  --arg stable "$STABLE_STATUS" \
  --arg main "$MAIN_FIELD" \
  --arg new_since_last "$NEW_SINCE_LAST" \
  --arg metric_bases $'Atualização estável = release oficial ainda não contida no runtime\nMain pós-release = desenvolvimento ainda sem release; não é pendência operacional\nNovos = avanço do main desde o alerta anterior' \
  --arg summary_label "$SUMMARY_LABEL" \
  --arg summary "Features ${FEAT_COUNT} | Fixes ${FIX_COUNT} | Perf ${PERF_COUNT} | Security ${SECURITY_COUNT} | Breaking ${BREAKING_COUNT}" \
  --arg breaking "$BREAKING_HEADER" \
  --arg features "$FEATURES_FIELD" \
  --arg fixes "$FIXES_FIELD" \
  --arg breaking_list "$BREAKING_FIELD" \
  --arg tags "$TAGS_FIELD" \
  --arg diff "$DIFF_URL" \
  --arg releases "$RELEASE_URL" \
  --arg action "$ACTION_TEXT" \
  '{content:"", embeds:[{title:$title, color:3447003, fields:[{name:"Última release oficial", value:$release, inline:true}, {name:"Runtime MGS", value:$local, inline:true}, {name:"Atualização estável", value:$stable, inline:false}, {name:"Main de desenvolvimento", value:$main, inline:false}, {name:"Novos no main desde o último alerta", value:$new_since_last, inline:true}, {name:"Como ler as contagens", value:$metric_bases, inline:false}, {name:$summary_label, value:$summary, inline:false}, {name:"Breaking", value:($breaking_list | if . == "nenhum" then "nenhum" else "```\n"+.[:900]+"\n```" end), inline:false}, {name:"Top features", value:("```\n"+$features[:900]+"\n```"), inline:false}, {name:"Top fixes", value:("```\n"+$fixes[:900]+"\n```"), inline:false}, {name:"Releases", value:$tags, inline:false}, {name:"Links", value:("[Diff do conjunto classificado]("+$diff+") | [Release notes]("+$releases+")"), inline:false}, {name:"Ação MGS", value:$action, inline:false}]}]}')

if [[ "$DRY_RUN" == "1" ]]; then
  if [[ -n "$DRY_RUN_OUTPUT" ]]; then
    printf '%s\n' "$PAYLOAD" > "$DRY_RUN_OUTPUT"
  fi
  log "DRY_RUN upstream=$UPSTREAM_SHORT local=$LOCAL_SHORT release=$LATEST_TAG stable_update=$STABLE_UPDATE_AVAILABLE stable_pending=$STABLE_COMMITS_PENDING main_post_release=$MAIN_POST_RELEASE_COUNT new_since_last=$NEW_SINCE_LAST_COUNT feat=$FEAT_COUNT fix=$FIX_COUNT breaking=$BREAKING_COUNT state_unchanged=true discord_post=false"
  printf 'DRY_RUN runtime_dir=%s upstream=%s local=%s release=%s stable_update=%s stable_pending=%s main_post_release=%s discord_post=false state_unchanged=true\n' \
      "$HERMES_DIR" "$UPSTREAM_SHORT" "$LOCAL_SHORT" "$LATEST_TAG" "$STABLE_UPDATE_AVAILABLE" "$STABLE_COMMITS_PENDING" "$MAIN_POST_RELEASE_COUNT"
  exit 0
fi

HTTP_CODE=$("$CURL_BIN" -s -o /tmp/hermes-monitor-response.json -w '%{http_code}' \
  --max-time 15 \
  -X POST "https://discord.com/api/v10/channels/${TARGET_CHANNEL_ID}/messages" \
  -H "Authorization: Bot ${DISCORD_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" || true)

if [[ "$HTTP_CODE" =~ ^2 ]]; then
  log "OK notified upstream=$UPSTREAM_SHORT local=$LOCAL_SHORT release=$LATEST_TAG stable_update=$STABLE_UPDATE_AVAILABLE stable_pending=$STABLE_COMMITS_PENDING main_post_release=$MAIN_POST_RELEASE_COUNT new_since_last=$NEW_SINCE_LAST_COUNT feat=$FEAT_COUNT fix=$FIX_COUNT breaking=$BREAKING_COUNT"
  
  # 12. Atualizar state
  jq -n --arg u "$CURRENT_UPSTREAM" --arg l "$CURRENT_LOCAL" --arg t "$(date -Iseconds)" \
        --arg tag "$LATEST_TAG" --arg release_commit "$LATEST_RELEASE_COMMIT" \
        --argjson stable_available "$STABLE_UPDATE_AVAILABLE" \
        --argjson stable_pending "$STABLE_COMMITS_PENDING" \
        --argjson main_post_release "$MAIN_POST_RELEASE_COUNT" \
        --argjson d "$STABLE_DAYS_PENDING" \
        --argjson f "$FEAT_COUNT" --argjson fx "$FIX_COUNT" --argjson br "$BREAKING_COUNT" \
        --argjson n "$NEW_SINCE_LAST_COUNT" \
    '{schema_version: 2, last_notified_upstream: $u, last_local: $l, last_check: $t,
      latest_tag: $tag, latest_release_commit: $release_commit,
      stable_update_available: $stable_available, stable_commits_pending: $stable_pending,
      main_post_release_commits: $main_post_release,
      commits_behind: $stable_pending, new_since_last_alert: $n, days_behind: $d,
      breakdown: {features: $f, fixes: $fx, breaking: $br}}' \
    > "$STATE"
else
  log "ERROR discord_post_failed http=$HTTP_CODE response=$(head -c 200 /tmp/hermes-monitor-response.json)"
  exit 1
fi
