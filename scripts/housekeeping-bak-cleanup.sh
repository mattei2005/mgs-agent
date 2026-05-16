#!/usr/bin/env bash
# =============================================================================
# housekeeping-bak-cleanup.sh — Remove arquivos *.bak* mais antigos que N dias
#
# Roda diariamente via cron. Cobre locais conhecidos onde patches deixam .bak:
#   - /root/.hermes/         (configs Hermes, profiles, .env)
#   - /root/mgs-agent/       (scripts, skills, data)
#   - /root/backups/         (snapshots pré-update)
#   - /tmp                  (temporários antigos)
#
# Proteções:
#   - NUNCA deleta canônicos (SOUL.md, config.yaml, .env, *.sh sem .bak)
#   - find -name "*.bak*" só pega arquivos com .bak no nome
#   - Loga tudo em /root/mgs-agent/logs/housekeeping.log
#   - Posta resumo no Discord (#alerts-infra) se algo foi deletado
#   - --dry-run lista o que seria deletado sem remover nem notificar
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

RETENTION_DAYS="${RETENTION_DAYS:-15}"
LOG=/root/mgs-agent/logs/housekeeping.log
BASE_DIR=/root/mgs-agent

# Carregar credenciais 1Password
set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

log() { echo "[$(date -Iseconds)] housekeeping: $*" | tee -a "$LOG"; }

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "=== START DRY-RUN — retention=${RETENTION_DAYS} dias ==="
else
    log "=== START — retention=${RETENTION_DAYS} dias ==="
fi

# ─── Coletar arquivos a deletar ANTES de deletar (pra logar/notificar) ──────
TO_DELETE=$(find /root/.hermes /root/mgs-agent /root/backups /tmp \
    -type f -name "*.bak*" \
    -mtime +"${RETENTION_DAYS}" \
    ! -path '*/.git/*' \
    ! -path '*/node_modules/*' \
    2>/dev/null || true)

COUNT=$(printf "%s" "$TO_DELETE" | grep -c "^." || true)
COUNT="${COUNT:-0}"

if [[ -z "$TO_DELETE" || "$COUNT" -eq 0 ]]; then
    log "Nada a deletar (zero arquivos *.bak* com mais de ${RETENTION_DAYS} dias)"
    log "=== END (no-op) ==="
    exit 0
fi

# Calcular tamanho total antes de deletar
TOTAL_SIZE=$(echo "$TO_DELETE" | xargs -d '\n' du -cb 2>/dev/null | tail -1 | awk '{print $1}')
TOTAL_MB=$(echo "scale=2; ${TOTAL_SIZE:-0}/1024/1024" | bc)

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: encontrados ${COUNT} arquivos (${TOTAL_MB} MB). Nada será deletado."
    echo "$TO_DELETE" | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        log "  would rm $f"
    done
    DIRS_CANDIDATE=$(find /root/backups -type d -empty -mtime +"${RETENTION_DAYS}" -print 2>/dev/null | wc -l)
    log "DRY-RUN: ${DIRS_CANDIDATE} diretórios vazios seriam removidos em /root/backups"
    log "=== END DRY-RUN — candidatos ${COUNT} arquivos / ${TOTAL_MB} MB ==="
    exit 0
fi

log "Encontrados ${COUNT} arquivos (${TOTAL_MB} MB). Deletando..."

# ─── Deletar ────────────────────────────────────────────────────────────────
echo "$TO_DELETE" | while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if rm -f "$f" 2>>"$LOG"; then
        log "  rm $f"
    else
        log "  FAIL $f"
    fi
done

# ─── Limpar diretórios vazios deixados pra trás (snapshots antigos) ─────────
DIRS_REMOVED=$(find /root/backups -type d -empty -mtime +"${RETENTION_DAYS}" -delete -print 2>/dev/null | wc -l)
if [[ "$DIRS_REMOVED" -gt 0 ]]; then
    log "Removidos ${DIRS_REMOVED} diretórios vazios em /root/backups"
fi

# ─── Notificar Discord ──────────────────────────────────────────────────────
WEBHOOK=$(op item get "Discord Webhook - Alerts Infra Channel" \
    --vault "MGS Conteúdo" \
    --fields label=webhook_url \
    --reveal 2>/dev/null || echo "")

if [[ "$WEBHOOK" == https://* ]]; then
    HOST=$(hostname)
    PAYLOAD=$(jq -n \
        --arg host "$HOST" \
        --arg retention "${RETENTION_DAYS} dias" \
        --arg files "$COUNT" \
        --arg size "${TOTAL_MB} MB" \
        --arg dirs "$DIRS_REMOVED" \
        '{content:"", embeds:[{title:"Housekeeping .bak executado", color:3447003, fields:[{name:"Host", value:$host, inline:true}, {name:"Retenção", value:$retention, inline:true}, {name:"Arquivos deletados", value:$files, inline:true}, {name:"Espaço liberado", value:$size, inline:true}, {name:"Diretórios vazios removidos", value:$dirs, inline:true}]}]}')
    curl -s -X POST "$WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --max-time 10 > /dev/null 2>&1 || log "WARN: Discord notify falhou"
    log "Discord notificado"
else
    log "WARN: WEBHOOK vazio — sem notificação Discord"
fi

log "=== END — deletados ${COUNT} arquivos / ${TOTAL_MB} MB ==="
