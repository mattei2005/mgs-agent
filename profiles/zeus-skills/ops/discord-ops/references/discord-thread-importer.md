# Discord Thread Importer — leitura sob demanda de threads antigas

## Contexto

Zeus não deve afirmar que consegue ler qualquer thread antiga diretamente pelo contexto do chat. O contexto ativo contém apenas a thread atual e mensagens entregues ao agente. Para consultar uma thread antiga específica, Rodolfo deve fornecer um link Discord ou thread/channel ID, e Zeus importa o histórico via Discord API em modo read-only.

## Script canônico

`/root/mgs-agent/scripts/import-discord-thread.py`

Uso:

```bash
cd /root/mgs-agent
scripts/import-discord-thread.py '<discord-link-ou-thread-id>'
```

Opções úteis:

```bash
scripts/import-discord-thread.py '<link-ou-id>' --limit 100
scripts/import-discord-thread.py '<link-ou-id>' --out-dir /root/mgs-agent/data/discord-thread-imports
```

## Saída

Arquivos locais:

```text
/root/mgs-agent/data/discord-thread-imports/<thread_id>.json
/root/mgs-agent/data/discord-thread-imports/<thread_id>.md
```

`data/discord-thread-imports/` deve permanecer no `.gitignore`: histórico importado é material operacional/local, não artefato para versionar.

## Fluxo operacional recomendado

1. Rodolfo manda: `Zeus, lê essa thread: <link>`.
2. Extrair link/ID e rodar o importador.
3. Ler o `.md` importado para responder com base no histórico real.
4. Se a Discord API retornar 403/404, explicar operacionalmente: bot sem acesso à thread, sem `Read Message History`, ou private thread sem membership.
5. Não fazer crawler geral por padrão. Importar só a thread explicitamente indicada por Rodolfo.

## Validação mínima ao alterar o script

```bash
cd /root/mgs-agent
python3 -m py_compile scripts/import-discord-thread.py
scripts/import-discord-thread.py --help
```

Se testar contra thread real, use `--limit` primeiro para limitar volume. Nunca exibir `DISCORD_BOT_TOKEN` ou qualquer credencial no chat.

## Pitfalls

- Discord links têm formato `https://discord.com/channels/{guild_id}/{thread_or_channel_id}/{message_id?}`; o ID importante para importação é o segundo ID depois do guild.
- Private threads podem exigir que o bot seja membro da thread, mesmo se tiver acesso ao canal pai.
- Importar histórico não deve postar mensagem nem modificar thread; o script é read-only contra Discord.
- Auto-commit pode tentar versionar snapshots se `.gitignore` não cobrir a pasta. Verificar `git status --short` após testes reais.
