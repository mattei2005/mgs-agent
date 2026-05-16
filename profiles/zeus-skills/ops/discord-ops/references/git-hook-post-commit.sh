#!/bin/bash
# Auto-push to GitHub after every commit + Discord notification for interactive sessions
# Token from 1Password, never persisted
# Install: cp this to /root/mgs-agent/.git/hooks/post-commit && chmod +x

LOG="/root/mgs-agent/logs/auto-push.log"
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%s)

# Detectar sessão interativa do Rodolfo via TTY check.
# Daemons (systemd, cron, watcher) nunca têm TTY.
# SSH interativo do Rodolfo sempre tem TTY.
IS_INTERACTIVE=0
if [ -t 0 ] || [ -t 1 ] || [ -t 2 ]; then
  IS_INTERACTIVE=1
fi

(
  ASKER=$(mktemp)
  cat > "$ASKER" <<'SCRIPT'
#!/bin/bash
case "$1" in
  *Username*) echo "mattei2005" ;;
  *Password*) op item get "GitHub PAT - mgs-agent" --vault "MGS Conteúdo" --fields github_token --reveal ;;
esac
SCRIPT
  chmod +x "$ASKER"

  [ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

  echo "[$(date -Iseconds)] auto-push START commit=$COMMIT_HASH msg=\"$COMMIT_MSG\"" >>"$LOG"

  if GIT_ASKPASS="$ASKER" GIT_TERMINAL_PROMPT=0 git -C /root/mgs-agent push origin main >>"$LOG" 2>&1; then
    echo "[$(date -Iseconds)] auto-push OK commit=$COMMIT_HASH" >>"$LOG"
  else
    echo "[$(date -Iseconds)] auto-push FAIL commit=$COMMIT_HASH" >>"$LOG"
  fi

  rm -f "$ASKER"

  # ── Discord notification — apenas sessão interativa (TTY = Rodolfo via SSH) ──
  if [[ "$IS_INTERACTIVE" == "1" ]]; then

    WEBHOOK_URL=$(op item get "Discord Webhook - Zeus Channel" \
      --vault "MGS Conteúdo" \
      --fields label=webhook_url --reveal 2>/dev/null || true)

    if [[ -z "$WEBHOOK_URL" ]]; then
      echo "[$(date -Iseconds)] discord-notify SKIP: webhook URL não recuperada" >>"$LOG"
    else
      mapfile -t ALL_FILES < <(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null)
      TOTAL_FILES=${#ALL_FILES[@]}
      if [[ $TOTAL_FILES -le 10 ]]; then
        FILES_STR=$(printf '%s\n' "${ALL_FILES[@]}" | head -10 | sed 's/^/• /')
      else
        EXTRA=$(( TOTAL_FILES - 10 ))
        FILES_STR=$(printf '%s\n' "${ALL_FILES[@]}" | head -10 | sed 's/^/• /')
        FILES_STR="${FILES_STR}\n+${EXTRA} more"
      fi

      COMMIT_MSG_ESC=$(echo "$COMMIT_MSG" | sed 's/"/\\"/g' | head -c 200)
      FILES_STR_ESC=$(printf '%b' "$FILES_STR" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g' | head -c 800)

      PAYLOAD=$(cat <<JSON
{
  "content": "[INFRA-COMMIT-RODOLFO]",
  "embeds": [{"title": "Commit ${COMMIT_HASH}", "description": "${COMMIT_MSG_ESC}", "color": 16753920,
    "fields": [{"name": "Arquivos modificados (${TOTAL_FILES})", "value": "${FILES_STR_ESC}"}],
    "footer": {"text": "Validar se afeta inventário"}}]
}
JSON
)

      HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 5 \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$PAYLOAD" \
        "$WEBHOOK_URL" 2>/dev/null || echo "000")

      if [[ "$HTTP_STATUS" == "204" ]]; then
        echo "[$(date -Iseconds)] discord-notify OK commit=$COMMIT_HASH tty=1" >>"$LOG"
      else
        echo "[$(date -Iseconds)] discord-notify FAIL commit=$COMMIT_HASH http=$HTTP_STATUS tty=1" >>"$LOG"
      fi
    fi
  else
    echo "[$(date -Iseconds)] discord-notify SKIP commit=$COMMIT_HASH tty=0 (daemon/automated)" >>"$LOG"
  fi

) & disown

exit 0
