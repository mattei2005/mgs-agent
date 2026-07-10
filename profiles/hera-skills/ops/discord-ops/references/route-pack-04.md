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

When Rodolfo asks to add Raquel or another user to a Zeus/Atena thread, use Discord API `PUT /channels/{thread_id}/thread-members/{user_id}`. Do this even when no dedicated `discord_admin` tool is loaded: load the bot token from the active profile `.env` inside a terminal/shell command, call Discord API directly, and never print the token. If it returns `403 Missing Access`, the likely cause is that the user is not in the parent channel yet; report that clearly, then retry the same PUT after Rodolfo grants parent-channel access. Do not claim the thread add succeeded until the API returns `204`.


### Diagnóstico de título ruim em auto-thread

Quando Rodolfo perguntar por que uma thread não foi renomeada, ou por que o título ficou genérico/truncado, não assumir erro de Discord/permissão. Ver `references/discord-auto-thread-title-diagnostics.md`.

Resumo operacional:
- O título inicial da thread Discord é escolhido pelo gateway no momento de criação (`_auto_create_thread` / `_auto_thread_name_from_message`), antes da resposta do agente.
- Logs de `Auxiliary title_generation` depois da resposta são o título GPT-style interno de sessão Hermes. Se esse título não estiver conectado a um callback de rename Discord, a UI do Discord continuará mostrando fallback/truncamento.
- Validar via Discord API o `name` atual da thread e comparar com a primeira mensagem/inbound log.
- Se só alguns assuntos parecem inteligentes, provavelmente `_auto_thread_name_from_message(...)` está cobrindo apenas regras hardcoded e o fallback está usando os primeiros termos limpos da mensagem.
- Padrão MGS esperado por Rodolfo: igual ChatGPT — toda thread deve receber título semântico pelo assunto real do primeiro prompt, não só famílias pré-programadas.
- Correção preferida: arquitetura híbrida. Manter regras class-level rápidas no `_auto_thread_name_from_message(...)`, mas conectar o `agent/title_generator.py` pós-primeira resposta a um callback Discord que renomeia a thread com o título GPT-style, sem sobrescrever título manual específico.
- Playbook detalhado: `references/discord-gpt-style-thread-title-rename.md`.

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

