# REPORT-INFRA em embed sem mention e sem thread (2026-07-02)

## Contexto
Rodolfo reclamou que REPORT-INFRA/alertas em `#alerts-infra` estavam abrindo threads e mencionando Zeus/Rodolfo. O print mostrou threads criadas por webhook como `Confirmação de recebimento - Webhook` e `Ping de webhook sem payload - Webhook`.

## Causa raiz
O helper/report anterior enviava mentions no `content` do webhook (`<@Zeus> <@Rodolfo>`). Como Zeus aceita mensagens de bots/webhooks quando é mencionado (`DISCORD_ALLOW_BOTS=mentions`), o próprio Zeus acordava no `#alerts-infra`. Com `auto_thread=true` e o canal não listado em `no_thread_channels`, o adapter Discord criava threads automaticamente e depois renomeava pelo título gerado.

## Regra operacional
Para REPORT-INFRA e alertas operacionais normais em `#alerts-infra`:

- `content` deve ser string vazia: sem mention de Zeus, Rodolfo ou qualquer pessoa.
- Usar embed com fields (`Ação`, `Tipo`, `Path`, `Motivo`, `Evidência`, etc.).
- `#alerts-infra` deve estar em `discord.no_thread_channels` do Zeus para impedir auto-thread nesse canal.
- Não fazer teste real repetido no canal depois de corrigir; validar por config/log/helper e só postar quando houver necessidade operacional real.
- Mentions ficam reservadas para alerta crítico com push explicitamente necessário, não para REPORT-INFRA rotineiro.

## Implementação validada
- Helper: `/root/mgs-agent/scripts/send-report-infra-embed.sh`
  - `PAYLOAD.content == ""`
  - webhook real retornou HTTP 204
- Config Zeus:
  - `discord.no_thread_channels: '1498132022634483894'`
  - ativo em `/root/.hermes/profiles/zeus/config.yaml`
  - versionado em `/root/mgs-agent/profiles/zeus-config.yaml`
- Restart seguro do gateway necessário para o `no_thread_channels` entrar em runtime.

## Checklist futuro
1. Antes de enviar alerta no `#alerts-infra`, verificar se o caminho usa `send-report-infra-embed.sh` ou outro payload com `content:""`.
2. Se surgir thread automática de webhook, checar `agent.log` por `inbound message user=Webhook` e `Discord thread renamed... Webhook`.
3. Se aparecer, validar `DISCORD_NO_THREAD_CHANNELS` efetivo no ambiente do serviço e reiniciar Zeus via restart seguro.
4. Atualizar scripts antigos que ainda postem `[REPORT-INFRA] ...` em texto cru quando forem tocados.
