#!/bin/bash
# Auto-commit watcher pro mgs-agent
# Detecta mudanças e cria commit (push acontece via hook 1P existente)

set -euo pipefail

REPO_DIR="/root/mgs-agent"
LOG_FILE="/root/mgs-agent/logs/auto-commit-watcher.log"
DEBOUNCE_SECONDS=10  # espera 10s antes de commitar (evita spam)
SENSITIVE_PATH_REGEX='(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_ed25519|.*credential.*|.*secret.*|.*token.*|.*password.*|hosts\.yml|\.npmrc|\.pypirc)$'

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

  # Verifica se há algo pra commitar
  if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    log "Working tree limpo, skipping"
    continue
  fi

  # Lista arquivos modificados pra mensagem
  CHANGES=$(git status --porcelain | head -3 | awk '{print $2}' | tr '\n' ' ')
  CHANGES_TRIM=$(echo "$CHANGES" | cut -c1-100)

  # Add + commit (push acontece via hook 1P existente)
  git add .

  COMMIT_MSG="auto: $CHANGES_TRIM"

  if git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1; then
    log "Commit OK: $COMMIT_MSG"
    log "Push será disparado pelo hook 1P em background"
  else
    log "ERRO no commit (talvez nada novo)"
  fi
done
