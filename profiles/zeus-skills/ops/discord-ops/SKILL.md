---
name: discord-ops
description: "Operações Discord para o ecossistema MGS: comunicação inter-agente (Zeus↔Atena), roles managed (managed=true, não deletáveis via API), e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check para distinção humano/daemon."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification]
related_skills: [hermes-agent-ops, log-monitor-discord-alert]
---

# Discord Ops — Comunicação Inter-Agente, Roles e Webhooks

## SEÇÃO A — Comunicação Inter-Agente (Zeus → Atena)

### Quando usar
- Zeus precisa perguntar algo diretamente à Atena
- Zeus precisa notificar Atena de uma decisão
- Qualquer comunicação agente→agente via Discord

### Pré-requisito: DISCORD_ALLOW_BOTS

Por padrão o Hermes **ignora mensagens de bots silenciosamente**:

```bash
# No .env do agente DESTINO (ex: Atena)
DISCORD_ALLOW_BOTS=mentions   # aceita bots apenas se @mencionado (recomendado)
DISCORD_ALLOW_BOTS=all        # aceita qualquer bot (não recomendado)
```

Após editar o `.env`, **reiniciar o agente destino** para carregar a variável.

### IDs importantes

| Agente | Discord Bot ID | Canal ID |
|--------|---------------|----------|
| **Zeus** | `1496296175014252634` | `1496267442899521627` (`#zeus-admin-agent`) |
| **Atena** | `1496306920494202950` | `1496267571543019653` (`#atena-content-agent`) |
| **Rodolfo** | `344196393512075265` | — |
| **Alerts MGS** | — | `1498132022634483894` (`#mgs-alerts`) |
| **Alerts Yoast** | — | `1498193722871910550` (`#alerts-yoast`) |

### Enviando mensagem Zeus → Atena

Obrigatório incluir `<@BOT_ID>` com `DISCORD_ALLOW_BOTS=mentions`:

```python
send_message(
    message="<@1496306920494202950> Atena, aqui é o Zeus. [pergunta]",
    target="discord:1496267571543019653"
)
```

Sem `<@1496306920494202950>` → Atena ignora silenciosamente.

### Verificando que Atena recebeu

```bash
tail -20 /root/.hermes/profiles/atena/logs/agent.log
# Esperar: inbound message: platform=discord user=Zeus ...
```

### Lendo a resposta da Atena

```bash
ls -t /root/.hermes/profiles/atena/sessions/session_*.json | head -1
python3 -c "
import json
with open('/root/.hermes/profiles/atena/sessions/session_XXXXXXXX.json') as f:
    s = json.load(f)
for m in s.get('messages', []):
    if m.get('role') == 'assistant':
        content = m.get('content','')
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    print(c['text'])
        elif content:
            print(content)
"
```

### Formato REPORT-INFRA (Atena → Zeus)

Dois user mentions: bot Zeus (para `DISCORD_ALLOW_BOTS=mentions`) + Rodolfo (push notification):

```
[REPORT-INFRA] <@1496296175014252634> <@344196393512075265>
Ação: criada/modificada/removida
Tipo: cron / skill / script / config / data
Path: caminho exato
Motivo: contexto
Evidência: hash de commit ou output de comando
```

Zeus responde com máximo 2 linhas:
- `✅ Registrado.`
- `✅ Registrado. Inventário atualizado (commit XXXX).`
- `❌ Erro ao processar: {motivo}`

### Convenção de canal Discord por tipo de alerta

| Tipo | Canal | Webhook 1Password |
|---|---|---|
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Operacional Zeus | `#zeus-admin-agent` (1496267442899521627) | `Discord Webhook - Zeus Channel` |

**NÃO usar** o webhook `#zeus-admin-agent` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus, `[REPORT-INFRA]` de agentes, e commits interativos.

---

## SEÇÃO B — Roles Managed (não deletáveis via API)

### O Problema

Roles com `managed: true` são criados quando um bot é adicionado ao server. A API **não permite deletar**:
```
DELETE /guilds/{guild_id}/roles/{role_id} → HTTP 400: "Cannot delete a managed role"
```

### Como Identificar

```bash
curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/guilds/{GUILD_ID}/roles" \
  | jq '.[] | select(.id == "{ROLE_ID}") | {name, managed}'
# managed: true → não deletável; managed: false → pode deletar
```

### Características

- Criados automaticamente quando bot é adicionado
- Nome = nome do bot (ex: "Zeus", "Atena")
- `mentionable: false` por padrão
- Removidos apenas quando o bot é removido do server

### Alternativa Operacional

Parar de mencionar o role — usar **user mention direto** (`<@BOT_ID>` + `<@344196393512075265>`). O role continua existindo mas inofensivo. **Por que não usar role mention:** a role `mentionable: false` e não dispara push notification para Rodolfo. User mention direto é o que realmente notifica.

---

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

Webhook URL: 1Password → vault `MGS Conteúdo` → item `Discord Webhook - Zeus Channel` → campo `label=webhook_url` (não `url`).

### Pitfalls do hook

1. **`op` sem token no cron/background:** sempre `source /root/mgs-agent/.env` explicitamente no subshell
2. **URL hardcoded:** nunca. URL no 1Password, lida em runtime
3. **curl sem timeout:** usar `--max-time 5`; Discord pode estar offline
4. **Erros silenciosos:** usar `|| true` e `2>/dev/null` em tudo Discord; o push para GitHub NUNCA pode falhar por causa da notificação
5. **Identidade git compartilhada:** não filtrar por `%an/%ae` — usar TTY check
6. **`mapfile` em commits vazios:** `diff-tree` retorna vazio para `--allow-empty`; embed aparece sem lista de arquivos (inofensivo)
7. **Não testar via `terminal()` do Zeus:** subshell não tem TTY; testar via SSH direto do Rodolfo
