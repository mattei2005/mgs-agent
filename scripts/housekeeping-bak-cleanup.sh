#!/usr/bin/env bash
# =============================================================================
# housekeeping-bak-cleanup.sh — Remove backups antigos preservando o último
#
# Roda duas vezes por semana via cron. Cobre locais conhecidos onde patches deixam backups:
#   - /root/.hermes/         (configs Hermes, profiles, .env)
#   - /root/mgs-agent/       (scripts, skills, data)
#   - /root/backups/         (snapshots pré-update)
#   - /tmp                  (temporários antigos)
#   - /root/mgs-agent/reports/hermes-updates/**/hermes-profiles-backup-*.tar.gz
#                            (backups grandes de profiles gerados por update Hermes)
#
# Proteções:
#   - NUNCA deleta canônicos (SOUL.md, config.yaml, .env, *.sh sem marcador backup)
#   - Backups pequenos: só pega nomes com marcador explícito de backup: *.bak*,
#     *.backup*, *.old, *.orig, *~
#   - Backups grandes Hermes update: aplica retenção dedicada, preservando apenas
#     o mais recente globalmente (default: 1) e deletando o restante acima de
#     HERMES_UPDATE_BACKUP_RETENTION_DAYS (default: 2 dias).
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
HERMES_UPDATE_BACKUP_RETENTION_DAYS="${HERMES_UPDATE_BACKUP_RETENTION_DAYS:-2}"
HERMES_UPDATE_BACKUP_KEEP_LATEST="${HERMES_UPDATE_BACKUP_KEEP_LATEST:-1}"
BASE_DIR=/root/mgs-agent
LOG="${MGS_HOUSEKEEPING_LOG:-${BASE_DIR}/logs/housekeeping.log}"
SCAN_ROOTS="${MGS_HOUSEKEEPING_SCAN_ROOTS:-/root/.hermes:/root/mgs-agent:/root/backups:/tmp}"
BACKUPS_ROOT="${MGS_HOUSEKEEPING_BACKUPS_ROOT:-/root/backups}"
HERMES_UPDATE_ROOT="${MGS_HOUSEKEEPING_HERMES_UPDATE_ROOT:-${BASE_DIR}/reports/hermes-updates}"
DISCORD_CHANNEL_ID="${MGS_DISCORD_CHANNEL_ID_OVERRIDE:-1498132022634483894}"
DISCORD_API_URL="${MGS_DISCORD_API_URL_OVERRIDE:-https://discord.com/api/v10/channels/${DISCORD_CHANNEL_ID}/messages}"
CANDIDATES_FILE="$(mktemp)"
KEEP_FILE="$(mktemp)"
DELETE_FILE="$(mktemp)"
trap 'rm -f "$CANDIDATES_FILE" "$KEEP_FILE" "$DELETE_FILE"' EXIT

# Token local do bot Zeus; housekeeping não consulta o 1Password.
set -a
# shellcheck source=/dev/null
source "/root/.hermes/profiles/zeus/.env" 2>/dev/null || true
set +a
BOT_TOKEN="${MGS_DISCORD_BOT_TOKEN_OVERRIDE:-${DISCORD_BOT_TOKEN:-}}"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -Iseconds)] housekeeping: $*" | tee -a "$LOG"; }

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "=== START DRY-RUN — retention=${RETENTION_DAYS} dias, preserve_latest=1 ==="
else
    log "=== START — retention=${RETENTION_DAYS} dias, preserve_latest=1 ==="
fi

# ─── Coletar candidatos e decidir o que pode ser deletado ────────────────────
# A regra é calculada em Python para evitar bugs de parsing em nomes com espaço.
python3 - "$RETENTION_DAYS" "$CANDIDATES_FILE" "$KEEP_FILE" "$DELETE_FILE" "$SCAN_ROOTS" <<'PY'
import os
import re
import sys
import time
from pathlib import Path

retention_days = int(sys.argv[1])
candidates_path = Path(sys.argv[2])
keep_path = Path(sys.argv[3])
delete_path = Path(sys.argv[4])

roots = [Path(value) for value in sys.argv[5].split(os.pathsep) if value]
skip_parts = {'.git', 'node_modules'}
now = time.time()
cutoff = now - retention_days * 86400

backup_name_re = re.compile(
    r'(?i)(?:\.bak(?:[-_.].*)?|\.backup(?:[-_.].*)?|\.old(?:[-_.].*)?|\.orig(?:[-_.].*)?|~)$'
)

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

# ─── Retenção dedicada para backups grandes de update Hermes ────────────────
# O fluxo controlado de update pode gerar vários tarballs de ~1.5GB no mesmo dia.
# Eles não têm extensão .bak, então a limpeza genérica acima não os alcança.
HERMES_DELETE_FILE="$(mktemp)"
trap 'rm -f "$CANDIDATES_FILE" "$KEEP_FILE" "$DELETE_FILE" "$HERMES_DELETE_FILE"' EXIT
python3 - "$HERMES_UPDATE_BACKUP_RETENTION_DAYS" "$HERMES_UPDATE_BACKUP_KEEP_LATEST" "$HERMES_DELETE_FILE" "$HERMES_UPDATE_ROOT" <<'PY'
import sys
import time
from pathlib import Path

