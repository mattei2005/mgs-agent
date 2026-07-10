### Formato REPORT-INFRA (Atena/Ares → Zeus)

Dois user mentions: bot Zeus (para `DISCORD_ALLOW_BOTS=mentions`) + Rodolfo (push notification):

```
[REPORT-INFRA] <@1496296175014252634> <@344196393512075265>
Ação: criada/modificada/removida
Tipo: cron / skill / script / config / data
Path: caminho exato
Motivo: contexto
Evidência: hash de commit ou output de comando
```

Ares-specific pitfall: REPORT-INFRA **não deve abrir thread** no canal de infra/alertas. Para Ares, preferir sempre `/root/mgs-agent/scripts/ares-report-infra.sh` via webhook. Não usar `/root/mgs-agent/scripts/ares-discord-post-with-thread.py` para `[REPORT-INFRA]` sem `--thread-id`, porque isso posta no canal e cria thread automática. Se precisar validar sem sujar o Discord: `printf '[REPORT-INFRA] test\n' | /root/mgs-agent/scripts/ares-report-infra.sh --dry-run`.

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

