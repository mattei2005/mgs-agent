---
name: hermes-agent-restart
description: Diagnostica e reinicia agentes Hermes (Atena, Zeus, etc) quando estão online mas não respondem no Discord. Cobre sessão Discord stale, rate limit em loop, e crash silencioso.
version: 1.0.0
author: Zeus
---

# Hermes Agent Restart — Diagnóstico e Reinicialização

## Quando usar

- Agente está online (processo rodando) mas não responde no Discord
- Mensagens não aparecem como `inbound message` no log
- Agente travou em loop de rate limit e foi reiniciado, mas não recebe novos eventos
- Usuário relata silêncio após período de alta atividade

## Sintomas típicos

| Sintoma | Causa provável |
|---------|---------------|
| Processo rodando, Discord conectado, mas sem `inbound message` no log | Sessão Discord stale OU Message Content Intent desabilitada no portal |
| Múltiplos `Retrying request` com waits longos (21s, 45s, 56s) | Rate limit Anthropic |
| Gateway reiniciou mas parou de receber após reconexão | Sessão zumbi pós-restart |
| `response ready` com `time=1139s` (>10 min) | Pipeline longo + rate limit acumulado |

## Diagnóstico

```bash
# 1. Verificar se processo está rodando
ps aux | grep -E "hermes.*atena|hermes.*zeus" | grep -v grep

# 2. Verificar últimas linhas do log
tail -30 /root/.hermes/profiles/atena/logs/agent.log

# 3. Checar se mensagens estão chegando
grep "inbound message" /root/.hermes/profiles/atena/logs/agent.log | tail -5

# 4. Ver se está em loop de rate limit
grep -E "Retry|inbound|response ready|ERROR" /root/.hermes/profiles/atena/logs/agent.log | tail -20
```

**Sessão stale confirmada quando:** processo está vivo, log mostra `Connected as Atena#2956`, mas nenhum `inbound message` novo após mensagens enviadas pelo usuário.

## Reinicialização

```bash
# 1. Matar processo
pkill -f "hermes -p atena gateway run"

# 2. Confirmar que morreu
sleep 2 && ps aux | grep "atena" | grep -v grep

# 3. Reiniciar em background (OBRIGATÓRIO usar background=true — não usar nohup/disown)
# Via terminal(background=true, command="atena gateway run")

# 4. Verificar conexão (aguardar ~5s)
sleep 5 && tail -10 /root/.hermes/profiles/atena/logs/agent.log
```

Confirmar sucesso quando log mostrar:
```
Connected as Atena#2956
✓ discord connected
Gateway running with 1 platform(s)
```

## Causa raiz difícil: Message Content Intent

Se após reinicialização e confirmação de conexão o agente **continua sem receber mensagens** (nenhum `inbound message` no log após mensagens enviadas pelo usuário), o problema não é o processo nem a sessão Discord — é uma **configuração no Discord Developer Portal**.

**Verificar:**
1. https://discord.com/developers/applications → selecionar a aplicação do bot
2. Aba **Bot** → seção **Privileged Gateway Intents**
3. Confirmar que **Message Content Intent** está **habilitada**

Sem essa intent, o bot conecta normalmente, aparece online, mas o Discord não entrega eventos de mensagem — silêncio total no log.

**Identificar esse caso:** reiniciou o agente, confirmou `Connected as Atena#2956` e `Gateway running`, mas mesmo assim zero `inbound message` após múltiplas mensagens do usuário → suspeitar de intent desabilitada.

## Pitfalls

- **Não usar `nohup/disown/&` no terminal foreground** — Hermes rejeita; usar `terminal(background=true)`
- **Sessão zumbi é silenciosa** — Discord mostra o bot como online mas eventos não chegam; só detectável pelo log
- **Rate limit Anthropic não derruba o gateway** — o processo continua vivo e retrying; só para se o usuário ou sistema reinicia manualmente
- **Após reiniciar, nova sessão Discord é criada** — Session ID muda, mas isso é normal e esperado
- **`pkill` mata pelo padrão exato** — usar `pkill -f "hermes -p atena gateway run"` para não matar outros perfis (zeus, etc)
- **Instância em terminal interativo (pts/N)** — se o agente foi iniciado manualmente num terminal aberto (ex: `pts/2`), o output vai para aquele terminal, NÃO para o agent.log. O log fica parado mas o processo está vivo e recebendo. Detectar com `ps aux | grep atena` e checar a coluna `TTY` — se for `pts/N` em vez de `?`, está num terminal interativo.
- **Múltiplas instâncias conflitam** — ao reiniciar, verificar se já não há PID ativo com `hermes gateway` PID file. Se sim, usar `hermes gateway restart` ou `hermes gateway run --replace` em vez de matar e subir manualmente. Subir uma segunda instância quando já há uma ativa resulta em erro `Another gateway instance is already running`.
- **`terminal(background=true)` não redireciona pro agent.log automaticamente** — o processo filho escreve no stdout do Hermes, não no log do perfil. Para garantir que logs vão ao arquivo correto, o processo já existente em pts/N é preferível — verificar se ele está funcional antes de reiniciar.
- **`config.yaml` sobrescreve `.env` para `allowed_channels`** — se `discord.allowed_channels` estiver vazio (`''`) no `config.yaml`, o agente ignora TODAS as mensagens silenciosamente, mesmo que `DISCORD_ALLOWED_CHANNELS` esteja correto no `.env`. O bot conecta, aparece online, mas não recebe nada. Fix: definir `allowed_channels: '1496267571543019653'` no `config.yaml`. Esse é o **primeiro lugar a checar** quando o agente reconectou após reinicialização mas ainda não recebe mensagens e a Message Content Intent está habilitada.
- **Mensagens de outros bots são ignoradas por padrão** — `DISCORD_ALLOW_BOTS` no `.env` do agente destino controla isso. Default é `none` (ignora todos os bots silenciosamente). Para comunicação inter-agente (ex: Zeus→Atena), usar `DISCORD_ALLOW_BOTS=mentions` — o agente origem deve incluir `<@BOT_ID>` no texto da mensagem para que o destino a aceite. `all` aceita qualquer bot (não recomendado).

## Patch local busy_input_mode em gateway

Existe patch local aplicado em `/root/.hermes/hermes-agent/gateway/run.py` que faz `busy_input_mode: queue` funcionar em gateway mode durante operação normal (não só durante drain de restart). Documentação em `/root/mgs-agent/patches/hermes/`.

Quando o Hermes for atualizado:
1. Verificar se patch ainda está presente: `grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py`
2. Se não estiver, reaplicar: `patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch`
3. Restart: `systemctl restart zeus-gateway atena-gateway`

Issue upstream: https://github.com/NousResearch/hermes-agent/issues/14905

## Logs úteis

```
/root/.hermes/profiles/atena/logs/agent.log   # Atividade principal
/root/.hermes/profiles/atena/logs/errors.log  # Erros e warnings
/root/mgs-agent/logs/generate-rec.log          # Log do pipeline REC
/root/mgs-agent/logs/events-audit.jsonl        # Audit trail de eventos
```
