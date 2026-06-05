---
name: discord-ops
description: "Operações do ecossistema de agentes MGS (Zeus/Atena): comunicação inter-agente via Discord, diagnóstico e reinicialização de gateway, versionamento de profiles (SOUL.md, skills) via git, roles managed, e hook git post-commit com notificação via webhook. Cobre IDs de canais/bots, DISCORD_ALLOW_BOTS, TTY check, sessão stale, rate limit, Message Content Intent, symlink pitfall e ciclo cron de sync."
tags: [discord, inter-agent, messaging, webhook, hook, git, roles, infra, notification, hermes, agent, restart, versioning, soul, profile, systemd, cron]
related_skills: [log-monitor-discord-alert, wp-plugin-mass-operation, hermes-update]
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
| **Ares** | *(pendente — bot/token próprio ainda não criado)* | `1508853425952133180` (`#ares-campaign-ads-agent`) |
| **Rodolfo** | `344196393512075265` | — |
| **Alerts MGS** | — | `1498132022634483894` (`#mgs-alerts`) |
| **Alerts Yoast** | — | `1498193722871910550` (`#alerts-yoast`) |

### Anti-loop em threads com múltiplos agentes

Regra principal: **em thread compartilhada com Rodolfo + mais de um agente, não iniciar conversa agente→agente por padrão**. Cada agente deve responder ao humano, não ficar alinhando estado com outro bot.

#### Review de alinhamento entre agentes, sem acordar bots

Quando Rodolfo pedir para comparar, acompanhar ou validar a resposta de Zeus/Atena/Ares/outro agente na mesma thread:
- Não mencionar o outro bot; usar texto simples (`Atena`, `Zeus`).
- Primeiro importar/ler a thread em modo read-only se a mensagem do outro agente não estiver no contexto ativo **ou se houver qualquer chance de ela já ter chegado enquanto Zeus processava**. Não postar “aguardando/monitor ativo” antes de fazer essa checagem.
- Se Rodolfo disser “acompanhe a resposta quando ela responder”, trate como uma tarefa de observação: checar a thread atual primeiro; só configurar monitor se a resposta ainda não existir de fato. Se configurar monitor/cron, remover assim que a resposta for capturada ou se o usuário apontar que já respondeu.
- Evitar resposta prematura que concorra com a resposta do outro agente. O fluxo correto é: ler estado atual da thread → avaliar mensagem existente → responder com veredito; não anunciar que vai avaliar depois quando a evidência já está disponível.
- Responder ao Rodolfo com uma matriz curta de alinhamento: `Ponto | Agente A disse | Agente B disse | Alinhamento`.
- Quando Rodolfo pedir “leia tudo na thread X e veja se faz sentido”, importar a thread em modo read-only e validar claims operacionais contra evidência real antes do veredito: arquivos citados, links no SKILL.md, scripts/runner existentes, commits mencionados e estado git quando relevante. Se outro agente disser “verifiquei”, “salvei”, “linkei” ou “commit criado”, tratar isso como claim verificável, não como fato.
- Separar claramente `conceito correto` de `implementação pronta`: ex. REC+P1 pode estar certo como desenho/orquestração, mas ainda não estar operacional se falta runner, renderer ou hard gate automatizado.
- Separar consenso de diferença operacional. Exemplo: “Atena falou como dona do processo; Zeus trouxe evidência técnica e patch concreto.”
- Se houver divergência, declarar a decisão recomendada sem iniciar conversa agente→agente.
- Terminar com `Próximo passo pendente:` quando a conversa envolver execução/patch/infra ou quando o veredito concluir que a ideia faz sentido mas ainda falta implementação/teste.

O incidente real `1505532189490811081` mostrou que a regra “mencione o outro agente quando falar dele” é perigosa se aplicada como padrão: cada mention acorda o bot destino, gera fila, e qualquer confirmação vira novo input.

Regras operacionais:
- Responder mensagens do Rodolfo normalmente.
- Quando Rodolfo responde em reply/menção a uma proposta clara do Zeus com linguagem como “execute”, “ok, execute”, “manda ver”, interpretar como autorização para a ação proposta pelo Zeus. Não deixar uma mensagem intercalada de outro bot redefinir o escopo para uma ação diferente (ex: restart) sem evidência explícita do Rodolfo.
- Não responder a mensagens de outro agente que sejam só `queued`, `read-only`, `recebido`, `sem ação`, `(empty)`, erro transitório de modelo, confirmação de estado, pedido redundante de confirmação ou repetição do que já foi aceito.
- Depois de um estado final aceito, ficar em silêncio até pedido novo do Rodolfo, pergunta operacional real, autorização explícita ou alerta crítico.
- Se Rodolfo disser “parem”, “looping”, “pare de mencionar”, “pare de responder”, ou equivalente: uma confirmação curta ao Rodolfo no máximo; depois silêncio total para mensagens de agente/gateway naquela thread.
- Citar outro agente em texto simples (`Atena`, `Zeus`) quando não for necessário acordá-lo. **Não usar user mention só para falar sobre o agente.**
- Usar user mention de outro bot apenas quando Rodolfo pedir explicitamente para acionar/encaminhar ao agente, ou em comunicação cross-channel onde `DISCORD_ALLOW_BOTS=mentions` exige mention para roteamento.
- Em conversa multi-agente onde Rodolfo impôs gate de segurança, explicação/alinhamento pode ocorrer sem ação; execução, patch, restart, persistência em SOUL/config/skill/script só com autorização explícita.
- Não ecoar exemplos de mentions dentro de blocos de código; se precisar documentar, escrever “user mention do bot X, ID Y”.

