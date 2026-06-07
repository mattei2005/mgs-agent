#!/usr/bin/env bash
# =============================================================================
# housekeeping-bak-cleanup.sh — Remove backups antigos preservando o último
#
# Roda diariamente via cron. Cobre locais conhecidos onde patches deixam backups:
#   - /root/.hermes/         (configs Hermes, profiles, .env)
#   - /root/mgs-agent/       (scripts, skills, data)
#   - /root/backups/         (snapshots pré-update)
#   - /tmp                  (temporários antigos)
#
# Proteções:
#   - NUNCA deleta canônicos (SOUL.md, config.yaml, .env, *.sh sem marcador backup)
#   - Só pega nomes com marcador explícito de backup: *.bak*, *.backup*, *.old,
#     *.orig, *~
#   - Preserva SEMPRE o arquivo mais recente de cada família de backup, mesmo
#     acima da retenção. Se só existe 1 arquivo na família, não deleta.
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
CANDIDATES_FILE="$(mktemp)"
KEEP_FILE="$(mktemp)"
DELETE_FILE="$(mktemp)"
trap 'rm -f "$CANDIDATES_FILE" "$KEEP_FILE" "$DELETE_FILE"' EXIT

# Carregar credenciais 1Password apenas para notificação em execução real.
set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

log() { echo "[$(date -Iseconds)] housekeeping: $*" | tee -a "$LOG"; }

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "=== START DRY-RUN — retention=${RETENTION_DAYS} dias, preserve_latest=1 ==="
else
    log "=== START — retention=${RETENTION_DAYS} dias, preserve_latest=1 ==="
fi

# ─── Coletar candidatos e decidir o que pode ser deletado ────────────────────
# A regra é calculada em Python para evitar bugs de parsing em nomes com espaço.
python3 - "$RETENTION_DAYS" "$CANDIDATES_FILE" "$KEEP_FILE" "$DELETE_FILE" <<'PY'
import os
import re
import sys
import time
from pathlib import Path

retention_days = int(sys.argv[1])
candidates_path = Path(sys.argv[2])
keep_path = Path(sys.argv[3])
delete_path = Path(sys.argv[4])

roots = [Path('/root/.hermes'), Path('/root/mgs-agent'), Path('/root/backups'), Path('/tmp')]
skip_parts = {'.git', 'node_modules'}
now = time.time()
cutoff = now - retention_days * 86400

backup_name_re = re.compile(r'(\.bak|\.backup|\.old|\.orig|~)', re.IGNORECASE)

# Normaliza nomes comuns de backup para família estável:
#   SOUL.md.bak-20260602-195530                 -> SOUL.md
#   file.md-pre-ceo-corrections-20260605.bak    -> file.md
#   crontab-root-20260603-151254-webshare.bak   -> crontab-root
#   config.yaml.old                             -> config.yaml
#   file~                                      -> file

def family_base(name: str) -> str:
    n = name
    n = re.sub(r'~$', '', n)
    n = re.sub(r'(?i)(\.bak|\.backup|\.old|\.orig)([-_.].*)?$', '', n)
    n = re.sub(r'(?i)-pre-[^-]+.*$', '', n)
    n = re.sub(r'(?i)-pre-.*$', '', n)
    n = re.sub(r'(?i)-backup[-_.].*$', '', n)
    n = re.sub(r'(?i)-bak[-_.].*$', '', n)
    n = re.sub(r'[-_.]?\d{8}[-_.]?\d{4,6}.*$', '', n)
    n = re.sub(r'[-_.]?\d{14}.*$', '', n)
    n = n.rstrip('-_. ')
    return n or name

records = []
for root in roots:
    if not root.exists():
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_parts]
        parent = Path(dirpath)
        for filename in filenames:
            if not backup_name_re.search(filename):
                continue
            p = parent / filename
            try:
                st = p.stat()
            except OSError:
                continue
            if not p.is_file():
                continue
            family = f"{parent}|{family_base(filename).lower()}"
            records.append({
                'path': str(p),
                'mtime': st.st_mtime,
                'size': st.st_size,
                'family': family,
            })

by_family = {}
for r in records:
    by_family.setdefault(r['family'], []).append(r)

