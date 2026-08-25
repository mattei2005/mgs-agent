#!/usr/bin/env bash
# =============================================================================
# monitor-auto-push.sh — Monitor de falhas no auto-push do mgs-agent
# Roda a cada 15min via cron. Detecta STARTs sem OK correspondente,
# erros explícitos no log, e envia alerta Discord se threshold atingido.
# Estado persistido em data/auto-push-monitor.json
# =============================================================================

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [--dry-run]"
    exit 0
elif [[ -n "${1:-}" ]]; then
    echo "ERROR: argumento desconhecido: $1" >&2
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${MGS_AUTOPUSH_BASE_DIR:-$(dirname "$SCRIPT_DIR")}"
PUSH_LOG="${BASE_DIR}/logs/auto-push.log"
AUTO_COMMIT_LOG="${BASE_DIR}/logs/auto-commit-watcher.log"
STATE_FILE="${BASE_DIR}/data/auto-push-monitor.json"
WINDOW_MINUTES="${WINDOW_MINUTES:-60}"
THRESHOLD="${THRESHOLD:-3}"
ANTI_SPAM_HOURS="${ANTI_SPAM_HOURS:-2}"

# ─── Transporte Discord direto pelo bot Zeus ────────────────────────────────
DISCORD_CHANNEL_ID="${MGS_AUTOPUSH_DISCORD_CHANNEL_ID:-1498132022634483894}"
DISCORD_POSTER="${MGS_AUTOPUSH_DISCORD_POSTER:-${BASE_DIR}/scripts/discord-bot-post.py}"
GIT_SSH_COMMAND_DEFAULT="ssh -i /root/.ssh/mgs_github_deploy_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/.ssh/known_hosts_github_mgs"

post_discord_payload() {
    local payload="$1"
    printf '%s' "$payload" | "$DISCORD_POSTER" --channel-id "$DISCORD_CHANNEL_ID"
}


NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_EPOCH="$(date +%s)"

log() { echo "[$(date -Iseconds)] monitor-auto-push: $*"; }

# ─── Garantir state file existe ──────────────────────────────────────────────
if [[ ! -f "$STATE_FILE" ]]; then
    cat > "$STATE_FILE" <<'EOF'
{
  "_meta": {
    "description": "Estado do monitor de auto-push. Atualizado a cada execução do cron monitor-auto-push.sh",
    "created": "auto",
    "threshold": 3,
    "anti_spam_window_hours": 2
  },
  "last_check": null,
  "consecutive_failures": 0,
  "last_alert_sent": null,
  "last_failure_details": []
}
EOF
    log "State file criado em $STATE_FILE"
fi

# ─── Ler estado atual ─────────────────────────────────────────────────────────
CONSECUTIVE=$(jq -r '.consecutive_failures // 0' "$STATE_FILE")
LAST_ALERT=$(jq -r '.last_alert_sent // "null"' "$STATE_FILE")

# ─── Ler log de push ─────────────────────────────────────────────────────────
if [[ ! -f "$PUSH_LOG" ]]; then
    log "WARN: Push log não encontrado em $PUSH_LOG — nada a monitorar"
    jq --arg ts "$NOW_ISO" '.last_check = $ts' "$STATE_FILE" > "${STATE_FILE}.tmp" \
        && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    exit 0
fi

# ─── Janela de análise: últimos WINDOW_MINUTES minutos ───────────────────────
CUTOFF_EPOCH=$(( NOW_EPOCH - WINDOW_MINUTES * 60 ))

# Extrair linhas da janela (formato: [2026-04-26T16:27:40-04:00] ...)
# Converter timestamp do log para epoch para filtrar
WINDOW_LINES=""
while IFS= read -r line; do
    ts="$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}')" || continue
    line_epoch="$(date -d "$ts" +%s 2>/dev/null)" || continue
    if (( line_epoch >= CUTOFF_EPOCH )); then
        WINDOW_LINES+="$line"$'\n'
    fi
done < "$PUSH_LOG"