retention_days = int(sys.argv[1])
keep_latest = int(sys.argv[2])
out = Path(sys.argv[3])
root = Path(sys.argv[4])
cutoff = time.time() - retention_days * 86400
records = []
if root.exists():
    for p in root.glob('**/hermes-profiles-backup*.tar.gz'):
        try:
            st = p.stat()
        except OSError:
            continue
        if p.is_file():
            records.append((st.st_mtime, st.st_size, str(p)))
records.sort(key=lambda x: (x[0], x[2]), reverse=True)
keep = {path for _, _, path in records[:keep_latest]}
with out.open('w') as f:
    for mtime, size, path in records:
        if path in keep:
            continue
        if mtime < cutoff:
            f.write(f"{int(mtime)}\t{size}\thermes-update-backup\t{path}\n")
PY

HERMES_COUNT=$(wc -l < "$HERMES_DELETE_FILE" | tr -d ' ')
HERMES_TOTAL_SIZE=$(awk -F '\t' '{sum += $2} END {print sum+0}' "$HERMES_DELETE_FILE")
HERMES_TOTAL_MB=$(awk -v bytes="${HERMES_TOTAL_SIZE:-0}" 'BEGIN {printf "%.2f", bytes/1024/1024}')
TOTAL_COUNT=$((COUNT + HERMES_COUNT))
TOTAL_SIZE_ALL=$((TOTAL_SIZE + HERMES_TOTAL_SIZE))
TOTAL_MB_ALL=$(awk -v bytes="${TOTAL_SIZE_ALL:-0}" 'BEGIN {printf "%.2f", bytes/1024/1024}')
HERMES_PRESERVED_COUNT=$(find "$HERMES_UPDATE_ROOT" -type f -name 'hermes-profiles-backup*.tar.gz' 2>/dev/null | wc -l | tr -d ' ')

if [[ "$TOTAL_COUNT" -eq 0 ]]; then
    log "Nada a deletar (${CANDIDATE_COUNT} backup(s) pequenos encontrados; ${KEEP_COUNT} preservado(s); Hermes update tarballs elegíveis=0)"
    log "=== END (no-op) ==="
    exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: encontrados ${CANDIDATE_COUNT} backup(s) pequenos; ${COUNT} seriam deletados (${TOTAL_MB} MB); ${KEEP_COUNT} preservados."
    awk -F '\t' '{print $4}' "$DELETE_FILE" | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        log "  would rm $f"
    done
    if [[ "$HERMES_COUNT" -gt 0 ]]; then
        log "DRY-RUN: Hermes update tarballs: ${HERMES_COUNT} seriam deletados (${HERMES_TOTAL_MB} MB); keep_latest=${HERMES_UPDATE_BACKUP_KEEP_LATEST}; retention=${HERMES_UPDATE_BACKUP_RETENTION_DAYS}d."
        awk -F '\t' '{print $4}' "$HERMES_DELETE_FILE" | while IFS= read -r f; do
            [[ -z "$f" ]] && continue
            log "  would rm hermes-update $f"
        done
    fi
    # Limit in awk instead of piping through head: with `set -o pipefail`,
    # head closes early and can make awk exit on SIGPIPE, falsely failing an
    # otherwise successful dry-run when more than 30 families are preserved.
    awk -F '\t' '$1 == "preserve_latest" && shown < 30 {print $5; shown++}' "$KEEP_FILE" | while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        log "  keep latest $f"
    done
    DIRS_CANDIDATE=0
    if [[ -d "$BACKUPS_ROOT" ]]; then
        DIRS_CANDIDATE=$(find "$BACKUPS_ROOT" -mindepth 1 -type d -empty -mtime +"${RETENTION_DAYS}" -print 2>/dev/null | wc -l)
    fi
    log "DRY-RUN: ${DIRS_CANDIDATE} diretórios vazios seriam removidos em /root/backups"
    log "=== END DRY-RUN — candidatos ${TOTAL_COUNT} arquivos / ${TOTAL_MB_ALL} MB ==="
    exit 0
fi

log "Encontrados ${CANDIDATE_COUNT} backup(s) pequenos + Hermes update tarballs; deletando ${TOTAL_COUNT} antigo(s) (${TOTAL_MB_ALL} MB); preservando ${KEEP_COUNT} pequenos + ${HERMES_PRESERVED_COUNT} Hermes update recentes."

# ─── Deletar e verificar cada remoção ────────────────────────────────────────
DELETE_FAILURES=0
while IFS=$'\t' read -r _mtime _size _family f; do
    [[ -z "$f" ]] && continue
    if rm -f -- "$f" 2>>"$LOG" && [[ ! -e "$f" ]]; then
        log "  rm $f"
    else
        log "  FAIL $f"
        DELETE_FAILURES=$((DELETE_FAILURES + 1))
    fi
