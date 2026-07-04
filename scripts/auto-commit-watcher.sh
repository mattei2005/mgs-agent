#!/bin/bash
# Auto-commit watcher pro mgs-agent
# Detecta mudanças e cria commit (push acontece via hook 1P existente)

set -euo pipefail

REPO_DIR="/root/mgs-agent"
LOG_FILE="/root/mgs-agent/logs/auto-commit-watcher.log"
DEBOUNCE_SECONDS=10  # espera 10s antes de commitar (evita spam)
SENSITIVE_PATH_REGEX='(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_ed25519|.*credential.*|.*secret.*|.*token.*|.*password.*|.*webhook.*|.*private.*|hosts\.yml|\.npmrc|\.pypirc)$'
SENSITIVE_ALLOWLIST_REGEX='(^|/)(honcho_sanitized_secret_scan\.py|report-infra-runtime-permissions-auth-and-secret-wrappers-2026-06-17\.md)$'

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

log "=== Watcher started ==="

while inotifywait -r -e modify,create,delete,move \
  --exclude '\.git/|\.bak|\.swp|\.tmp|sessions/|/logs/|node_modules' \
  "$REPO_DIR" 2>/dev/null; do

  log "Mudança detectada"
  sleep "$DEBOUNCE_SECONDS"

  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  if [ "$CURRENT_BRANCH" != "main" ]; then
    log "BLOQUEADO: branch atual=$CURRENT_BRANCH; auto-commit só roda na main"
    continue
  fi

  # Captura o status uma única vez. Evita pipelines com `head` sob
  # `set -o pipefail`: quando há muitas mudanças, o produtor do pipe pode
  # receber SIGPIPE e derrubar o watcher com exit 141, gerando restart loop.
  STATUS_OUTPUT=$(git status --porcelain -- "${GIT_PATHSPECS[@]}")

  # Verifica se há algo pra commitar
  if [ -z "$STATUS_OUTPUT" ]; then
    log "Working tree limpo, skipping"
    continue
  fi

  # Lista arquivos modificados pra mensagem sem fechar pipe prematuramente.
  CHANGES=$(printf '%s\n' "$STATUS_OUTPUT" | awk 'NR<=3 {print $2}' | tr '\n' ' ')
  CHANGES_TRIM=$(printf '%s' "$CHANGES" | cut -c1-100)

  # Guardrail: nunca auto-commitar arquivo com nome sensível.
  # Se aparecer algo suspeito, aborta esta rodada e exige revisão humana.
  SENSITIVE_CHANGES=$(printf '%s\n' "$STATUS_OUTPUT" | awk '{print $2}' | grep -Ei "$SENSITIVE_PATH_REGEX" | grep -Eiv "$SENSITIVE_ALLOWLIST_REGEX" || true)
  if [ -n "$SENSITIVE_CHANGES" ]; then
    log "BLOQUEADO: arquivo sensível detectado; commit automático abortado"
    printf '%s\n' "$SENSITIVE_CHANGES" | while IFS= read -r f; do log "  sensitive: $f"; done
    continue
  fi

  # Add + commit (push acontece via hook 1P existente)
  # Stage somente os paths retornados pelo status filtrado. Evita `git add .`
  # tocar diretórios ignorados que ainda têm histórico versionado.
  while IFS= read -r status_line; do
    [ -n "$status_line" ] || continue
    path=$(printf '%s\n' "$status_line" | awk '{print $2}')
    [ -n "$path" ] || continue
    git add -A -- "$path"
  done <<< "$STATUS_OUTPUT"

  COMMIT_MSG="auto: $CHANGES_TRIM"

  if git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1; then
    log "Commit OK: $COMMIT_MSG"
    log "Push será disparado pelo hook 1P em background"
  else
    log "ERRO no commit (talvez nada novo)"
  fi
done