# ─── Detectar STARTs sem OK correspondente ───────────────────────────────────
NEW_FAILURES=()
LAST_OK_COMMIT=""
LAST_OK_TS=""

# Extrair todos os commits START na janela
while IFS= read -r line; do
    if echo "$line" | grep -q "auto-push START"; then
        commit="$(echo "$line" | grep -oP 'commit=\K[a-f0-9]+')" || continue
        ts="$(echo "$line" | grep -oP '\[\K[^\]]+')" || continue
        # Verificar se existe OK para esse commit no log completo.
        # Se o commit já chegou em origin/main por reconciliação manual/outro worktree,
        # não é falha ativa de auto-push. Se ele também não pertence mais ao HEAD
        # local, foi supersedido por reconciliação e não deve manter alerta vermelho.
        if ! grep -q "auto-push OK commit=${commit}" "$PUSH_LOG"; then
            if git -C "$BASE_DIR" merge-base --is-ancestor "$commit" origin/main 2>/dev/null; then
                continue
            fi
            if ! git -C "$BASE_DIR" merge-base --is-ancestor "$commit" HEAD 2>/dev/null; then
                continue
            fi
            NEW_FAILURES+=("${ts} commit=${commit} [START sem OK]")
        fi
    fi
done <<< "$WINDOW_LINES"

# ─── Detectar erros explícitos na janela ─────────────────────────────────────
# IMPORTANTE: Só checa linhas que NÃO sejam START/OK/SKIP do auto-push, pois
# mensagens de commit podem conter palavras como "timeout", "error" inocentes
# (ex: "docs: F1 curl timeout fix" — não é erro de push).
ERROR_PATTERNS="rejected|failed to push|Authentication failed|fatal:|error:|timeout|Permission denied"
EXPLICIT_ERRORS=()
while IFS= read -r line; do
    # Pular linhas de START/OK/SKIP — mensagens de commit têm palavras inocentes
    if echo "$line" | grep -qE "auto-push (START|OK|SKIP)|discord-notify"; then
        continue
    fi
    if echo "$line" | grep -qiE "$ERROR_PATTERNS"; then
        EXPLICIT_ERRORS+=("$line")
    fi
done <<< "$WINDOW_LINES"

# ─── Detectar último auto-push OK (para report) ──────────────────────────────
if grep -q "auto-push OK" "$PUSH_LOG"; then
    LAST_OK_LINE="$(grep "auto-push OK" "$PUSH_LOG" | tail -1)"
    LAST_OK_COMMIT="$(echo "$LAST_OK_LINE" | grep -oP 'commit=\K[a-f0-9]+')" || true
    LAST_OK_TS="$(echo "$LAST_OK_LINE" | grep -oP '\[\K[^\]]+' | head -1)" || true
fi

# ─── Detectar divergência estrutural do repo ──────────────────────────────────
# O log sozinho não basta: se o watcher estiver em branch lateral, ou travado
# antes de commitar, o log pode parecer OK enquanto GitHub/main fica velho.
REPO_FAILURES=()
AUTO_COMMIT_GUARDRAIL_BLOCKED=0
CURRENT_BRANCH="$(git -C "$BASE_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    REPO_FAILURES+=("repo branch=$CURRENT_BRANCH [esperado main]")
fi

# Fetch é read-only; usar a mesma identidade SSH restrita do hook de push.
if GIT_SSH_COMMAND="${MGS_AUTOPUSH_GIT_SSH_COMMAND:-$GIT_SSH_COMMAND_DEFAULT}" \
    git -C "$BASE_DIR" fetch --quiet origin main 2>/dev/null; then
    LOCAL_HEAD="$(git -C "$BASE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    ORIGIN_MAIN="$(git -C "$BASE_DIR" rev-parse --short origin/main 2>/dev/null || echo unknown)"
    if [[ "$CURRENT_BRANCH" == "main" && "$LOCAL_HEAD" != "$ORIGIN_MAIN" ]]; then
        REPO_FAILURES+=("main local=$LOCAL_HEAD origin/main=$ORIGIN_MAIN [push pendente]")
    fi
