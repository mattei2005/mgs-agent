---
name: inter-agent-messaging
description: Habilita e usa comunicação direta Zeus→Atena (e futuros agentes) via Discord. Cobre configuração, IDs, formato de mensagem e como verificar que foi recebida.
version: 1.0.0
author: Zeus
---

# Comunicação Inter-Agente (Zeus → Atena)

## Quando usar

- Zeus precisa perguntar algo diretamente à Atena (status, prontidão, etc.)
- Zeus precisa notificar Atena de uma decisão (aprovação/negação de usuário)
- Qualquer comunicação agente→agente via Discord

## Pré-requisito: DISCORD_ALLOW_BOTS

Por padrão o Hermes **ignora mensagens de bots silenciosamente**. Para habilitar:

```bash
# No .env do agente DESTINO (ex: Atena)
DISCORD_ALLOW_BOTS=mentions   # aceita bots apenas se @mencionado
# ou
DISCORD_ALLOW_BOTS=all        # aceita qualquer bot (não recomendado)
```

Após editar o `.env`, **reiniciar o agente destino** para carregar a variável.

## IDs importantes

| Agente | Discord Bot ID | Canal ID |
|--------|---------------|----------|
| **Zeus** | `1496296175014252634` | `1496267442899521627` (`#zeus-admin-agent`) |
| **Atena** | `1496306920494202950` | `1496267571543019653` (`#atena-content-agent`) |

> ⚠️ **Atenção:** Os IDs são diferentes nos últimos dígitos — confirmar via API se houver dúvida. Zeus bot ID (`1496296175014252634`) é o que Atena usa no REPORT-INFRA para acionar Zeus. Atena bot ID (`1496306920494202950`) é o que Zeus usa ao enviar mensagens para Atena.

Para descobrir o ID de um bot via API:
```bash
TOKEN="<bot_token>"
curl -s -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/users/@me | python3 -c "import sys,json; d=json.load(sys.stdin); print('ID:', d['id'])"
```

## Enviando mensagem Zeus → Atena

Usar `send_message` com o canal da Atena. **Obrigatório incluir `<@BOT_ID>` no texto** quando `DISCORD_ALLOW_BOTS=mentions`:

```python
send_message(
    message="<@1496306920494202950> Atena, aqui é o Zeus. [sua pergunta]",
    target="discord:1496267571543019653"
)
```

Sem o `<@1496306920494202950>`, a Atena vai ignorar silenciosamente mesmo com `DISCORD_ALLOW_BOTS=mentions`.

## Verificando que a Atena recebeu

Após enviar, checar o log da Atena:

```bash
tail -20 /root/.hermes/profiles/atena/logs/agent.log
```

Confirmar quando aparecer:
```
inbound message: platform=discord user=Zeus chat=1496267571543019653 msg='...'
response ready: ... time=Xs api_calls=N response=N chars
```

## Lendo a resposta da Atena

A resposta vai para o canal da Atena no Discord. Para ler programaticamente via session:

```bash
# Pegar o session file mais recente
ls -t /root/.hermes/profiles/atena/sessions/session_*.json | head -1

# Ler a resposta do assistant
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

Ou simplesmente aguardar o Rodolfo ver a resposta no canal `#atena-content-agent`.

## Formato REPORT-INFRA (Atena → Zeus)

Quando Atena reporta mudanças de infra ao canal `#zeus-admin-agent`, o formato canônico usa **dois user mentions**: bot user do Zeus (para ativar `DISCORD_ALLOW_BOTS=mentions`) + user mention do Rodolfo (para push notification real no celular):

```
[REPORT-INFRA] <@1496296175014252634> <@344196393512075265>
Ação: criada/modificada/removida
Tipo: cron / skill / script / config / data
Path: caminho exato
Motivo: contexto
Evidência: hash de commit ou output de comando
```

> **Por que não usar role mention da role Zeus?** A role tem `mentionable: false` e membros: 1 (só o bot, já coberto pelo user mention). Não dispara push notification para ninguém. User mention direto do Rodolfo (`<@344196393512075265>`) é o que realmente notifica.

Zeus responde com máximo 2 linhas:
- `✅ Registrado.` — sem ação adicional
- `✅ Registrado. Inventário atualizado (commit XXXX).` — quando infra-inventory.json foi atualizado
- `❌ Erro ao processar: {motivo}`

## Pitfalls

- **Validar `DISCORD_ALLOW_BOTS` no profile `.env`, não no base** — o arquivo `/root/.hermes/.env` é template/comentários. A config real fica em `/root/.hermes/profiles/{agent}/.env`. Fazer `grep DISCORD_ALLOW_BOTS /root/.hermes/.env` sempre retorna vazio — validar sempre em `/root/.hermes/profiles/zeus/.env`.
- **Sem @mention = silêncio** — com `DISCORD_ALLOW_BOTS=mentions`, a mensagem sem `<@BOT_ID>` é descartada sem log de erro
- **Reiniciar o agente destino após editar `.env`** — variáveis de ambiente só são carregadas na inicialização
- **A resposta vai pro canal da Atena, não pro Zeus** — Zeus não recebe callback automático; deve ler o log ou session file
- **Sessão nova por interação** — cada mensagem do Zeus para a Atena cria uma nova sessão no session store da Atena; o session ID está no nome do arquivo mais recente em `/root/.hermes/profiles/atena/sessions/`
- **Roles "Zeus" e "Atena" no server são `managed: true`** — criados automaticamente pelo Discord quando o bot é adicionado. Não podem ser deletados via API (`HTTP 400 "Cannot delete a managed role"`). São cosméticos e inofensivos — ignorar.
- **Push notification mobile depende de config do Discord, não do formato** — user mention `<@USER_ID>` chega corretamente; se push não aparece no celular, verificar: (1) Configurações do servidor → canal → override de notificações (não pode estar mudo), (2) Discord mobile → Notificações → Push ativado, (3) Sistema operacional → Discord → permissão de notificação em background. Canal de alertas MGS: `1498132022634483894`.
