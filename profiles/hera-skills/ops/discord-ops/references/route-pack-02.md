### Criando/ativando novo agente Discord (Zeus/Atena/Ares)

Quando criar um novo agente Hermes no Discord, validar o token próprio no 1Password antes de escrever `.env` ou subir systemd. Ver `references/new-discord-agent-1p-flow.md`.

Checklist curto:
- O item `Discord Bot - <Agent>` deve ter campo customizado `discord_bot_token` não vazio; reportar só `len=X`, nunca o valor.
- O item `Discord Webhook - <Agent> Channel` pode ter `webhook_url` e `canal`, mas webhook **não** substitui bot token.
- Usar `set -a; source /root/mgs-agent/.env; set +a` antes de `op`, para exportar `OP_SERVICE_ACCOUNT_TOKEN`.
- Se `op://MGS Conteúdo/...` falhar por acento/espaço, resolver `vault_id`/`item_id` e usar referência por ID.
- Instalar `/etc/systemd/system/<agent>-gateway.service` exige confirmação crítica explícita; só depois validar `systemctl is-active` + logs.

### Novo agente Discord/Hermes — bootstrap de bot, token e service

Quando criar um novo agente MGS com bot/canal próprios (ex: Ares), seguir o playbook `references/new-discord-agent-bootstrap.md`. Ele cobre: scopes OAuth2 (`bot` + `applications.commands`), permissões mínimas, campo 1Password `discord_bot_token`, `.env`, service systemd pelo template Zeus/Atena, e validação separada de gateway online vs bot realmente membro do servidor/canal.

Pitfall crítico validado: `Connected as <Agent>#...` prova token/gateway, mas não prova acesso ao servidor. Se `GET /channels/<channel_id>` com o token do novo bot retorna `403 Missing Access` e `GET /guilds/<guild_id>/members/<bot_id>` com bot admin retorna `404 Unknown Member`, o bot ainda não foi convidado ao servidor ou o invite não concluiu.

### Enviando mensagem Zeus → Atena em outro canal

Para comunicação **cross-channel** Zeus → Atena, incluir `<@BOT_ID>` porque Atena usa `DISCORD_ALLOW_BOTS=mentions`:

```python
send_message(
    message="<@1496306920494202950> Atena, aqui é o Zeus. [pergunta]",
    target="discord:1496267571543019653"
)
```

Sem o user mention do bot Atena, Atena ignora silenciosamente.

Em thread compartilhada, não usar esse padrão automaticamente; só acionar Atena com mention se Rodolfo pedir explicitamente.

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

### Formato REPORT-INFRA (Atena/Hera/outro agente → Zeus)

Se `send_message` para `discord:#alerts-infra` retornar `403 Missing Access`, não assumir que o canal está errado. O bot do agente pode não ter overwrite/permissão no canal. Com autorização explícita de Rodolfo, corrigir via Discord API usando um bot/admin operacional: `PUT /channels/{alerts_infra_channel_id}/permissions/{agent_bot_id}` com allow para ViewChannel, SendMessages, EmbedLinks, AttachFiles e ReadMessageHistory; validar `GET /channels/{id}` com o token do agente antes/depois. Só então reenviar o REPORT-INFRA.

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
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| REPORT-INFRA / alertas infra | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**NÃO usar** o webhook `#zeus-admin-agent` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus e commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

### REPORT-INFRA canal inacessível pelo agente

Se o agente precisar enviar `[REPORT-INFRA]` para `#alerts-infra` e receber Discord `403 Missing Access`, não descartar o reporte nem fingir envio. Com autorização explícita de Rodolfo para liberar acesso:

```text
1. Validar que o bot do agente não acessa o canal: GET /channels/{alerts_infra_id} com token do agente => 403.
2. Usar um bot/admin operacional autorizado para aplicar permission overwrite no canal para o bot do agente.
3. Considerar liberado apenas se PUT /channels/{channel_id}/permissions/{bot_id} retornar HTTP 204.
4. Validar com o token do agente: GET /channels/{channel_id} => HTTP 200.
5. Reenviar o REPORT-INFRA e registrar o message_id.
```

Não imprimir tokens. Reportar apenas códigos HTTP, IDs de canal/bot e resultado.

### Layout de alertas automáticos via webhook

Quando ajustar ou criar alertas nos canais `#mgs-alerts` / `#alerts-yoast`, evitar mensagens longas em texto corrido. Rodolfo considera esse formato poluído e difícil de entender.

Padrão preferido:
- `content`: só mention/push + frase curta quando precisa notificação (`<@344196393512075265> alerta de ...`). Sem blocos longos no content.
- `embeds`: título curto, cor por severidade e `fields` separados por assunto (`Script`, `Estado`, `Ação`, `Detalhe técnico`, `API calls`, etc.).
- Resoluções: embed verde simples com título curto (`Cron recuperado`, `Service normalizado`) e descrição de 1 linha.
- Custo/volume: separar `Custo real`, `Custo hipotético`, `API calls`, `Tokens estimados`, `Referência`, `Nota` em fields; não jogar tudo em uma descrição Markdown única.
- Emojis: usar só como indicador de severidade no resumo/título; não repetir em toda linha.

Exemplo jq compacto para webhook:

```bash
PAYLOAD=$(jq -n \
  --arg c "<@344196393512075265> alerta de cron stale" \
  --arg script "$SCRIPT" \
  --arg detail "$DETAIL" \
  '{content:$c, embeds:[{title:"Cron sem log recente", color:15158332, fields:[
    {name:"Script", value:("`"+$script+"`"), inline:true},
    {name:"Estado", value:"STALE", inline:true},
    {name:"Ação", value:"Verificar cron, script e log.", inline:false},
    {name:"Detalhe técnico", value:("```text\n"+$detail+"\n```"), inline:false}
  ]}]}')
```

Validação mínima antes de reportar sucesso: `bash -n` no script alterado e dry-run quando existir (`--dry-run`, sem envio Discord). Se o script for monitor cron, evitar disparar alerta real de teste para não sujar o canal; validar payload estrutural/localmente quando possível.

Em execuções multi-etapa de infra para Rodolfo, cada relatório parcial, final ou bloqueado deve terminar com `Próximo passo pendente:` e nomear a próxima ação operacional concreta até o checklist estar concluído. Mesmo quando a execução fica bloqueada por safety gate/falta de permissão, declarar o próximo comando/manual action esperado e a evidência que deve ser validada depois.

---
