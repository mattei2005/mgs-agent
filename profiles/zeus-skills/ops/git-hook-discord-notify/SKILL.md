---
name: git-hook-discord-notify
description: "Adiciona notificação Discord ao post-commit hook do git mgs-agent. Envia embed para canal Zeus apenas quando commit vem de sessão interativa (TTY check). Solução definitiva para distinguir Rodolfo de daemons/agentes."
tags: [git, discord, webhook, hook, notification, infra]
related_skills: [inter-agent-messaging]
---

# Hook git post-commit com notificação Discord

## Quando usar
- Precisa notificar canal Discord automaticamente após commits no mgs-agent
- Auditoria de mudanças de infra em tempo real

## Pré-requisitos

1. **Discord Webhook URL** no 1Password:
   - Vault: `MGS Conteúdo`
   - Item: `Discord Webhook - Zeus Channel`
   - Field: `webhook_url`

2. **Verificar URL antes de escrever o hook:**
   ```bash
   set -a && source /root/mgs-agent/.env && set +a
   op item get "Discord Webhook - Zeus Channel" \
     --vault "MGS Conteúdo" --fields label=webhook_url --reveal 2>&1
   # Deve retornar https://discord.com/api/webhooks/...
   ```
   > ⚠️ O `op` CLI precisa do `OP_SERVICE_ACCOUNT_TOKEN` — sourcear `.env` primeiro. Sem isso: "No accounts configured".

## ⚠️ PITFALL CRÍTICO: filtro por autor não funciona no mgs-agent

O repo `/root/mgs-agent` tem `git config user.name = "Rodolfo Mattei"` configurado localmente. **Todos os commits** (auto-commits do watcher, commits da Atena, commits manuais) saem com a mesma identidade. O filtro `%an/%ae` não discrimina — validado empiricamente em 2026-04-24.

## ✅ Solução validada: TTY check

Validação empírica confirmou distinção perfeita:
- SSH interativo do Rodolfo → TTY ativo (`-t 0/1/2` = true)
- Auto-commit watcher (systemd) → sem TTY
- Atena gateway (systemd) → sem TTY  
- Zeus gateway (systemd) → sem TTY
- Crons → sem TTY

```bash
# Capturar ANTES do subshell background (herda via variável)
IS_INTERACTIVE=0
if [ -t 0 ] || [ -t 1 ] || [ -t 2 ]; then
  IS_INTERACTIVE=1
fi

# No subshell:
if [[ "$IS_INTERACTIVE" == "1" ]]; then
  # notificar Discord
else
  echo "[$(date -Iseconds)] discord-notify SKIP commit=$COMMIT_HASH tty=0 (daemon/automated)" >>"$LOG"
fi
```

**Importante:** capturar `IS_INTERACTIVE` no processo pai (antes do `( ) & disown`). O subshell herda variáveis mas não tem acesso ao TTY do pai após o fork.

## Hook post-commit completo (versão produção — TTY check)

Localização: `/root/mgs-agent/.git/hooks/post-commit`

```bash
#!/bin/bash
# Auto-push to GitHub after every commit
# Token from 1Password, never persisted

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
  "embeds": [{
    "title": "Commit ${COMMIT_HASH}",
    "description": "${COMMIT_MSG_ESC}",
    "color": 16753920,
    "fields": [{
      "name": "Arquivos modificados (${TOTAL_FILES})",
      "value": "${FILES_STR_ESC}"
    }],
    "footer": {"text": "Validar se afeta inventário"}
  }]
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
```

## Instalação

```bash
# Copiar conteúdo acima para o hook
chmod +x /root/mgs-agent/.git/hooks/post-commit

# Verificar que URL não está hardcoded
grep -i 'discord.com/api/webhooks' /root/mgs-agent/.git/hooks/post-commit \
  && echo "ERRO: URL hardcoded" || echo "OK: URL não hardcoded"
```

## Teste

```bash
# Teste 1 — path interativo (TTY = Rodolfo via SSH)
# Fazer da sua sessão SSH diretamente (não via execute_code do Zeus):
cd /root/mgs-agent
echo "# test" >> INFRA.md && git add INFRA.md
git commit -m "test: hook TTY interativo"
# Aguardar ~10s → mensagem deve aparecer no #zeus-admin-agent
git revert HEAD --no-edit

# Teste 2 — daemon path (sem TTY)
# Aguardar próximo auto-commit do watcher
# Verificar log:
grep 'discord-notify' /root/mgs-agent/logs/auto-push.log | tail -5
# Esperado: discord-notify SKIP commit=HASH tty=0 (daemon/automated)
```

> ⚠️ **Não é possível testar o caminho interativo via `terminal()` do Zeus** — o subshell não tem TTY. O teste deve ser feito pelo próprio Rodolfo via SSH.

## Validação de sucesso

- Log mostra `discord-notify OK commit=HASH`
- HTTP 204 do Discord = sucesso
- HTTP 000 = curl falhou (timeout ou rede)
- HTTP 400/401 = payload malformado ou URL inválida

## Pitfalls

1. **`op` sem token:** hook executa em background sem herdar o env do shell que fez o commit. Sempre sourcear `/root/mgs-agent/.env` explicitamente no início do subshell.

2. **URL hardcoded:** nunca. O hook é commitado no repo (não o `.git/hooks/`, mas o padrão de código). URL no 1Password, lida em runtime.

3. **curl sem timeout:** Discord pode demorar ou ficar offline. `--max-time 5` garante que o hook não trava o push.

4. **Erros silenciosos:** usar `|| true` e `2>/dev/null` em tudo relacionado ao Discord. O push para GitHub NUNCA pode falhar por causa da notificação.

5. **Identidade git compartilhada:** `/root/mgs-agent` usa `user.name=Rodolfo Mattei` para todos os commits. Filtro por `%an/%ae` não distingue humano de daemon — usar TTY check (solução definitiva validada em 2026-04-25).

6. **`mapfile` e `git diff-tree`:** funciona apenas para commits com arquivos. Para commits vazios (`--allow-empty`), `diff-tree` retorna vazio — `TOTAL_FILES=0`, `value` do embed ficará vazio. Inofensivo, mas o embed aparece sem lista de arquivos.