done < <(awk -F '\t' 'NF >= 4 {print}' "$DELETE_FILE" "$HERMES_DELETE_FILE")

if (( DELETE_FAILURES > 0 )); then
    log "ERRO: ${DELETE_FAILURES} arquivo(s) permaneceram após tentativa de remoção"
    exit 1
fi

# ─── Limpar diretórios vazios deixados pra trás (snapshots antigos) ─────────
DIRS_REMOVED=$({
    if [[ -d "$BACKUPS_ROOT" ]]; then
        find "$BACKUPS_ROOT" -mindepth 1 -type d -empty -mtime +"${RETENTION_DAYS}" -delete -print 2>/dev/null
    fi
    if [[ -d "$HERMES_UPDATE_ROOT" ]]; then
        find "$HERMES_UPDATE_ROOT" -mindepth 1 -type d -empty -mtime +"${HERMES_UPDATE_BACKUP_RETENTION_DAYS}" -delete -print 2>/dev/null
    fi
} | wc -l)
if [[ "$DIRS_REMOVED" -gt 0 ]]; then
    log "Removidos ${DIRS_REMOVED} diretórios vazios"
fi

# ─── Notificar Discord diretamente pelo bot Zeus ─────────────────────────────
if [[ -n "$BOT_TOKEN" ]]; then
    HOST=$(hostname)
    PRESERVED_LABEL="${KEEP_COUNT} pequenos + ${HERMES_PRESERVED_COUNT} tarballs Hermes"
    STATUS_LABEL="OK — baixo risco (somente backups antigos; canônicos preservados)"
    DELETED_SUMMARY=$(awk -F '\t' '{print $4}' "$DELETE_FILE" "$HERMES_DELETE_FILE" | awk '
        BEGIN {config=0; auth=0; soul=0; hermes=0; temp=0; other=0}
        /hermes-profiles-backup.*\.tar\.gz$/ {hermes++; next}
        /config\.yaml/ {config++; next}
        /auth\.json/ {auth++; next}
        /SOUL\.md/ {soul++; next}
        /~$/ {temp++; next}
        NF {other++}
        END {
            if (config) print "config.yaml.bak: " config;
            if (auth) print "auth.json.bak: " auth;
            if (soul) print "SOUL.md.bak: " soul;
            if (hermes) print "hermes update tarball: " hermes;
            if (temp) print "temp backup ~: " temp;
            if (other) print "outros backups: " other;
            if (!config && !auth && !soul && !hermes && !temp && !other) print "nenhum arquivo";
        }'
    )
    DELETED_SAMPLE=$(awk -F '\t' '{print $4}' "$DELETE_FILE" "$HERMES_DELETE_FILE" | head -5 | sed 's#^/root/#~/#' || true)
    if [[ -z "$DELETED_SAMPLE" ]]; then
        DELETED_SAMPLE="nenhum arquivo"
    fi
    PAYLOAD=$(jq -n \
        --arg host "$HOST" \
        --arg retention "${RETENTION_DAYS} dias" \
        --arg status "$STATUS_LABEL" \
        --arg deleted "${TOTAL_COUNT} arquivos / ${TOTAL_MB_ALL} MB" \
        --arg preserved "$PRESERVED_LABEL" \
        --arg dirs "$DIRS_REMOVED" \
        --arg summary "$DELETED_SUMMARY" \
        --arg sample "$DELETED_SAMPLE" \
        '{content:"", embeds:[{title:"Housekeeping de backups executado", color:3447003, fields:[{name:"Host", value:$host, inline:true}, {name:"Retenção", value:$retention, inline:true}, {name:"Status", value:$status, inline:false}, {name:"Deletados", value:$deleted, inline:true}, {name:"Preservados", value:$preserved, inline:true}, {name:"Diretórios vazios", value:$dirs, inline:true}, {name:"Tipos deletados", value:$summary, inline:false}, {name:"Amostra", value:$sample, inline:false}, {name:"Log completo", value:"`/root/mgs-agent/logs/housekeeping.log`", inline:false}]}]}')
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
        -X POST \
        -H "Authorization: Bot ${BOT_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "User-Agent: MGS-Zeus-Housekeeping/1.0" \
        -d "$PAYLOAD" \
        "$DISCORD_API_URL" 2>/dev/null || printf '000')
    if [[ "$HTTP_CODE" =~ ^20[01]$ ]]; then
        log "Discord bot notificado (HTTP ${HTTP_CODE}, channel=${DISCORD_CHANNEL_ID})"
    else
        log "WARN: Discord bot falhou (HTTP ${HTTP_CODE:-none})"
    fi
else
    log "WARN: DISCORD_BOT_TOKEN do Zeus ausente — sem notificação Discord"
fi

log "=== END — deletados ${TOTAL_COUNT} arquivos / ${TOTAL_MB_ALL} MB ==="
