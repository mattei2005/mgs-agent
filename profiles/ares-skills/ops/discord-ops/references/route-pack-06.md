## SEÇÃO F — Threads: Ciclo de Vida, Tokens e Leitura de Histórico

Ver `references/discord-threads-lifecycle.md` para referência completa.

### Auto-add de membros em threads: diagnosticar prompt/config antes de culpar Discord

Quando Rodolfo relatar que Atena/Zeus cria threads mas parou de colocar pessoas automaticamente nelas, usar `references/discord-thread-auto-add-members-regression.md`. Para a correção aplicada em 2026-05-19 na Atena, ver `references/discord-thread-auto-add-members-2026-05-19.md`.

### Conversa dentro de threads criadas por cron no `logs-aquisicao`

Quando Ares cria relatório no `logs-aquisicao` e Rodolfo responde dentro da thread, Ares deve responder ali. Se Rodolfo reclamar “Mandei lá e você não respondeu”, faça primeiro o reparo operacional: importar/ler a thread específica e responder nela antes de diagnosticar. Depois valide a configuração do gateway.

Pitfall validado no Ares: alterar só `/root/.hermes/profiles/ares/.env` não basta quando `/root/.hermes/profiles/ares/config.yaml` tem seção `discord:`; o config pode manter `allowed_channels`, `free_response_channels` e `thread_require_mention` antigos. Use `hermes -p ares config set discord.allowed_channels ...`, `discord.free_response_channels ...` e `discord.thread_require_mention false`, depois restart seguro via `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`. Detalhe do caso e checklist: `references/discord-logs-aquisicao-thread-chat-2026-06-19.md`.

Lição validada: o gateway Discord do Hermes cria threads via `_auto_create_thread(...)`, mas não adiciona membros extras por padrão. No setup MGS, o comportamento antigo vinha de um `channel_prompts` bootstrap que fazia auto-discover + `PUT /channels/{THREAD_ID}/thread-members/{uid}` via `execute_code`. Se esse prompt/config for simplificado demais, a thread continua sendo criada, mas só ficam o usuário autor + bot/agente.

### Invariante: a mensagem humana deve ser o starter da auto-thread

Em canais com `discord.auto_thread=true`, toda thread criada com sucesso deve nascer de `message.create_thread(...)` aplicado à mensagem humana original. Nunca usar como fallback uma mensagem-semente do bot (`Thread created by Hermes`) e abrir a thread a partir dela: esse caminho faz a thread aparecer como iniciada pelo agente e esconde do histórico interno o texto e os anexos enviados pelo usuário.

Fluxo seguro quando `message.create_thread(...)` falhar:

1. Reconciliar pelo snowflake da mensagem, pois a thread criada a partir de uma mensagem usa o mesmo ID do starter; consultar cache/guild/API antes de repetir.
2. Se a thread já existir, reutilizá-la e continuar o pedido, evitando duplicata em caso de resposta perdida/race.
3. Se não existir, repetir somente `message.create_thread(...)` uma vez após backoff curto.
4. Se persistir a falha, retornar `None`, registrar o erro direto e deixar o caller avisar no canal pai; não criar seed do bot e não executar em uma thread sem a mensagem-fonte.
5. Testar: retry direto, reconciliação de create com resposta perdida, fail-closed sem `channel.send`, dedup e auto-add.

Regressão coberta no runtime MGS por `tests/gateway/test_discord_auto_thread_origin.py`.

Regra operacional atual: Atena/content threads devem auto-add Raquel (`1496254952501280974`) + Rodolfo (`344196393512075265`). Zeus/admin threads atualmente só exigem Rodolfo. Não adicionar todo mundo do guild/canal; usar política explícita por agente/canal.

Diagnóstico mínimo:
- Inspecionar `/root/.hermes/profiles/{atena,zeus}/config.yaml` → `discord.channel_prompts`.
- Procurar no histórico versionado por `thread-members`, `auto-discover`, `renomear thread + adicionar membros`.
- Verificar no gateway (`/root/.hermes/hermes-agent/gateway/platforms/discord.py`) se há `thread.add_user`/`thread-members`; se não houver, core não está fazendo auto-add.
- Consultar Discord API para `GET /channels/{THREAD_ID}/thread-members` e reportar apenas contagem/IDs permitidos; nunca imprimir token/header.

Correção preferida: implementar auto-add determinístico pós-criação no runtime/config (`thread_auto_add_users`/roles) ou restaurar prompt enxuto só para thread comprovadamente nova. Não voltar com script longo em toda resposta/follow-up.



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

### Leitura sob demanda de threads antigas

Quando Rodolfo perguntar se o agente consegue ler uma thread antiga por ID/link, responder com precisão: o contexto ativo não traz automaticamente todo o histórico, mas o agente consegue importar uma thread específica em modo read-only via Discord API **quando o bot do profile tem acesso à thread/canal**. Não responda “só leio o contexto entregue pelo gateway” antes de tentar o importador.

Referência e playbook: `references/discord-thread-importer.md`.

Fluxo padrão:
1. Rodolfo fornece link Discord ou thread/channel ID.
2. Rodar `/root/mgs-agent/scripts/import-discord-thread.py --profile ares --limit 1000 '<link-ou-id>'`.
3. Ler `/root/mgs-agent/data/discord-thread-imports/<thread_id>.md` ou `.json` para responder.
4. Reportar contagem de mensagens, snapshot e modo read-only.
5. Se retornar `403 Missing Access`, reportar que o bot do profile não tem acesso à thread/canal; não inventar conteúdo.
6. Manter `data/discord-thread-imports/` local-only no `.gitignore`; não versionar históricos importados.

---
## SEÇÃO G — Importar histórico de thread antiga por link/ID

Quando Rodolfo/Raquel pedir para Zeus, Atena, Ares ou outro agente MGS ler uma thread antiga, use o importador read-only canônico por link/ID. Ver `references/discord-thread-history-import.md`.

Comandos padrão:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile legacy-agent '<LINK_OU_ID>'
```

Pitfall: usar o `--profile` correto evita tentar acessar private threads com o token do bot errado. Os snapshots em `data/discord-thread-imports/` são local-only e não devem ser versionados.

---