Pitfall validado: responder “ignorado”, “read-only mantido”, `[sem resposta operacional]`, `sem ação`, ou mencionar o bot destino para corrigir uma mensagem automática ainda gera novo input e prolonga o loop. A melhor resposta para ruído automático é silêncio total.

Referência do incidente real: `references/discord-agent-loop-incident-2026-05-17.md` — thread `1505532189490811081`, Zeus/Atena, mentions + queued/read-only/(empty) causando ping-pong até lock/archive/delete.

Playbook de limpeza pós-incidente: `references/discord-shared-thread-loop-cleanup.md` — usar quando o loop gerou regras ruins/redundantes em SOUL, skills ou memória; consolida a política segura e o checklist para desfazer regras perigosas.

### Limpeza pós-loop de regras persistidas

Se um loop multiagente levou à criação apressada de skills/memórias/regras, tratar como correção operacional, não como aprendizado automático bruto:
- Auditar mudanças recentes em SOUL, skills e memórias dos agentes envolvidos.
- Remover regras amplas do tipo “sempre mencionar Zeus/Atena” em thread compartilhada.
- Consolidar em um único skill guarda-chuva por agente; evitar 2–3 skills estreitas sobre o mesmo incidente.
- Preservar no máximo uma referência concisa do incidente, com política final segura.
- Validar que a regra final diferencia thread compartilhada de cross-channel: em thread, texto simples por padrão; cross-channel pode exigir mention para roteamento.

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
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| Operacional Zeus | `#zeus-admin-agent` (1496267442899521627) | `Discord Webhook - Zeus Channel` |