else
    REPO_FAILURES+=("git fetch origin/main falhou [não foi possível validar GitHub]")
fi

DIRTY_COUNT="$(git -C "$BASE_DIR" status --porcelain=v1 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${DIRTY_COUNT:-0}" != "0" ]]; then
    log "INFO: working tree tem ${DIRTY_COUNT} mudança(s) local(is); não conta como falha porque auto-commit pode estar em debounce/guardrail"
fi

# Se o auto-commit watcher estiver abortando por guardrail, o auto-push nunca
# chega a iniciar. Alertar apenas se o bloqueio for o estado mais recente do
# watcher; bloqueios históricos dentro da janela não devem manter falso vermelho
# depois de um commit/skip limpo posterior.
if [[ -f "$AUTO_COMMIT_LOG" ]]; then
    LAST_BLOCK_EPOCH=0
    LAST_CLEAR_EPOCH=0
    while IFS= read -r line; do
        ts="$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || true)"
        [[ -n "$ts" ]] || continue
        line_epoch="$(date -d "$ts" +%s 2>/dev/null || true)"
        [[ -n "$line_epoch" ]] || continue
        (( line_epoch >= CUTOFF_EPOCH )) || continue
        if echo "$line" | grep -q "BLOQUEADO: arquivo sensível detectado"; then
            LAST_BLOCK_EPOCH="$line_epoch"
        elif echo "$line" | grep -qE "Commit OK:|Working tree limpo, skipping|ERRO no commit"; then
            LAST_CLEAR_EPOCH="$line_epoch"
        fi
    done < <(tail -500 "$AUTO_COMMIT_LOG" 2>/dev/null || true)
    if (( LAST_BLOCK_EPOCH > LAST_CLEAR_EPOCH )); then
        AUTO_COMMIT_GUARDRAIL_BLOCKED=1
        REPO_FAILURES+=("auto-commit bloqueado por guardrail sensível [commit/push não iniciou]")
    fi
fi

