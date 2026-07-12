### Pedidos operacionais ao Zeus e permissões de canais

Quando Rodolfo pedir para acionar/pedir algo ao Zeus, enviar no canal/thread operacional do Zeus **mencionando explicitamente o bot Zeus (`<@1496296175014252634>`)**. Sem user mention, Zeus pode não ler/agir por causa de `DISCORD_ALLOW_BOTS=mentions`.

Quando o pedido for adicionar pessoas a um canal de logs, primeiro verificar se o bot do perfil atual tem permissão real no canal (`GET /channels/<id>` + permissões computadas, especialmente `MANAGE_ROLES`/`MANAGE_CHANNELS`). Se tiver, aplicar permission overwrite por usuário e validar com novo `GET /channels/<id>` antes de reportar sucesso. Se não tiver, aí sim encaminhar ao Zeus/admin com mention explícita e IDs.

Se Rodolfo corrigir que uma mensagem ao Zeus foi enviada sem mention, reenviar a mensagem corrigida imediatamente com o user mention real do Zeus no início; não tratar como já entregue nem apenas explicar a regra. Para pedidos de permissão/canal (ex.: adicionar usuários ao `logs-aquisicao`), listar IDs em texto normal fora de bloco de código se a mention do Zeus precisa acordar o bot. Antes de concluir que precisa do Zeus, porém, verificar se o bot do agente atual já ganhou permissão no canal: `GET /channels/{channel_id}`, `GET /guilds/{guild_id}/members/{bot_id}`, roles/overwrites e flags efetivas (`MANAGE_ROLES`/`MANAGE_CHANNELS`, `CREATE_PUBLIC_THREADS`, `SEND_MESSAGES_IN_THREADS`). Se a permissão existir, aplicar `PUT /channels/{channel_id}/permissions/{user_id}` para os usuários pedidos e validar os overwrites por GET; só acionar Zeus/admin quando faltar permissão real.

Não enviar tarefa operacional em `#alerts-infra`. `#alerts-infra` é para `[REPORT-INFRA]`, alertas e rastreabilidade de mudanças; abrir tarefa lá polui o canal e cria thread fora do contexto correto.

Fluxo:
1. Tentar enviar no alvo do Zeus (`discord:#zeus` ou canal ID do Zeus disponível no ambiente).
2. Se `send_message` retornar `403 Missing Access`, **não usar `#alerts-infra` como fallback de tarefa**.
3. Reportar o bloqueio ao Rodolfo e pedir/corrigir permissão do bot no canal do Zeus, ou usar outro alvo do Zeus explicitamente autorizado por Rodolfo.
4. Só usar `#alerts-infra` quando a mensagem for realmente um `[REPORT-INFRA]`/alerta de infra, não um pedido operacional.

Pitfall validado no Ares: pedido ao Zeus sobre capacidade de leitura de threads foi enviado para `#alerts-infra` após `#zeus` retornar 403; Rodolfo corrigiu que isso não fazia sentido porque abriu thread no canal de alertas.

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

### Formato REPORT-INFRA (Atena/Ares → Zeus)

REPORT-INFRA usa somente Discord Embed pelo helper canônico `/root/mgs-agent/scripts/send-report-infra-embed.sh`: `content` vazio, sem mentions, sem thread e sem segunda cópia em texto. O adaptador `/root/mgs-agent/scripts/ares-report-infra.sh` permanece compatível com payloads legados, mas os converte para o mesmo embed. Não usar `send_message` nem `ares-discord-post-with-thread.py` para REPORT-INFRA. Validar sem sujar o canal com `ares-report-infra.sh --dry-run`.

Zeus responde com máximo 2 linhas:
- `✅ Registrado.`
- `✅ Registrado. Inventário atualizado (commit XXXX).`
- `❌ Erro ao processar: {motivo}`

#### Fallback quando `send_message` retorna Missing Access

Se o webhook do `#alerts-infra` funciona mas `send_message` direto do agente retorna `403 Missing Access`, corrigir permissões do bot no canal em vez de depender apenas do webhook, quando Rodolfo autorizar:

```text
Passo | Ação
------|------------------------------------------------------------
1     | Validar o token do bot alvo com GET /users/@me sem imprimir token
2     | Validar que um bot admin/Zeus consegue GET /channels/<alerts-infra>
3     | Confirmar que o bot alvo é membro do guild
4     | Aplicar permission overwrite no canal para o user ID do bot alvo
5     | Liberar: VIEW_CHANNEL, SEND_MESSAGES, READ_MESSAGE_HISTORY, EMBED_LINKS, ATTACH_FILES
6     | Validar GET /channels pelo bot alvo
7     | Fazer um `send_message` real no #alerts-infra com REPORT-INFRA
```

Pitfall: uma URL de webhook pode ser válida mesmo quando `send_message` do bot falha por falta de acesso ao canal. Trate webhook e bot permissions como caminhos separados; validar ambos quando o usuário quiser fallback direto.

### Convenção de canal Discord por tipo de alerta

| Tipo | Canal | Webhook 1Password |
|---|---|---|
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| REPORT-INFRA / alertas infra | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**NÃO usar** o webhook `#zeus-admin-agent` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus e commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894).

### Layout de alertas automáticos via webhook

Quando ajustar ou criar alertas nos canais `#mgs-alerts` / `#alerts-yoast`, evitar mensagens longas em texto corrido. Rodolfo considera esse formato poluído e difícil de entender.

