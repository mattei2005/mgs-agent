#!/usr/bin/env bash
# =============================================================================
# monitor-auto-push.sh — Monitor de falhas no auto-push do mgs-agent
# Roda a cada 15min via cron. Detecta STARTs sem OK correspondente,
# erros explícitos no log, e envia alerta Discord se threshold atingido.
# Estado persistido em data/auto-push-monitor.json
# =============================================================================

set -euo pipefail

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PUSH_LOG="${BASE_DIR}/logs/auto-push.log"
STATE_FILE="${BASE_DIR}/data/auto-push-monitor.json"
WINDOW_MINUTES="${WINDOW_MINUTES:-60}"
THRESHOLD="${THRESHOLD:-3}"
ANTI_SPAM_HOURS="${ANTI_SPAM_HOURS:-2}"

# ─── Credenciais via 1Password ────────────────────────────────────────────────
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true

WEBHOOK_URL="$(op item get "Discord Webhook - Zeus Channel" \
    --vault 'MGS Conteúdo' \
    --fields label=webhook_url \
    --reveal 2>/dev/null)"

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
        # Verificar se existe OK para esse commit no log completo
        if ! grep -q "auto-push OK commit=${commit}" "$PUSH_LOG"; then
            NEW_FAILURES+=("${ts} commit=${commit} [START sem OK]")
        fi
    fi
done <<< "$WINDOW_LINES"

# ─── Detectar erros explícitos na janela ─────────────────────────────────────
ERROR_PATTERNS="rejected|failed to push|Authentication failed|fatal:|error:|timeout|Permission denied"
EXPLICIT_ERRORS=()
while IFS= read -r line; do
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

# ─── Contabilizar falhas ──────────────────────────────────────────────────────
TOTAL_NEW_FAILURES=$(( ${#NEW_FAILURES[@]} + ${#EXPLICIT_ERRORS[@]} ))
ALL_FAILURE_DETAILS=("${NEW_FAILURES[@]}" "${EXPLICIT_ERRORS[@]}")

# ─── Lógica de estado ─────────────────────────────────────────────────────────
ALERT_WAS_ACTIVE=false
if (( CONSECUTIVE >= THRESHOLD )); then
    ALERT_WAS_ACTIVE=true
fi

if (( TOTAL_NEW_FAILURES > 0 )); then
    # Incrementar falhas consecutivas
    NEW_CONSECUTIVE=$(( CONSECUTIVE + TOTAL_NEW_FAILURES ))
    FAILURE_JSON="$(printf '%s\n' "${ALL_FAILURE_DETAILS[@]}" | jq -R . | jq -s .)"

    log "FALHA detectada: ${TOTAL_NEW_FAILURES} nova(s), total consecutivo=${NEW_CONSECUTIVE}"

    # Verificar anti-spam
    SEND_ALERT=false
    if (( NEW_CONSECUTIVE >= THRESHOLD )); then
        if [[ "$LAST_ALERT" == "null" ]]; then
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
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg n "$NEW_CONSECUTIVE" \
                --arg detail "$LAST_DETAIL" \
                --arg ok_ts "${LAST_OK_TS:-nunca}" \
                '{content: "🚨 **AUTO-PUSH FALHANDO**\nFalhas consecutivas: \($n)\nÚltimo erro: \($detail)\nÚltimo push OK: \($ok_ts)\nAção: investigar `/root/mgs-agent/logs/auto-push.log`"}')" \
            --max-time 10 >/dev/null
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
        if [[ "$ALERT_WAS_ACTIVE" == "true" ]] && [[ -n "$WEBHOOK_URL" ]]; then
            log "Enviando alerta RESOLVIDO para Discord"
            curl -s -X POST "$WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "$(jq -n \
                    --arg n "$CONSECUTIVE" \
                    --arg commit "${LAST_OK_COMMIT:-desconhecido}" \
                    --arg ts "${LAST_OK_TS:-desconhecido}" \
                    '{content: "✅ **AUTO-PUSH RESTABELECIDO**\nApós \($n) falhas consecutivas, push voltou a funcionar.\nÚltimo commit OK: \($commit) em \($ts)"}')" \
                --max-time 10 >/dev/null
        fi
    else
        log "OK: zero falhas detectadas na janela de ${WINDOW_MINUTES}min"
    fi

    jq --arg ts "$NOW_ISO" \
       '.last_check = $ts | .consecutive_failures = 0 | .last_failure_details = []' \
       "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

log "Concluído. consecutive_failures=$(jq -r '.consecutive_failures' "$STATE_FILE") last_ok=${LAST_OK_COMMIT:-n/a}"
