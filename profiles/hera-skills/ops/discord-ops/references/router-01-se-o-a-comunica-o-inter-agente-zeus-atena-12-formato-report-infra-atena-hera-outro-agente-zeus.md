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

