#!/bin/bash
# Auto-commit watcher pro mgs-agent
# Detecta mudanças e cria commit (push acontece via hook 1P existente)

set -euo pipefail

REPO_DIR="${MGS_AUTOCOMMIT_REPO_DIR:-/root/mgs-agent}"
LOG_FILE="${MGS_AUTOCOMMIT_LOG_FILE:-/root/mgs-agent/logs/auto-commit-watcher.log}"
BATCH_TARGET="${MGS_AUTOCOMMIT_BATCH_TARGET:-10}"
BATCH_QUIET_SECONDS="${MGS_AUTOCOMMIT_BATCH_QUIET_SECONDS:-10}"
BATCH_MAX_WAIT_SECONDS="${MGS_AUTOCOMMIT_BATCH_MAX_WAIT_SECONDS:-600}"
SENSITIVE_PATH_REGEX='(^|/)(\.env($|\.)|.*\.pem|.*\.key|id_rsa|id_ed25519|.*credential.*|.*secret.*|.*token.*|.*password.*|.*webhook.*|.*private.*|hosts\.yml|\.npmrc|\.pypirc)$'
# Allowlist estritamente nominal para código/documentação revisados e sem segredo.
# Nunca usar padrão amplo por diretório ou por extensão.
SENSITIVE_ALLOWLIST_REGEX='(^|/)(honcho_sanitized_secret_scan\.py|report-infra-runtime-permissions-auth-and-secret-wrappers-2026-06-17\.md|service-account-token-rotation-bootstrap\.md)$'

# Não commitar artefatos/runtime state que mudam em loop ou são pesados.
# Importante: aplicar o mesmo pathspec em `git status` e `git add`.
GIT_PATHSPECS=(
  "."
  ":(exclude)data/*-state.json"
  ":(exclude)data/**/*-state.json"
  ":(exclude)data/ares/creative-inventory/video-frame-samples-full/**"
  ":(exclude)data/browser-profiles/**"
  ":(exclude)data/ares/meta-ads/audit/token-debug-*.json"
  ":(exclude)data/**/audit/**/*.json"
  ":(exclude)data/**/reports/**/*.json"
  ":(exclude)data/**/state/**/*.json"
  ":(exclude)data/ares/meta-ads/audit/**/*.json"
  ":(exclude)data/ares/meta-ads/reports/**/*.json"
  ":(exclude)data/ares/meta-ads/state/**/*.json"
  ":(exclude)data/mgs-gateway-restart-finalizer-*.sh"
)

mkdir -p "$(dirname "$LOG_FILE")"
cd "$REPO_DIR" || exit 1

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Evita duas instâncias stageando/commitando o mesmo índice Git.
exec 9>"$REPO_DIR/.git/auto-commit-watcher.lock"
if ! flock -n 9; then
  log "BLOQUEADO: outra instância do auto-commit-watcher já está ativa"
  exit 0
fi

# Monitor persistente: não existe janela cega durante quiet period, status,
# staging ou commit. O snapshot Git no flush continua sendo autoritativo.
coproc INOTIFY_MONITOR {
  exec inotifywait -m -q -r -e modify,create,delete,move \
    --format '%e' \
    --exclude '\.git/|\.bak|\.swp|\.tmp|sessions/|/logs/|node_modules' \
    "$REPO_DIR" 2>>"$LOG_FILE"
}
INOTIFY_FD=${INOTIFY_MONITOR[0]}
INOTIFY_PID=$INOTIFY_MONITOR_PID

cleanup_monitor() {
  kill "$INOTIFY_PID" 2>/dev/null || true
  wait "$INOTIFY_PID" 2>/dev/null || true
}
trap cleanup_monitor EXIT
trap 'exit 0' INT TERM

BATCH_ACTIVE=0
BATCH_COUNT=0
BATCH_STARTED_AT=0
LAST_EVENT_AT=0

log "=== Watcher started — batch_target=${BATCH_TARGET} max_wait=${BATCH_MAX_WAIT_SECONDS}s quiet=${BATCH_QUIET_SECONDS}s persistent_inotify=1 ==="

