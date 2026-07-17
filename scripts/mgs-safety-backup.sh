#!/usr/bin/env bash
# =============================================================================
# mgs-safety-backup.sh — Snapshot operacional seguro da MGS
#
# Roda via cron diariamente, mas só cria novo backup se o último snapshot tiver
# mais de BACKUP_INTERVAL_DAYS (default: 3). Use --force para criar agora.
#
# Proteções:
#   - Exclui segredos conhecidos (.env, auth.json, token, secret, credential etc.)
#   - Gera manifest sem conteúdo sensível
#   - Valida o tar.gz com tar -tzf antes de declarar sucesso
#   - Mantém sempre o último snapshot, mesmo se acima da retenção
#   - --dry-run mostra o que faria sem criar/deletar nada
# =============================================================================

set -euo pipefail

BASE_DIR=/root/mgs-agent
BACKUP_DIR="${BACKUP_DIR:-/root/mgs-agent/backups/safety}"
LOG="${LOG:-/root/mgs-agent/logs/mgs-safety-backup.log}"
INTERVAL_DAYS="${BACKUP_INTERVAL_DAYS:-3}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DRY_RUN=0
FORCE=0

usage() {
  echo "Usage: $0 [--dry-run] [--force]"
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: argumento desconhecido: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG")"
log() { echo "[$(date -Iseconds)] mgs-safety-backup: $*" | tee -a "$LOG"; }

latest_backup() {
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mgs-safety-*.tar.gz' -printf '%T@\t%p\n' 2>/dev/null | sort -n | tail -1 | cut -f2-
}

should_create_backup() {
  local latest age_secs min_secs
  latest="$(latest_backup || true)"
  if [[ -z "$latest" || ! -f "$latest" ]]; then
    return 0
  fi
  age_secs=$(( $(date +%s) - $(stat -c %Y "$latest") ))
  min_secs=$(( INTERVAL_DAYS * 86400 ))
  (( age_secs >= min_secs ))
}

cleanup_old_safety_backups() {
  local latest cutoff
  latest="$(latest_backup || true)"
  cutoff=$(( $(date +%s) - RETENTION_DAYS * 86400 ))
  find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'mgs-safety-*.tar.gz' -o -name 'mgs-safety-*.manifest.txt' \) -print0 2>/dev/null |
    while IFS= read -r -d '' f; do
      [[ -z "$latest" ]] && continue
      # Preservar sempre o tar.gz mais recente e seu manifest correspondente.
      if [[ "$f" == "$latest" || "$f" == "${latest%.tar.gz}.manifest.txt" ]]; then
        continue
      fi
      if (( $(stat -c %Y "$f") < cutoff )); then
        if [[ "$DRY_RUN" -eq 1 ]]; then
          log "DRY-RUN: would rm old safety backup $f"
        else
          rm -f -- "$f"
          log "rm old safety backup $f"
        fi
      fi
    done
}

TS="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="${BACKUP_DIR}/mgs-safety-${TS}.tar.gz"
MANIFEST="${BACKUP_DIR}/mgs-safety-${TS}.manifest.txt"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

if [[ "$FORCE" -eq 0 ]] && ! should_create_backup; then
  latest="$(latest_backup || true)"
  log "SKIP: último backup ainda dentro do intervalo de ${INTERVAL_DAYS} dias: ${latest:-none}"
  cleanup_old_safety_backups
  exit 0
fi

log_start="START interval=${INTERVAL_DAYS}d retention=${RETENTION_DAYS}d archive=$ARCHIVE"
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: $log_start"
else
  log "$log_start"
fi

# Snapshot de crontab e units MGS em staging temporário.
mkdir -p "$TMPDIR/runtime/crontab" "$TMPDIR/runtime/systemd"
crontab -l > "$TMPDIR/runtime/crontab/root.crontab" 2>/dev/null || true
find /etc/systemd/system -maxdepth 1 -type f \
  \( -name 'zeus*.service' -o -name 'atena*.service' -o -name 'ares*.service' -o -name 'mgs*.service' \) \
  -exec cp -a {} "$TMPDIR/runtime/systemd/" \; 2>/dev/null || true

