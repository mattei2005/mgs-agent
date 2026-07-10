### Correção preferida: título IA uma vez após a primeira resposta

Quando Rodolfo pedir para corrigir thread title “burro”/regex/hardcoded no Discord, não mexer em `_auto_thread_name_from_message(...)` como solução primária. Ela deve continuar gerando o nome provisório porque Discord cria a thread antes da resposta. A correção correta é no `gateway/run.py`: conectar o `title_callback` do Discord ao `maybe_auto_title(...)` pós-primeira resposta, mas proteger o rename com `_discord_thread_safe_to_autorename(...)`.

Guardrails mínimos:
- `maybe_auto_title(...)` já só tenta título nas primeiras trocas; manter esse filtro.
- A thread Discord deve ser nova (`channel.created_at` dentro de janela curta, ex. 30 min), bloqueando follow-up depois de idle/reset.
- O nome atual da thread deve ainda ser o provisório calculado por `adapter._auto_thread_name_from_message(primeira_mensagem_acionável)`, sanitizado via `_sanitize_discord_thread_title(...)`; se divergir, assumir rename manual/IA anterior e não editar.
- A validação deve rodar imediatamente antes de `channel.edit(...)`, porque o auto-title roda em background thread e agenda coroutine async.

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

