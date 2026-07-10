## SEÇÃO C — Hook git post-commit com notificação Discord

### Quando usar
- Notificar canal Discord automaticamente após commits interativos do Rodolfo no mgs-agent
- Auditoria de mudanças de infra em tempo real

### ⚠️ PITFALL CRÍTICO: filtro por autor não funciona

O repo `/root/mgs-agent` tem `user.name=Rodolfo Mattei` para todos os commits (auto-commits do watcher, Atena, manuais). **Filtro `%an/%ae` não discrimina.**

### ✅ Solução validada: TTY check

- SSH interativo do Rodolfo → TTY ativo
- Auto-commit watcher (systemd) → sem TTY
- Gateways Zeus/Atena (systemd) → sem TTY
- Crons → sem TTY

```bash
# Capturar ANTES do subshell background (herda via variável)
IS_INTERACTIVE=0
if [ -t 0 ] || [ -t 1 ] || [ -t 2 ]; then
  IS_INTERACTIVE=1
fi
# No subshell, verificar $IS_INTERACTIVE
```

**CRÍTICO:** capturar `IS_INTERACTIVE` no processo pai (antes do `( ) & disown`). O subshell herda variáveis mas não acessa o TTY do pai após fork.

### Hook post-commit (versão produção)

Localização: `/root/mgs-agent/.git/hooks/post-commit`

Instalar: copiar conteúdo do arquivo de referência `references/git-hook-post-commit.sh` para o hook e `chmod +x`.

Webhook URL: 1Password → vault `MGS Conteúdo` → item `Discord Webhook - Alerts Infra Channel` → campo `label=webhook_url` (não `url`) para REPORT-INFRA/alertas; usar `Discord Webhook - Zeus Channel` apenas para hook de commit interativo quando explicitamente aplicável.

### Webhook 403 false-negative / User-Agent

Se um envio de REPORT-INFRA via `send_message` ou Python `urllib.request` retornar 403, não concluir imediatamente que o webhook está morto. Validar com `curl` e User-Agent explícito antes de trocar credenciais:

```bash
WEBHOOK_URL=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=webhook_url --reveal)
curl -sS -A 'MGS-Agent-InfraReporter/1.0' -o /tmp/body -w '%{http_code}' --max-time 15 "$WEBHOOK_URL"
```

Padrão validado no Ares: `urllib` sem User-Agent/rota direta do bot pode cair em `403`, enquanto o webhook real responde `200` em GET e `204` em POST via `curl -A`. Para REPORT-INFRA de Ares, preferir o helper persistente `/root/mgs-agent/scripts/ares-report-infra.sh`, que busca o webhook no 1Password e envia por `curl` com User-Agent. Ao resolver pendências, marcar arquivos locais como `.delivered` só depois de `http_status=204`.

### Pitfalls do hook

1. **`op` sem token no cron/background:** sempre `source /root/mgs-agent/.env` explicitamente no subshell
2. **URL hardcoded:** nunca. URL no 1Password, lida em runtime
3. **curl sem timeout:** usar `--max-time 5`; Discord pode estar offline
4. **Erros silenciosos:** usar `|| true` e `2>/dev/null` em tudo Discord; o push para GitHub NUNCA pode falhar por causa da notificação
5. **Identidade git compartilhada:** não filtrar por `%an/%ae` — usar TTY check
6. **`mapfile` em commits vazios:** `diff-tree` retorna vazio para `--allow-empty`; embed aparece sem lista de arquivos (inofensivo)
7. **Não testar via `terminal()` do Zeus:** subshell não tem TTY; testar via SSH direto do Rodolfo

---