keep = []
delete = []
for family, items in by_family.items():
    newest = max(items, key=lambda x: (x['mtime'], x['path']))
    newest_path = newest['path']
    for item in items:
        reason = None
        if item['path'] == newest_path:
            reason = 'preserve_latest'
            keep.append((item, reason))
        elif item['mtime'] > cutoff:
            reason = 'inside_retention'
            keep.append((item, reason))
        else:
            delete.append(item)

records.sort(key=lambda x: (x['family'], -x['mtime'], x['path']))
keep.sort(key=lambda x: (x[0]['family'], -x[0]['mtime'], x[0]['path']))
delete.sort(key=lambda x: (x['family'], x['mtime'], x['path']))

with candidates_path.open('w') as f:
    for r in records:
        f.write(f"{int(r['mtime'])}\t{r['size']}\t{r['family']}\t{r['path']}\n")
with keep_path.open('w') as f:
    for r, reason in keep:
        f.write(f"{reason}\t{int(r['mtime'])}\t{r['size']}\t{r['family']}\t{r['path']}\n")
with delete_path.open('w') as f:
    for r in delete:
        f.write(f"{int(r['mtime'])}\t{r['size']}\t{r['family']}\t{r['path']}\n")
PY

COUNT=$(wc -l < "$DELETE_FILE" | tr -d ' ')
KEEP_COUNT=$(wc -l < "$KEEP_FILE" | tr -d ' ')
CANDIDATE_COUNT=$(wc -l < "$CANDIDATES_FILE" | tr -d ' ')
TOTAL_SIZE=$(awk -F '\t' '{sum += $2} END {print sum+0}' "$DELETE_FILE")
TOTAL_MB=$(awk -v bytes="${TOTAL_SIZE:-0}" 'BEGIN {printf "%.2f", bytes/1024/1024}')

if [[ "$COUNT" -eq 0 ]]; then
    log "Nada a deletar (${CANDIDATE_COUNT} backup(s) encontrados; ${KEEP_COUNT} preservado(s) por último/retencão)"
    log "=== END (no-op) ==="
    exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: encontrados ${CANDIDATE_COUNT} backup(s); ${COUNT} seriam deletados (${TOTAL_MB} MB); ${KEEP_COUNT} preservados."
    awk -F '\t' '{print $4}' "$DELETE_FILE" | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        log "  would rm $f"
    done
    awk -F '\t' '$1 == "preserve_latest" {print $5}' "$KEEP_FILE" | head -30 | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        log "  keep latest $f"
    done
    DIRS_CANDIDATE=$(find /root/backups -type d -empty -mtime +"${RETENTION_DAYS}" -print 2>/dev/null | wc -l)
    log "DRY-RUN: ${DIRS_CANDIDATE} diretórios vazios seriam removidos em /root/backups"
    log "=== END DRY-RUN — candidatos ${COUNT} arquivos / ${TOTAL_MB} MB ==="
    exit 0
fi

log "Encontrados ${CANDIDATE_COUNT} backup(s); deletando ${COUNT} antigo(s) (${TOTAL_MB} MB); preservando ${KEEP_COUNT}."

# ─── Deletar ────────────────────────────────────────────────────────────────
awk -F '\t' '{print $4}' "$DELETE_FILE" | while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if rm -f -- "$f" 2>>"$LOG"; then
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
        --arg preserved "$KEEP_COUNT" \
        --arg size "${TOTAL_MB} MB" \
        --arg dirs "$DIRS_REMOVED" \
        '{content:"", embeds:[{title:"Housekeeping de backups executado", color:3447003, fields:[{name:"Host", value:$host, inline:true}, {name:"Retenção", value:$retention, inline:true}, {name:"Arquivos deletados", value:$files, inline:true}, {name:"Backups preservados", value:$preserved, inline:true}, {name:"Espaço liberado", value:$size, inline:true}, {name:"Diretórios vazios removidos", value:$dirs, inline:true}]}]}')
    curl -s -X POST "$WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --max-time 10 > /dev/null 2>&1 || log "WARN: Discord notify falhou"
    log "Discord notificado"
else
    log "WARN: WEBHOOK vazio — sem notificação Discord"
fi

log "=== END — deletados ${COUNT} arquivos / ${TOTAL_MB} MB ==="