while true; do
  EVENT=""
  if IFS= read -r -t 1 EVENT <&"$INOTIFY_FD"; then
    NOW_TS=$SECONDS

    if (( BATCH_ACTIVE == 0 )); then
      BATCH_ACTIVE=1
      BATCH_STARTED_AT=$NOW_TS
      BATCH_COUNT=1
      log "Lote 1/${BATCH_TARGET} detectado; janela máxima ${BATCH_MAX_WAIT_SECONDS}s iniciada"
    elif (( NOW_TS - LAST_EVENT_AT >= BATCH_QUIET_SECONDS )); then
      BATCH_COUNT=$((BATCH_COUNT + 1))
      log "Lote ${BATCH_COUNT}/${BATCH_TARGET} detectado"
    fi

    LAST_EVENT_AT=$NOW_TS
    if [[ "$EVENT" == *Q_OVERFLOW* ]]; then
      log "WARN: overflow da fila inotify; o próximo snapshot Git será autoritativo"
    fi
  else
    READ_RC=$?
    if (( READ_RC == 1 )); then
      wait "$INOTIFY_PID" 2>/dev/null || true
      log "FATAL: monitor inotify encerrou inesperadamente"
      exit 1
    fi
  fi

  (( BATCH_ACTIVE == 1 )) || continue

  NOW_TS=$SECONDS
  ELAPSED=$((NOW_TS - BATCH_STARTED_AT))
  if (( BATCH_COUNT < BATCH_TARGET && ELAPSED < BATCH_MAX_WAIT_SECONDS )); then
    continue
  fi

  if (( BATCH_COUNT >= BATCH_TARGET )); then
    FLUSH_REASON="batch_target"
  else
    FLUSH_REASON="max_wait"
  fi
  log "Flush do auto-commit: reason=${FLUSH_REASON} batches=${BATCH_COUNT} elapsed=${ELAPSED}s"

  # Resetar antes do snapshot garante que eventos ocorridos durante
  # status/add/commit sejam lidos como o próximo agrupamento.
  BATCH_ACTIVE=0
  BATCH_COUNT=0
  BATCH_STARTED_AT=0
  LAST_EVENT_AT=0

  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  if [ "$CURRENT_BRANCH" != "main" ]; then
    log "BLOQUEADO: branch atual=$CURRENT_BRANCH; auto-commit só roda na main"
    continue
  fi

  # Captura o status uma única vez em formato NUL-safe.
  # Motivo: `git status --porcelain` cita paths com espaço; parsear com awk `{print $2}`
  # transforma `"work/Fase 1.tsv"` em `"work/Fase`, gerando `fatal: pathspec ... did not match`
  # e restart loop no systemd.
  STATUS_FILE=$(mktemp)
  git status --porcelain=v1 -z -- "${GIT_PATHSPECS[@]}" > "$STATUS_FILE"

  # Verifica se há algo pra commitar
  if [ ! -s "$STATUS_FILE" ]; then
    rm -f "$STATUS_FILE"
    log "Working tree limpo, skipping"
    continue
  fi

  STATUS_PATHS=$(python3 - "$STATUS_FILE" <<'PY'
import sys
from pathlib import Path
raw = Path(sys.argv[1]).read_bytes().split(b"\0")
rows = []
i = 0
while i < len(raw):
    rec = raw[i]
    if not rec:
        i += 1
        continue
    status = rec[:2].decode("utf-8", "replace")
    path = rec[3:].decode("utf-8", "surrogateescape")
    if status[0] in "RC" or status[1] in "RC":
        # Porcelain -z em rename/copy traz path antigo no próximo registro.
        i += 1
    rows.append(status + "\t" + path)
    i += 1
sys.stdout.write("\n".join(rows))
PY
)
  rm -f "$STATUS_FILE"

  # Lista arquivos modificados pra mensagem sem fechar pipe prematuramente.
  CHANGES=$(printf '%s\n' "$STATUS_PATHS" | cut -f2- | awk 'NR<=3 {print}' | tr '\n' ' ')
  CHANGES_TRIM=$(printf '%s' "$CHANGES" | cut -c1-100)

  # Guardrail: nunca auto-commitar adição/modificação com nome sensível.
  # Deleções puras são seguras para este filtro: removem do Git um path já
  # versionado e não conseguem introduzir segredo novo. Bloqueá-las impediria
  # para sempre a limpeza/renomeação de docs com falso positivo no nome.
  SENSITIVE_CHANGES=$(printf '%s\n' "$STATUS_PATHS" | while IFS=$'\t' read -r status path; do
    [ -n "$path" ] || continue
    [[ "$status" == *D* ]] && continue
    printf '%s\n' "$path"
  done | grep -Ei "$SENSITIVE_PATH_REGEX" | grep -Eiv "$SENSITIVE_ALLOWLIST_REGEX" || true)
  if [ -n "$SENSITIVE_CHANGES" ]; then
    log "BLOQUEADO: arquivo sensível detectado; commit automático abortado"
    printf '%s\n' "$SENSITIVE_CHANGES" | while IFS= read -r f; do log "  sensitive: $f"; done
    continue
  fi

  # Add + commit (push acontece via hook 1P existente)
  # Stage somente os paths retornados pelo status filtrado. O parse é NUL-safe
  # para nomes com espaço; cada `git add` é tolerante a corrida de arquivo
  # removido/movido entre status e staging.
  while IFS=$'\t' read -r status path; do
    [ -n "$path" ] || continue
    if [[ "${status:0:1}" == "D" && "${status:1:1}" == " " ]]; then
      # Deleção já staged: não há path no working tree nem no index para stagear.
      continue
    elif [[ "${status:1:1}" == "D" ]]; then
      git add -u -- "$path" >> "$LOG_FILE" 2>&1 || log "WARN: não consegui stagear deleção volátil: $path"
    elif ! git add -A -- "$path" >> "$LOG_FILE" 2>&1; then
      log "WARN: não consegui stagear path volátil, seguindo: $path"
    fi
  done <<< "$STATUS_PATHS"

  COMMIT_MSG="auto: $CHANGES_TRIM"

  if git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1; then
    log "Commit OK: $COMMIT_MSG"
    log "Push será disparado pelo hook 1P em background"
  else
    log "ERRO no commit (talvez nada novo)"
  fi
done
