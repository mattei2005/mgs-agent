# Discord Thread History Import — Read-only por link/ID

## Quando usar

Use quando Rodolfo/Raquel pedir para Zeus ou Atena ler uma thread antiga do Discord e fornecer:

- link da thread;
- ID da thread/canal;
- link de mensagem Discord.

## Script canônico

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
```

O script é read-only contra Discord e grava snapshots locais em:

```text
/root/mgs-agent/data/discord-thread-imports/<thread_id>.json
/root/mgs-agent/data/discord-thread-imports/<thread_id>.md
```

`data/discord-thread-imports/` deve permanecer local-only/ignored no git; o script é versionado, os históricos importados não.

## Sequência operacional

1. Receber link/ID do usuário.
2. Rodar o importador com o profile do agente que precisa ler a thread.
3. Ler o `.md` gerado.
4. Responder apenas com base no histórico importado ou em logs locais.
5. Se a API retornar 403/404, reportar acesso insuficiente do bot ou ID/link inválido — não inventar conteúdo.

## Pitfalls

- Para Atena, usar `--profile atena`; para Zeus, usar `--profile zeus`. Isso evita usar o token do bot errado em private threads.
- Não expor `DISCORD_BOT_TOKEN`, headers de autorização ou payloads sensíveis no chat.
- Link de mensagem é aceito; o parser extrai o channel/thread ID do formato `/channels/{guild}/{channel_or_thread}/{message}`.
- Se a thread for private, o bot precisa ser membro da thread ou ter permissão suficiente (`Read Message History`).