# Lista de fontes. Arquivos ausentes são ignorados.
SOURCES=(
  "/root/mgs-agent/context"
  "/root/mgs-agent/docs"
  "/root/mgs-agent/scripts"
  "/root/mgs-agent/profiles"
  "/root/mgs-agent/data"
  "$TMPDIR/runtime"
)

EXCLUDES=(
  "--exclude=.git"
  "--exclude=node_modules"
  "--exclude=__pycache__"
  "--exclude=*.pyc"
  "--exclude=.env"
  "--exclude=.env.*"
  "--exclude=*auth.json*"
  "--exclude=*credentials*"
  "--exclude=*credential*"
  "--exclude=*secret*"
  "--exclude=*token*"
  "--exclude=*password*"
  "--exclude=*passwd*"
  "--exclude=*webhook*"
  "--exclude=*.sqlite"
  "--exclude=*.db"
  "--exclude=*.log"
  "--exclude=logs"
  "--exclude=backups"
)

existing_sources=()
for src in "${SOURCES[@]}"; do
  [[ -e "$src" ]] && existing_sources+=("$src")
done

if [[ "${#existing_sources[@]}" -eq 0 ]]; then
  log "ERROR: nenhuma fonte encontrada para backup"
  exit 2
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY-RUN: fontes incluídas:"
  printf '  %s\n' "${existing_sources[@]}" | tee -a "$LOG"
  log "DRY-RUN: destino $ARCHIVE"
  cleanup_old_safety_backups
  log "END DRY-RUN"
  exit 0
fi

# Criar archive sem imprimir lista de arquivos no chat/log.
# Usar caminhos relativos a / evita warning de tar sobre leading slash no cron.
# GNU tar pode sair com code 1 quando um arquivo muda durante leitura
# ("file changed as we read it"). Para snapshot operacional MGS isso é
# aceitável como WARN se o archive existir e `tar -tzf` validar; caso contrário
# falha fechado.
tar_sources=()
for src in "${existing_sources[@]}"; do
  tar_sources+=("${src#/}")
done
set +e
tar_output=$(tar -C / -czf "$ARCHIVE" "${EXCLUDES[@]}" "${tar_sources[@]}" 2>&1)
tar_rc=$?
set -e
if [[ "$tar_rc" -ne 0 ]]; then
  if [[ "$tar_rc" -eq 1 && -s "$ARCHIVE" && "$tar_output" == *"file changed as we read it"* ]]; then
    log "WARN: tar retornou 1 por arquivo alterado durante leitura; validando archive mesmo assim"
    printf '%s\n' "$tar_output" >> "$LOG"
  else
    printf '%s\n' "$tar_output" >> "$LOG"
    log "ERROR: tar falhou rc=$tar_rc"
    exit "$tar_rc"
  fi
fi

# Manifest técnico: caminhos no archive + tamanho/hash do pacote. Não contém conteúdo.
{
  echo "created_at=$(date -Iseconds)"
  echo "host=$(hostname)"
  echo "archive=$ARCHIVE"
  echo "sha256=$(sha256sum "$ARCHIVE" | awk '{print $1}')"
  echo "size_bytes=$(stat -c %s "$ARCHIVE")"
  echo "sources=${existing_sources[*]}"
  echo
  echo "archive_listing:"
  tar -tzf "$ARCHIVE"
} > "$MANIFEST"

# Validação real do tar.
tar -tzf "$ARCHIVE" >/dev/null

cleanup_old_safety_backups

SIZE_MB=$(awk -v bytes="$(stat -c %s "$ARCHIVE")" 'BEGIN {printf "%.2f", bytes/1024/1024}')
log "END OK archive=$ARCHIVE size=${SIZE_MB}MB manifest=$MANIFEST"