# ─── Contabilizar falhas ──────────────────────────────────────────────────────
TOTAL_NEW_FAILURES=$(( ${#NEW_FAILURES[@]} + ${#EXPLICIT_ERRORS[@]} + ${#REPO_FAILURES[@]} ))
ALL_FAILURE_DETAILS=("${NEW_FAILURES[@]}" "${EXPLICIT_ERRORS[@]}" "${REPO_FAILURES[@]}")

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: total_failures=${TOTAL_NEW_FAILURES} starts_sem_ok=${#NEW_FAILURES[@]} explicit_errors=${#EXPLICIT_ERRORS[@]} repo_failures=${#REPO_FAILURES[@]} last_ok=${LAST_OK_COMMIT:-n/a} dirty=${DIRTY_COUNT:-0}"
    if (( TOTAL_NEW_FAILURES > 0 )); then
        printf '%s\n' "${ALL_FAILURE_DETAILS[@]}" | sed 's/^/[DRY-RUN] /'
    fi
    exit 0
fi

# ─── Lógica de estado ─────────────────────────────────────────────────────────
ALERT_WAS_ACTIVE=false
if (( CONSECUTIVE >= THRESHOLD )); then
    ALERT_WAS_ACTIVE=true
fi

if (( TOTAL_NEW_FAILURES > 0 )); then
    # Contar ciclos consecutivos com falha, não a quantidade de sintomas no
    # mesmo ciclo. A terceira leitura falha aciona a intervenção do Zeus.
    NEW_CONSECUTIVE=$(( CONSECUTIVE + 1 ))
    FAILURE_JSON="$(printf '%s\n' "${ALL_FAILURE_DETAILS[@]}" | jq -R . | jq -s .)"

    log "FALHA detectada: ${TOTAL_NEW_FAILURES} nova(s), total consecutivo=${NEW_CONSECUTIVE}"

    # Verificar anti-spam. Todo incidente recorrente, inclusive guardrail,
    # entra no mesmo contrato: intervenção automática na terceira falha.
    SEND_ALERT=false
    SHOULD_EVALUATE_ALERT=false
    if (( NEW_CONSECUTIVE >= THRESHOLD )); then
        SHOULD_EVALUATE_ALERT=true
    fi

    if [[ "$SHOULD_EVALUATE_ALERT" == "true" ]]; then
        if [[ "$LAST_ALERT" == "null" ]] || (( CONSECUTIVE == 0 )); then
            SEND_ALERT=true
        else
            LAST_ALERT_EPOCH="$(date -d "$LAST_ALERT" +%s 2>/dev/null || echo 0)"
            ANTI_SPAM_SECS=$(( ANTI_SPAM_HOURS * 3600 ))
            if (( NOW_EPOCH - LAST_ALERT_EPOCH > ANTI_SPAM_SECS )); then
                SEND_ALERT=true
            else
                log "Anti-spam: alerta já enviado há menos de ${ANTI_SPAM_HOURS}h — suprimindo"
            fi
        fi
    fi

    # Atualizar state
    LAST_DETAIL="${ALL_FAILURE_DETAILS[0]:-desconhecido}"
    if [[ "$SEND_ALERT" == "true" ]]; then
        ALERT_TS="$NOW_ISO"
        log "Enviando alerta Discord — ${NEW_CONSECUTIVE} falhas consecutivas"
        PAYLOAD=$(jq -n \
            --arg n "$NEW_CONSECUTIVE" \
            --arg detail "$LAST_DETAIL" \
            --arg ok_ts "${LAST_OK_TS:-nunca}" \
            '{content:"<@344196393512075265> alerta de auto-push", embeds:[{title:"Auto-push falhando", color:15158332, fields:[{name:"Falhas consecutivas", value:$n, inline:true}, {name:"Último push OK", value:$ok_ts, inline:true}, {name:"Último erro", value:("```text\n"+$detail+"\n```"), inline:false}, {name:"Ação", value:"Intervenção automática do Zeus acionada na 3ª falha; investigar causa-raiz, corrigir e validar.", inline:false}]}]}')
        post_discord_payload "$PAYLOAD" >/dev/null || exit 2
    else
        ALERT_TS="$LAST_ALERT"
    fi

    jq --arg ts "$NOW_ISO" \
       --argjson c "$NEW_CONSECUTIVE" \
       --arg at "$ALERT_TS" \
       --argjson fd "$FAILURE_JSON" \
       '.last_check = $ts | .consecutive_failures = $c | .last_alert_sent = $at | .last_failure_details = $fd' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

else
    # Zero falhas na janela
    if (( CONSECUTIVE > 0 )); then
        log "RESOLVIDO: zero falhas detectadas (anterior: ${CONSECUTIVE} consecutivas)"

        # Enviar "RESOLVIDO" se havia alerta ativo
        if [[ "$ALERT_WAS_ACTIVE" == "true" ]]; then
            log "Enviando alerta RESOLVIDO para Discord"
            PAYLOAD=$(jq -n \
                --arg n "$CONSECUTIVE" \
                --arg commit "${LAST_OK_COMMIT:-desconhecido}" \
                --arg ts "${LAST_OK_TS:-desconhecido}" \
                '{content:"", embeds:[{title:"Auto-push restabelecido", color:3066993, fields:[{name:"Falhas anteriores", value:$n, inline:true}, {name:"Último commit OK", value:("`"+$commit+"`"), inline:true}, {name:"Horário", value:$ts, inline:false}]}]}')
            post_discord_payload "$PAYLOAD" >/dev/null || exit 2
        fi
    else
        log "OK: zero falhas detectadas na janela de ${WINDOW_MINUTES}min"
    fi

    jq --arg ts "$NOW_ISO" \
       '.last_check = $ts | .consecutive_failures = 0 | .last_failure_details = []' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

log "Concluído. consecutive_failures=$(jq -r '.consecutive_failures' "$STATE_FILE") last_ok=${LAST_OK_COMMIT:-n/a}"