**NÃO usar** o webhook `#zeus-admin-agent` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus, `[REPORT-INFRA]` de agentes, e commits interativos.

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
8. **Commit local ≠ upload GitHub:** ao reportar commits para Rodolfo, diferenciar explicitamente `commit local`, `push/upload para GitHub`, `upstream configurado` e `auto-push confirmado`. Se a branch não tem upstream (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` falha), dizer que o commit ainda não está confirmado no GitHub e nomear o comando de push necessário, em vez de usar só o termo técnico “upstream”.

---

## SEÇÃO D — Diagnóstico, Cron Scheduler e Reinicialização de Agente (Gateway Hermes)

### Quando usar
- Agente está online (processo rodando) mas não responde no Discord
- Mensagens não aparecem como `inbound message` no log
- Agente travou em loop de rate limit
- Usuário relata silêncio após período de alta atividade
- Auditar ou migrar cron jobs Hermes/Linux entre profiles MGS

### Cron-worker architecture / provider pinning

Ver `references/hermes-cron-worker-architecture.md` para o padrão completo de auditoria e migração.

Para estabilidade pós-migração Codex OAuth, ver também `references/hermes-codex-oauth-and-auxiliary-compression.md`: padrão híbrido GPT-5.5 Codex como modelo principal + auxiliares Haiku/Anthropic, sync OAuth global→profiles via cron, validação de restarts e pitfalls de chat-log com `$`.

Resumo operacional MGS:
- `zeus` e `atena` ficam em `gpt-5.5` via `openai-codex` para trabalho principal.
- Cron com LLM deve rodar no profile dedicado `cron-worker` usando `claude-haiku-4-5-20251001` via `anthropic`.
- Cron determinístico deve ser script-only ou Hermes `no_agent=True`; não gastar LLM.
- Para modelos Claude, não confiar em `provider: auto` quando o profile default é `openai-codex`; pin explícito: `provider: anthropic`.
- Erro `model is not supported when using Codex with a ChatGPT account` para Haiku geralmente indica provider errado, não ID de modelo inválido.

Antes de mudar cron/profile/service, fazer Fase 1 read-only: configs dos profiles, `cron/jobs.json`, `crontab -l`, `systemctl cat`, e reportar sem restart/write.

### Approval buttons no Discord: prompts frequentes e “This interaction failed”

Quando Rodolfo relatar que botões `Allow Once / Allow Session / Always Allow / Deny` falham com “This interaction failed” ou aparecem com frequência excessiva, usar o playbook em `references/hermes-discord-approval-buttons.md`.

Resumo operacional:
- Diagnosticar em `errors.log`, `agent.log`, `gateway/platforms/discord.py` e `tools/approval.py` antes de mudar config.
- Se o handler editar a mensagem antes de dar ACK, patchar para `await interaction.response.defer(ephemeral=True)` imediatamente e só depois resolver a fila Hermes / editar `interaction.message`.
- Para reduzir ruído de falso positivo em operações MGS conhecidas, preferir `approvals.mode: smart` + `approvals.gateway_timeout: 900`, preservando hardline blocks.
- Não desligar aprovações globalmente (`mode: off`) sem autorização explícita; isso remove uma camada de segurança.
- Após patch em runtime Hermes, `py_compile` e restart controlado do gateway afetado são obrigatórios antes de declarar mitigação ativa.

### Discord mostrando retry/TTFB técnico em toda mensagem

Quando Rodolfo relatar que Zeus/Atena está postando mensagens técnicas como `Retrying in ...`, `No first byte from provider in 45s`, rate-limit waits, ou falhas auxiliares dentro das threads, tratar como **ruído de status callback**, não como motivo automático para trocar modelo/provider.

### Live tool-call trace no Discord com cleanup automático

Quando Rodolfo quiser a UX de “atividade ao vivo” no Discord — tool calls visíveis enquanto o agente trabalha e removidos quando a resposta final chega — usar `references/discord-live-tool-trace-cleanup.md`.

Resumo operacional:
- Ativar `display.platforms.discord.tool_progress: all` e `tool_preview_length` adequado por profile.
- Ativar `display.platforms.discord.cleanup_progress: true` para apagar breadcrumbs após sucesso.
- Garantir que o adapter Discord implemente `delete_message`; sem isso o runner desativa cleanup silenciosamente.
- Aplicar config nos profiles ativos e nas cópias versionadas em `/root/mgs-agent/profiles/*-config.yaml`.
- Validar com `py_compile` + parse YAML/AST sem restart; pedir autorização separada para reiniciar gateways.

Padrão correto:
- Confirmar o sintoma no print/logs (`agent.log`/`errors.log`) e distinguir: retry interno pode continuar, mas não deve poluir Discord.
- Corrigir no gateway em `_prepare_gateway_status_message(...)`, aplicando a supressão de status ruidoso também para `Platform.DISCORD`.
- Manter logs completos; só suprimir o envio ao chat.
- Atualizar teste de gateway para cobrir Telegram + Discord.
- Rodar `py_compile` + pytest do filtro e reiniciar os gateways afetados.

Referência detalhada: `references/discord-provider-retry-noise-filter.md`.

### Gateway routing/restart incident reference

When correcting routing between Zeus/Atena, avoiding duplicate threads, restarting a gateway during an active conversation, or designing recovery after restart interruption, see:
- `references/discord-gateway-routing-and-restart-incident-2026-05-18.md`
- `references/gateway-restart-coordination.md`
- `references/gateway-restart-recovery-checkpoint.md`

Rule: Zeus can keep read access to Atena's channel, but must not free-respond/auto-thread there without explicit @Zeus. During benchmark or maintenance, do not combine patch + restart + cron/self-check from the bot being restarted; stabilize the service first, then validate. If a restart interrupts an active turn, recovery must be deterministic and return to the same thread with status/next-step so Rodolfo does not need to prompt “continua”.

### Busy input no Discord: `/queue` vs `/steer`

Quando Rodolfo mandar uma segunda pergunta enquanto Zeus/Atena ainda está processando a primeira:

- `/steer texto` **não cria nova resposta**. Injeta o texto como orientação dentro do turno em andamento, após o próximo tool call. Use para corrigir/interromper direção da resposta atual.
- `/queue texto` cria **um novo turno FIFO**. O agente termina a resposta atual e depois responde o texto enfileirado como pergunta separada.
- Mensagem normal durante execução depende de `display.busy_input_mode`. Em `queue`, o caminho atual pode usar `merge_pending_message_event()` com slot único, o que pode mesclar/substituir follow-ups em vez de garantir uma resposta por mensagem.

Se o objetivo operacional for “Rodolfo pode mandar duas perguntas ao mesmo tempo e receber duas respostas em sequência”, a correção de runtime é tratar mensagem normal em `busy_input_mode: queue` como FIFO real, usando o mesmo mecanismo de `/queue` (`_enqueue_fifo`) em vez de `merge_pending_message_event()`/`_queue_or_replace_pending_event()`. Antes de patchar Hermes runtime: fazer backup, patch pequeno em `gateway/run.py`, restart do service afetado e teste real com duas mensagens rápidas.

Referência detalhada: `references/hermes-discord-busy-input-queue.md`.

### Sintomas típicos

| Sintoma | Causa provável |
|---------|---------------|
| Processo rodando, Discord conectado, mas sem `inbound message` | Sessão stale OU Message Content Intent desabilitada |
| Múltiplos `Retrying request` (waits 21s, 45s, 56s) | Rate limit Anthropic |
| Gateway reiniciou mas parou de receber após reconexão | Sessão zumbi pós-restart |
| Canal principal responde inline e não cria threads, apesar de `auto_thread: true` | Upstream Hermes pode estar pulando auto-thread em `free_response_channels` |

### Adding a user to a private Discord thread

When Rodolfo asks to add Raquel or another user to a Zeus/Atena thread, use Discord API `PUT /channels/{thread_id}/thread-members/{user_id}`. If it returns `403 Missing Access`, the likely cause is that the user is not in the parent channel yet; report that clearly, then retry the same PUT after Rodolfo grants parent-channel access. Do not claim the thread add succeeded until the API returns `204`.


### Diagnóstico de título ruim em auto-thread

Quando Rodolfo perguntar por que uma thread não foi renomeada, ou por que o título ficou genérico/truncado, não assumir erro de Discord/permissão. Ver `references/discord-auto-thread-title-diagnostics.md`.

Resumo operacional:
- O título da thread Discord é escolhido pelo gateway no momento de criação (`_auto_create_thread` / `_auto_thread_name_from_message`), antes da resposta do agente.
- Logs de `Auxiliary title_generation` depois da resposta normalmente são título interno de sessão Hermes; não significam que o Discord thread title foi atualizado.
- Validar via Discord API o `name` atual da thread e comparar com a primeira mensagem/inbound log.
- Se não houver regra semântica para a família do pedido (ex: `github + push/autopush`), o fallback usa os primeiros termos limpos da mensagem; isso é “renomeou mal”, não “não renomeou”.
- Correção preferida: regra class-level no `_auto_thread_name_from_message(...)` e, se necessário, rename pós-resposta idempotente via `PATCH /channels/{thread_id}` sem sobrescrever rename manual do usuário/moderador.

### Regressão/quirk: `free_response_channels` pode desativar auto-thread

Quando Rodolfo relatar que está falando no canal principal e o agente responde ali mesmo sem abrir thread, não assumir que `auto_thread` foi desligado. Diagnóstico validado em 2026-05-22 no Zeus:

```bash
python3 - <<'PY'
import yaml
p='/root/.hermes/profiles/zeus/config.yaml'
c=yaml.safe_load(open(p)) or {}
d=c.get('discord',{}) or {}
for k in ['auto_thread','require_mention','thread_require_mention','free_response_channels','allowed_channels','no_thread_channels']:
    print(k, repr(d.get(k,'<missing>')))
PY
tr '\0' '\n' < /proc/$(systemctl show -p MainPID --value zeus-gateway.service)/environ \
  | grep -E '^DISCORD_.*(THREAD|CHANNEL|MENTION|IGNORE|AUTO)' \
  | sed -E 's/(TOKEN|KEY|SECRET)=.*/\1=[REDACTED]/'
git -C /root/.hermes/hermes-agent blame -L 4545,4558 -- gateway/platforms/discord.py
```

Causa observada: commit upstream `d55754456 fix(discord): keep free-response channels inline` alterou a condição para:

```python
skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel
```

Efeito: se o canal do agente está em `free_response_channels` para aceitar mensagens sem `@bot`, o Hermes pode responder inline e não criar thread, mesmo com `DISCORD_AUTO_THREAD=true`. Para MGS, o comportamento desejado no canal Zeus é: aceitar mensagem sem mention **e ainda criar thread**.

Correção recomendada, se Rodolfo autorizar: patch local pequeno em `/root/.hermes/hermes-agent/gateway/platforms/discord.py` removendo `or is_free_channel` dessa condição, depois `py_compile`, restart controlado do gateway afetado e teste real no canal principal. Registrar patch em `/root/mgs-agent/patches/hermes/` para reaplicar após updates.

### Diagnóstico

```bash
# 1. Verificar processo
ps aux | grep -E "hermes.*atena|hermes.*zeus" | grep -v grep

# 2. Últimas linhas do log
tail -30 /root/.hermes/profiles/atena/logs/agent.log

# 3. Checar chegada de mensagens
grep "inbound message" /root/.hermes/profiles/atena/logs/agent.log | tail -5

# 4. Loop de rate limit?
grep -E "Retry|inbound|response ready|ERROR" /root/.hermes/profiles/atena/logs/agent.log | tail -20
```

**Sessão stale confirmada quando:** processo vivo, log mostra `Connected as Atena#2956`, mas nenhum `inbound message` novo após mensagens enviadas.

### Reinicialização

```bash
pkill -f "hermes -p atena gateway run"
sleep 2 && ps aux | grep "atena" | grep -v grep   # confirmar morte
# Reiniciar com terminal(background=true)
sleep 5 && tail -10 /root/.hermes/profiles/atena/logs/agent.log
```

Confirmar sucesso: `Connected as Atena#2956` + `✓ discord connected` + `Gateway running with 1 platform(s)`

### Causa raiz difícil: Message Content Intent

Se após reinicialização o agente **continua sem receber**: verificar no Discord Developer Portal:
1. https://discord.com/developers/applications → aplicação do bot
2. Aba **Bot** → **Privileged Gateway Intents** → confirmar **Message Content Intent** habilitada

### Patch local `busy_input_mode` em gateway

Patch em `/root/.hermes/hermes-agent/gateway/run.py` que faz `busy_input_mode: queue` funcionar em gateway mode. Quando o Hermes for atualizado:
1. Verificar: `grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py`
2. Se não estiver: `patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch`
3. Restart: `systemctl restart zeus-gateway atena-gateway`

Issue upstream: https://github.com/NousResearch/hermes-agent/issues/14905

### Pitfalls (restart)

- **Não combinar patch + restart + cron/LLM check no mesmo fluxo ativo sem necessidade.** Incidente 2026-05-18: restart de `zeus-gateway` durante uma conversa grande gerou `SIGTERM`, drain de ~106s, mensagens de “Gateway shutting down”, e um cron de pós-check concorreu com o turno seguinte. Para patch urgente de gateway: aplicar mudança mínima, validar sintaxe, fazer `systemctl restart <service>`, checar `systemctl show/is-active` diretamente após voltar, e evitar criar cron LLM entregue na origem como healthcheck; se precisar watchdog, usar script-only/no-agent silencioso.
- **Restart sob systemd pode ficar `deactivating/stop-sigterm` enquanto drena turno ativo.** Não declarar travamento imediatamente; verificar logs por `Shutdown phase: drain done` e novo `Connected as ...`. Se o usuário está aguardando ação operacional, manter resposta curta e não abrir novos loops de diagnóstico.
- **Roteamento Zeus/Atena:** se Zeus precisa ler o canal da Atena mas não responder a pedidos editoriais, manter `allowed_channels` incluindo Atena apenas com `require_mention=true`, `thread_require_mention=true` e `free_response_channels` restrito ao canal Zeus. Validar com logs que pedido normal no canal Atena não vira thread duplicada do Zeus.
- **Não usar `nohup/disown/&`** em terminal foreground — usar `terminal(background=true)`
- **Sessão zumbi é silenciosa** — Discord mostra online mas sem eventos; detectável só pelo log
- **`pkill` pelo padrão exato** — `pkill -f "hermes -p atena gateway run"` para não matar outros perfis
- **`config.yaml` sobrescreve `.env` para `allowed_channels`** — se `discord.allowed_channels` estiver vazio, agente ignora TODAS as mensagens. Fix: `allowed_channels: '1496267571543019653'` no `config.yaml`
- **Mensagens de bots ignoradas por padrão** — `DISCORD_ALLOW_BOTS=mentions` no `.env` do agente destino; com `mentions`, incluir `<@BOT_ID>` no texto
- **Profile `.env` real está em `/root/.hermes/profiles/{agent}/.env`** — nunca `/root/.hermes/.env` (é template)
- **Instância em terminal interativo (`pts/N`)** — output vai para aquele terminal, não para agent.log; detectar via coluna TTY no `ps aux`
- **Múltiplas instâncias conflitam** — verificar PID file antes de reiniciar; `Another gateway instance is already running`

### Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```

---

## SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico

Ver `references/discord-threads-lifecycle.md` para referência completa.

### Auto-add de membros em threads: diagnosticar prompt/config antes de culpar Discord

Quando Rodolfo relatar que Atena/Zeus cria threads mas parou de colocar pessoas automaticamente nelas, usar `references/discord-thread-auto-add-members-regression.md`. Para a correção aplicada em 2026-05-19 na Atena, ver `references/discord-thread-auto-add-members-2026-05-19.md`.

Lição validada: o gateway Discord do Hermes cria threads via `_auto_create_thread(...)`, mas não adiciona membros extras por padrão. No setup MGS, o comportamento antigo vinha de um `channel_prompts` bootstrap que fazia auto-discover + `PUT /channels/{THREAD_ID}/thread-members/{uid}` via `execute_code`. Se esse prompt/config for simplificado demais, a thread continua sendo criada, mas só ficam o usuário autor + bot/agente.

Pitfall 2026-05-26: `execute_code` pode não receber `DISCORD_BOT_TOKEN`; o env passthrough bloqueia credenciais de provider/bot por segurança. Se logs mostrarem `env passthrough: refusing ... DISCORD_BOT_TOKEN` ou `ERROR: DISCORD_BOT_TOKEN not set`, o bootstrap em prompt não consegue chamar Discord API. Preferir correção no runtime/gateway ou script shell que carregue o `.env` autorizado fora do sandbox, e validar com API/logs antes de declarar auto-add corrigido.

Regra operacional atual: Atena/content threads devem auto-add Raquel (`1496254952501280974`) + Rodolfo (`344196393512075265`). Zeus/admin threads atualmente só exigem Rodolfo. Não adicionar todo mundo do guild/canal; usar política explícita por agente/canal.

Diagnóstico mínimo:
- Inspecionar `/root/.hermes/profiles/{atena,zeus}/config.yaml` → `discord.channel_prompts`.
- Procurar no histórico versionado por `thread-members`, `auto-discover`, `renomear thread + adicionar membros`.
- Verificar no gateway (`/root/.hermes/hermes-agent/gateway/platforms/discord.py`) se há `thread.add_user`/`thread-members`; se não houver, core não está fazendo auto-add.
- Consultar Discord API para `GET /channels/{THREAD_ID}/thread-members` e reportar apenas contagem/IDs permitidos; nunca imprimir token/header.

Correção preferida: implementar auto-add determinístico pós-criação no runtime/config (`thread_auto_add_users`/roles) ou restaurar prompt enxuto só para thread comprovadamente nova. Não voltar com script longo em toda resposta/follow-up.



### Bootstrap de novo agente Discord/Hermes

Quando criar ou colocar online um novo agente MGS no Discord (bot/app OAuth, item 1Password, `.env`, canal privado, systemd service e smoke test), usar `references/new-discord-agent-bootstrap.md`. Ele cobre scopes OAuth, campos 1Password (`discord_bot_token`, `webhook_url`), validação de guild/channel access, overwrite de permissões, template systemd e `DISCORD_THREAD_AUTO_ADD_USERS` para auto-add do Rodolfo em threads sem depender de bootstrap via `execute_code`.

### Followed announcement channels com explicação automática

Quando Rodolfo criar um canal que segue anúncios externos (ex: Hermes announcements) e pedir para Zeus explicar automaticamente cada novo post abaixo do anúncio, usar o padrão de poller cron descrito em `references/discord-followed-announcement-explainer.md`.

Resumo operacional:
- Verificar acesso de Zeus e Atena via Discord API, mas lembrar que acesso ao canal ≠ gateway ouvindo; checar `discord.allowed_channels` separadamente.
- Preferir poller Zeus com state (`last_seen_id`/`processed`) + reply via `message_reference`, em vez de adicionar o canal ao gateway normal.
- Manter Atena fora desse fluxo por padrão; é administrativo/Hermes, não editorial.
- Inicializar state no message atual para não reprocessar histórico/follow setup.
- Ignorar state runtime no git para evitar auto-commit de churn.

Ver `references/discord-threads-lifecycle.md` para referência completa.

**Resumo executivo:** threads arquivadas = zero tokens. Tokens só correm quando chega mensagem nova. Histórico preservado indefinidamente (sem auto-delete). Canal Zeus: archive em 24h.

### Contexto perdido em thread ativa: verificar `session_reset` antes de culpar Discord

Quando Rodolfo relatar que um agente “perdeu contexto da thread”, respondeu como se fosse conversa nova, ou ignorou mensagens anteriores dentro da mesma thread, diagnosticar primeiro a sessão Hermes, não a thread Discord.

Checklist read-only:

```bash
# Config do profile afetado
python3 - <<'PY'
import yaml
p='/root/.hermes/profiles/ares/config.yaml'  # trocar profile
c=yaml.safe_load(open(p)) or {}
print(c.get('session_reset'))
print((c.get('discord') or {}).get('history_backfill'), (c.get('discord') or {}).get('history_backfill_limit'))
PY

# Sessão associada à thread e se ela reiniciou com history=0
grep -n "THREAD_ID\|Session expiry\|conversation turn: session=.*history=" /root/.hermes/profiles/ares/logs/agent.log | tail -120
```

Sinais de causa raiz:
- `Session expiry done` perto do horário diário configurado (`session_reset.at_hour`).
- Nova mensagem na mesma `thread_id/chat` cria novo `session_id` com `history=0`.
- `sessions/sessions.json` mostra a thread apontando para sessão nova, enquanto sessões antigas foram `expiry_finalized=true`.

Interpretação operacional: Discord preservou a thread; quem zerou contexto foi o Hermes por política de reset/expiração. Para threads operacionais longas (Canva/downloads/campanhas), o padrão recomendado é evitar reset diário rígido e usar expiração por inatividade maior:

```yaml
session_reset:
  mode: idle
  idle_minutes: 10080   # 7 dias, ajustar por perfil
  at_hour: 4
```

Aplicar mudança de config e restart de gateway só com autorização explícita quando afetar serviço ativo. Após restart, validar `systemctl is-active <agent>-gateway.service` e log com `Connected as ...` + próxima mensagem entrando com histórico esperado.

### Leitura sob demanda de threads antigas

Quando Rodolfo perguntar se Zeus consegue ler threads antigas, responder com precisão: Zeus não lê automaticamente qualquer thread antiga pelo contexto ativo. A solução operacional é importar uma thread específica por link/ID via Discord API em modo read-only.

Referência e playbook: `references/discord-thread-importer.md`.

Fluxo padrão:
1. Rodolfo fornece link Discord ou thread/channel ID.
2. Rodar `/root/mgs-agent/scripts/import-discord-thread.py '<link-ou-id>'`.
3. Ler `/root/mgs-agent/data/discord-thread-imports/<thread_id>.md` para responder.
4. Manter `data/discord-thread-imports/` local-only no `.gitignore`; não versionar históricos importados.

---

## SEÇÃO G — Importar histórico de thread antiga por link/ID

Quando Rodolfo/Raquel pedir para Zeus ou Atena ler uma thread antiga, use o importador read-only canônico por link/ID. Ver `references/discord-thread-history-import.md`.

Comandos padrão:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
```

Pitfall: usar o `--profile` correto evita tentar acessar private threads com o token do bot errado. Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---

## SEÇÃO E — Versionamento e Edição de Profiles (SOUL.md, config.yaml, skills)

### Quando usar
- SOUL.md de algum agente precisa de backup remoto / histórico git
- Novo agente criado e precisa ter SOUL.md rastreado
- Skills MGS-específicas precisam ser versionadas no repo
- Rodolfo pede ajuste de tom/verbosity/persona operacional do Zeus ou Atena
- Rodolfo pede uma “indexação”/auditoria de contexto sem mexer em providers de memória
- Rodolfo pede validação de acesso GitHub ou varredura completa de repositório privado/público

Para varredura GitHub/repo, ver `references/github-repo-audit.md`: validação segura de PAT via 1Password sem persistir credencial no remote, `GIT_ASKPASS` temporário, checklist de secrets atual+histórico, varredura de arquivos comprimidos no histórico (`*.tar.gz` com `.env`/profiles), sintaxe, crons/logs, dependências e relatório executivo. Ao reportar achados de secrets, nunca imprimir valores; separar `current tree clean` de `history dirty`, confirmar revogação/exposição externa antes de propor reescrita destrutiva de histórico.

Para hardening iterativo do `/root/mgs-agent`, ver também `references/mgs-repo-hardening-audit.md`: cobre pitfalls duráveis desta classe (`grep -c` gerando `0\n0`, guardrail contra auto-commit de segredos, detecção semântica de erro em cron fresco, SSH `accept-new` + `known_hosts_mgs`, stubs para scripts deprecated e higiene de runtime/backups versionados).

Para hardening pós-auditoria do repo MGS, ver `references/mgs-repo-hardening-audit-2026-05-16.md`: cobre correções reutilizáveis de `grep -c` com `set -e`, guardrails do auto-commit watcher, detecção semântica de erro em cron logs, SSH/SCP com `accept-new` + `known_hosts_mgs`, stubs para scripts deprecated, higiene de backups/runtime e ACK imediato em botões Discord.

Para a fase final de dependências/tooling, ver `references/mgs-deps-tooling-audit.md`: enumeração de manifests, `npm audit/outdated/test` sem upgrades destrutivos, conversão de API legacy Anthropic/FastAPI para stub fail-closed quando o serviço já está masked/inactive, e checklist de validação.

Para lint Bash profundo com ShellCheck durante hardening MGS, ver `references/mgs-shellcheck-hardening.md`: instalação aprovada, escopo de scripts rastreados, priorização de error/warning, correção do pitfall `cmd | python <<HEREDOC` (stdin sobrescrito), e formato de validação/relatório.

Para o fechamento pós-hardening, ver `references/mgs-hardening-release-hygiene.md`: classificar referências históricas vs runtime ativo, consolidar release note em `docs/changelog/`, documentar commits fragmentados do auto-commit watcher e validar git/serviços antes do relatório final.

### Ajustes de tom/verbosity, layout visual e contexto semântico

Ver `references/atena-profile-prompt-slimming.md` quando o objetivo for reduzir latência/loop de leitura da Atena no Discord: manter `SOUL.md` e `channel_prompts` curtos, remover leitura obrigatória de AGENT.md, evitar scripts longos de rename/mention antes de REC direto, sincronizar via `sync-souls.sh` e reiniciar/validar o gateway.

Ver `references/hermes-profile-style-context-ops.md` para o padrão validado de:
- adicionar “Modo executivo curto — teste ativo” no SOUL.md sem colar persona crua de curso;
- criar backup e rollback de SOUL.md;
- manter `reasoning_effort` inalterado quando o usuário pedir;
- fazer um manifesto read-only dos arquivos de memória/contexto como equivalente seguro de “indexação” sem mudar memória;
- rodar warm-up pós-troca de modelo/profile.

Ver também `references/agent-response-layout-standard.md` para o padrão MGS de respostas visuais no Discord: quando houver dados estruturados/comparáveis, usar bloco monoespaçado `text` com colunas alinhadas e separadores; os nomes das colunas devem nascer do contexto da thread, nunca ser copiados de exemplos.

Quando Rodolfo pedir para aplicar padrões de Zeus/Atena em agente novo/existente (ex: Ares) ou reclamar de tabelas Markdown cruas `|---|---|`, usar `references/mgs-agent-profile-pattern-rollout.md`. Esse playbook cobre auditoria comparativa SOUL/config/autorização/systemd, regra de layout `text`, sync de skills MGS-específicas (`Ares: growth/`) e o cuidado de double-confirm antes de editar `AGENT.md`.

Quando Rodolfo pedir para aplicar padrões do Zeus/Atena ao Ares ou outro agente novo, usar `references/agent-profile-parity-audit.md`: auditar SOUL/config ativos e cópias em `/root/mgs-agent/profiles/`, autorização, systemd, thread behavior, REPORT-INFRA, no-secret, validação e sync de skills MGS-específicas. O padrão visual `|---|---| porém em tabela` deve ser traduzido para bloco `text` alinhado, não tabela Markdown crua.

### ⚠️ PITFALL CRÍTICO: Symlink NÃO versiona conteúdo

```bash
ln -s /root/.hermes/profiles/zeus/SOUL.md /root/mgs-agent/profiles/zeus-soul.md
git add profiles/zeus-soul.md
# git armazena O APONTADOR (mode 120000), não o conteúdo
git show HEAD:profiles/zeus-soul.md → /root/.hermes/profiles/zeus/SOUL.md
```

Mudanças no SOUL.md real **não aparecem em `git diff`**, não disparam auto-push. Testado e confirmado em 2026-04-24.

### Solução implantada em produção — cópia periódica via cron

Script `/root/mgs-agent/scripts/sync-souls.sh` sincroniza SOUL.md + skills MGS-específicas:

```bash
#!/bin/bash
set -e

PROFILES_DIR="/root/.hermes/profiles"
TARGET_DIR="/root/mgs-agent/profiles"
mkdir -p "$TARGET_DIR"

# SOUL.md sync (mtime check)
for agent in zeus atena; do
    SOURCE="$PROFILES_DIR/$agent/SOUL.md"
    TARGET="$TARGET_DIR/$agent-soul.md"
    if [ -f "$SOURCE" ] && [ "$SOURCE" -nt "$TARGET" ]; then
        cp "$SOURCE" "$TARGET"
        echo "$(date -Iseconds) synced $agent SOUL"
    fi
done

# Skills MGS-específicas sync (rsync com --delete)
mkdir -p "$TARGET_DIR/zeus-skills"
rsync -a --delete \
    "$PROFILES_DIR/zeus/skills/ops/" \
    "$TARGET_DIR/zeus-skills/ops/" \
    && echo "$(date -Iseconds) synced zeus skills/ops"

for category in wordpress devops; do
    if [ -d "$PROFILES_DIR/atena/skills/$category" ]; then
        rsync -a --delete \
            "$PROFILES_DIR/atena/skills/$category/" \
            "$TARGET_DIR/atena-skills/$category/" \
            && echo "$(date -Iseconds) synced atena skills/$category"
    fi
done
```

**Crontab:** `*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh >> /root/mgs-agent/logs/sync-souls.log 2>&1`

**Destinos no git:**
- `profiles/zeus-soul.md` / `profiles/atena-soul.md` — SOUL.md dos agentes
- `profiles/zeus-skills/ops/` — skills operacionais MGS do Zeus
- `profiles/atena-skills/wordpress/` e `atena-skills/devops/` — skills MGS da Atena

**Por que rsync para skills (não `-nt`):** SOUL.md é 1 arquivo — mtime é suficiente. Skills são árvores de diretórios — `rsync -a --delete` detecta adições, modificações e deleções. O `--delete` propaga remoções.

### Diagnóstico rápido: symlink vs arquivo real no git

```bash
# mode 120000 = symlink (errado), 100644 = arquivo real (correto)
git ls-files -s profiles/

# Ver o que git armazenou como conteúdo
git show HEAD:profiles/zeus-soul.md

# Teste definitivo
echo "x" >> /root/.hermes/profiles/zeus/SOUL.md
git -C /root/mgs-agent diff  # vazio se symlink, diff real se arquivo
```

### Adicionar novo agente ao sync

1. Adicionar no loop `for agent in zeus atena NOVO_AGENTE` para SOUL.md.
2. Adicionar o agente no loop de `config.yaml` quando o profile tiver config versionada.
3. Adicionar bloco `rsync -a --delete` só para categorias MGS-específicas do novo agente; não sincronizar a árvore inteira de skills bundled/hub.
4. Rodar manualmente uma vez para criar os arquivos iniciais.
5. Confirmar cron: `crontab -l | grep sync-souls`.
6. Se a categoria virar política MGS-wide em `/root/mgs-agent/AGENT.md`, fazer double-confirm antes de editar, porque AGENT.md é Critical Subset.

Categorias seletivas conhecidas:
- Zeus: `ops/`
- Atena: `wordpress/`, `devops/`, e `autonomous-ai-agents/openhands` como exceção pontual
- Ares: `growth/`

### Política de extensão de skills

Se nova skill MGS-específica for criada em categoria não coberta (ex: `zeus/skills/data-science/`), adicionar ao bloco rsync do script E reportar via `[REPORT-INFRA]`. Skill fora do sync = não versionada = sem rastreabilidade.
