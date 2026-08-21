### Adding a user to a private Discord thread

When Rodolfo asks to add Raquel/Kelly/Geizian/Ially/gestor or another approved person to a Zeus/Atena/Ares/agente legado thread, **execute it**; do not answer “não consigo” unless API validation proves a real blocker. Use Discord API `PUT /channels/{thread_id}/thread-members/{user_id}`. Do this even when no dedicated `discord_admin` tool is loaded: load the bot token from the active profile `.env` or runtime service environment inside a terminal/shell command, call Discord API directly, and never print the token.

Canonical helper for the normal path:

```bash
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile <agent> --thread <thread_id> --user <user_id>
```

If it returns `403 Missing Access`, diagnose before refusing:
- `GET /channels/{thread_id}` with the posting bot token to confirm thread access and read `type` + `parent_id`.
- Search/confirm the user ID in the guild if only a human name was provided.
- Distinguish a private thread from a **public thread under a private parent channel**. For a public thread, adding a user who cannot view the parent requires a parent-channel overwrite; this broadens visibility beyond the requested thread because the user can then see the parent channel and its other public threads.
- When the original request says only “add X to this thread,” report the `403`, explain that parent access is required and broader, and obtain explicit confirmation before changing the parent overwrite. This is a scope-expanding prerequisite, not a routine hidden implementation detail.
- After confirmation, Zeus/admin can set a **minimal parent-channel user overwrite** (`VIEW_CHANNEL + SEND_MESSAGES + READ_MESSAGE_HISTORY + SEND_MESSAGES_IN_THREADS`) and retry the thread-member PUT. Current permission bitfield for that exact set is `274877975552`; send it as a decimal string with `deny=0` and overwrite `type=1` (member).
- Validate parent overwrite `PUT=204` and independent channel `GET=200` with exact overwrite readback, then validate `PUT .../thread-members/{user_id}` = `204` and `GET .../thread-members/{user_id}` = `200` before claiming success.
- Record the authorization, target user, parent/thread IDs, permission bitfield, HTTP statuses, and final result in `logs/events-audit.jsonl` without secrets.

For Zeus, keep this command pattern in `command_allowlist`/Always Allow so routine thread adds do not create approval friction:

```text
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Do not claim the thread add succeeded until the API returns `204`; verify with `GET /channels/{thread_id}/thread-members/{user_id}` returning `200` when possible.

Zeus-specific correction validated: if the helper returns `403 Missing Access` because the user is not in the parent private channel, first determine whether the required parent overwrite expands visibility beyond the requested thread. For a public thread, explain that broader access and obtain explicit confirmation; then apply the narrow parent-channel overwrite (`VIEW_CHANNEL`, `SEND_MESSAGES`, `READ_MESSAGE_HISTORY`, `SEND_MESSAGES_IN_THREADS`) and retry the helper/API add. Confirm success only after parent overwrite `204` when needed, independent overwrite readback, thread-member PUT `204`, and member GET `200`. Rodolfo expects Zeus to resolve this path rather than answer that it cannot add people, while still surfacing scope expansion before changing permissions. For exact reproduction and allowlist details, see `references/discord-thread-member-parent-access-and-allowlist-2026-06-29.md`.

For Zeus, this helper should be in `command_allowlist` as:

```text
/root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Operational correction validated on agente legado and Ares: if the agent replied “não consigo adicionar pessoas na thread”, fix the profile so future requests are executable, not just manually handled once:

```yaml
command_allowlist:
- /root/mgs-agent/scripts/discord-add-thread-member.sh --profile zeus --thread * --user *
```

Validate via ad-hoc `/tmp/hermes-verify-*` script: YAML parses, entry appears exactly once in active + versioned Zeus config, and a representative command matches the glob. This is not suite green.

Operational correction validated on agente legado and Ares: if the agent replied “não consigo adicionar pessoas na thread”, fix the profile so future requests are executable, not just manually handled once:
- Add the explicit user IDs to `discord.thread_auto_add_users` in `config.yaml` for automatic inclusion in new threads.
- If `.env` already defines `DISCORD_THREAD_AUTO_ADD_USERS`, update `.env` too; runtime env takes precedence over config hydration (`config.yaml` only sets env when the env var is absent).
- Add a short channel prompt/SOUL rule: on Rodolfo’s natural-language “adiciona X na thread”, call `/root/mgs-agent/scripts/discord-add-thread-member.sh --profile <agent> --thread <thread_id> --user <user_id>` or the equivalent Discord API directly, and confirm only after HTTP 204/GET 200; on 403, report Missing Access/parent-channel access needed.
- Restart the affected gateway and verify `systemctl is-active`, `Connected as ...`, `✓ discord connected`, and that `/proc/<pid>/environ` has the updated auto-add env value length/count without printing secrets.
- Record the authorization/profile change in `events-audit.jsonl` and check live config equals versioned config before reporting completion.

Pitfall: avoid rewriting full `config.yaml` with PyYAML for small profile edits unless necessary; it can reformat unrelated fields and generate noisy auto-commits. Prefer targeted patches, or restore from backup and reapply minimal textual edits before final validation. Auto-push/auto-commit may capture intermediate config states, so inspect recent commits/status if the edit was iterative.

Session reference: `references/discord-thread-member-autonomy-ares-legacy-agent-2026-06-16.md`.

### Separar canal privado/diretoria e canal de equipe

Use quando um agente atende liderança e gestores, mas Rodolfo precisa abrir conversas que não incluam automaticamente toda a equipe. Não criar outro agente apenas para resolver membership/visibilidade: um único profile pode atender vários canais com sessões separadas e o mesmo estado operacional.

Padrão recomendado, com privacidade por default:

1. Manter ou renomear o canal existente como `<agente>-gestores`/equipe, preservando os overwrites humanos já autorizados.
2. Criar `<agente>-diretoria` na mesma categoria com overwrite explícito:
   - `@everyone`: negar `VIEW_CHANNEL`;
   - Rodolfo: permitir `VIEW_CHANNEL`;
   - bot do agente: permitir o conjunto operacional necessário para responder/criar threads.
3. Remover o auto-add global (`discord.thread_auto_add_users: []` e `DISCORD_THREAD_AUTO_ADD_USERS=`). Essa lista é global por profile; mantê-la faria gestores entrarem também nas threads da Diretoria. Participantes extras entram apenas por pedido natural via helper/API.
4. Adicionar o novo channel ID em `discord.allowed_channels` e `discord.free_response_channels`, além de um `channel_prompts.<id>` curto declarando a privacidade por padrão.
5. Verificar `.env` antes de confiar em `config.yaml`: `DISCORD_ALLOWED_CHANNELS`, `DISCORD_FREE_RESPONSE_CHANNELS` e `DISCORD_THREAD_AUTO_ADD_USERS` prevalecem no processo quando definidos.
6. Atualizar config vivo + mirror versionado com edição textual mínima; validar YAML e igualdade dos artefatos relevantes.
7. Reiniciar o gateway pelo finalizer seguro porque mudanças de `.env`/roteamento são carregadas no startup. No processo novo, validar `/proc/<pid>/environ` sem imprimir tokens: novo channel ID presente e auto-add vazio.
8. Readback Discord obrigatório: canal novo `GET=200`, nome/categoria corretos e IDs dos overwrites exatamente no escopo planejado. Registrar audit, inventário e REPORT-INFRA.

Quando a reorganização também excluir um canal redundante, aplicar este fechamento antes do delete:

1. Tratar a exclusão do canal como operação crítica e obter a confirmação adicional mesmo quando o pedido inicial já disser “pode deletar”.
2. Inventariar mensagens, pins e threads ativas do canal. Deletar o canal pai também elimina as threads filhas e seus históricos.
3. Exportar via API o objeto do canal, permission overwrites, mensagens do pai e mensagens de cada thread; salvar em backup seguro e validar hashes antes do delete.
4. Atualizar primeiro config vivo, mirror versionado e overrides de `.env` (`DISCORD_ALLOWED_CHANNELS`, `DISCORD_FREE_RESPONSE_CHANNELS`, `DISCORD_HOME_CHANNEL`). Não imprimir nem diffar o `.env` inteiro: editar somente as linhas não secretas por mecanismo que não exponha linhas vizinhas.
5. Recriar a audiência exata dos canais preservados: negar `VIEW_CHANNEL` ao `@everyone`, adicionar usuários/bots aprovados e remover explicitamente bots/roles antigos. Validar o conjunto completo de overwrite IDs, não apenas a contagem.
6. Excluir o canal somente depois do backup e da configuração; validar `GET /channels/{parent}=404` e também `GET /channels/{thread}=404`.
7. Remover a entrada do inventário customizado: discovery genérico pode não podar artefatos Discord registrados manualmente. Confirmar por readback que o ID excluído desapareceu do inventário e que os canais preservados estão presentes com nomes e audiências atuais.
8. Reiniciar o gateway afetado pelo fluxo seguro, confirmar env efetivo do processo sem segredos, conexão Discord e rotas carregadas; então registrar audit e REPORT-INFRA.

Criar subagente separado somente quando também houver separação real de área, dados, ferramentas, autoridade ou fonte de verdade. Para mera privacidade de conversa, dois canais do mesmo agente reduzem drift e manutenção.

#### Regressão de auto-add em profile com canal privado + canal de equipe

Quando um mesmo profile atende um canal privado e outro compartilhado, esvaziar o `thread_auto_add_users` global protege o privado, mas também desliga o auto-add do canal de equipe. Isso é uma regressão de escopo, não falha do Discord.

Diagnóstico mínimo:

1. Confirmar o `parent_id` da thread e qual política deveria valer naquele canal.
2. Ler `discord.thread_auto_add_users` no config vivo e mirror, depois conferir `DISCORD_THREAD_AUTO_ADD_USERS` no processo sem imprimir segredos. O env efetivo vence a hidratação do config.
3. Consultar `GET /channels/{thread_id}/thread-members?with_member=true`; se houver apenas autor + bot, o auto-add não ocorreu.
4. Reconciliar Git/audit para descobrir se a lista foi removida deliberadamente durante uma separação de diretoria/equipe.
5. Reparar imediatamente a thread afetada com o helper canônico para cada participante explicitamente aprovado, respeitando `429 Retry-After`, e validar todos por GET/readback.

Correção durável preferida: suportar uma lista explícita **por canal pai**, com fallback global somente para profiles de política única. Um canal privado deve poder declarar lista vazia sem cair em auto-discovery amplo; o canal de equipe declara sua lista de usuários. Até esse suporte estar implantado e validado, não reativar a lista global em profile misto, pois isso vaza membership/notificações para o canal privado.

Critério de aceite da correção durável:

- teste unitário para canal privado vazio e canal compartilhado com lista explícita;
- config vivo e mirror com o mesmo mapa por canal;
- restart seguro do gateway afetado;
- validar no próximo thread real aberto pelo usuário e reportar na thread de origem; criar live smoke visível somente com autorização explícita prévia;
- quando houver thread real disponível, GET de membros comprovando que o canal compartilhado recebeu somente os aprovados e o privado não recebeu extras;
- audit, inventário e REPORT-INFRA quando runtime/config estrutural forem alterados.

Pitfalls:

- Não usar `thread_auto_add_users` global para “facilitar” o canal de equipe quando o mesmo profile também atende um canal privado; a lista global atingiria ambos.
- Preferir `thread_auto_add_users_by_channel`: lista explícita no canal operacional e `[]` no privado. O vazio explícito deve falhar fechado, sem auto-discovery. Procedimento e testes: `references/discord-thread-auto-add-members-regression.md`.
- Não tratar lista global vazia como autorização para descobrir/adicionar todos os membros visíveis do guild; vazio explícito deve significar “não adicionar ninguém”.
- Não confundir usuário autorizado a operar o agente com participante automático de toda thread. Autorização, visibilidade do canal e membership da thread são camadas diferentes.
- Antes de diagnosticar auto-thread de um usuário autorizado, conferir a allowlist humana efetiva do gateway. O adapter aplica `DISCORD_ALLOWED_USERS` antes de `_handle_message` e antes da criação automática da thread; se o `.env` contém apenas Rodolfo, os demais gestores ficam silenciosamente bloqueados mesmo quando o canal, `authorized-users.json` e `thread_auto_add_users_by_channel` estão corretos. Para profiles de equipe, exigir paridade de conjunto entre `data/authorized-users.json` → `discord.allow_from` no config vivo/mirror → `DISCORD_ALLOWED_USERS` no `.env` e no `/proc/<pid>/environ`. O `.env` vence o YAML. Nunca corrigir com wildcard; incluir somente IDs já autorizados, reiniciar com finalizer seguro e validar contagem/conjunto efetivo sem expor token.
- Não criar thread visível de smoke/teste em canal operacional para validar auto-add sem autorização explícita de Rodolfo. Preferir testes automatizados, config/runtime readback e uma thread real aberta pelo próprio usuário; reportar a validação na thread de origem. Se um live smoke isolado for indispensável, explicar antes o artefato visível e pedir autorização específica para criá-lo.
- Não assumir que renomear um canal atualiza nomes descritivos em dados/scripts: procurar o ID canônico e corrigir labels ativos, preservando referências históricas como histórico.
- Não confiar em uma chamada de escrita que depois falhou no parser de resposta: fazer GET independente e comparar o estado inteiro antes de repetir writes idempotentes.
- Validador pós-restart nunca pode interpretar `systemctl show --value` por posição: a ordem emitida pode ser `MainPID`, `ActiveState`, `SubState` mesmo quando os argumentos foram passados em outra ordem. Ler `key=value`, validar por nome, aguardar `active/running` com polling limitado e exigir markers de conexão posteriores ao `ActiveEnterTimestamp`. Um one-shot concluído não retoma sozinho; falha durante/paralela ao restart permanece histórica e exige nova revalidação explícita.
- O `file_mutation_verifier` pode anexar um footer enganoso quando uma tentativa tardia de patch falha depois que o writer canônico já gravou e o readback final passou. Estado final deve ser decidido por readback, não pelo footer de tentativas. Nos profiles Discord MGS, manter `display.inline_diffs: false` e `display.file_mutation_verifier: false` para não vazar trace/backend em respostas; validar tipo booleano e mirror, e recarregar o gateway pelo fluxo seguro.
- Ao criar ou reorganizar canal por API, nunca imprimir o bot token; retornar apenas status, channel ID, nome, parent e IDs/contagem dos overwrites.


#### Conferência pós-update/restart não é só “online”

Quando Rodolfo pedir para “conferir tudo de novo” após update, limpeza ou restart Hermes, não responder apenas que gateways estão `active/running`. Se a preocupação declarada for perda de configuração/patch local, validar e reportar explicitamente a recuperação da superfície local:
- comparar todos os markers/funções do `pre-local-diff.patch` e `pre-local-diff-cached.patch` contra o runtime vivo;
- rodar `ensure-hermes-mgs-patches.sh`, `py_compile` e testes alvo;
- separar `runtime íntegro` de `higiene de patch artifact`;
- dizer claramente quantos markers foram conferidos e quantos faltam, ex.: `35/35 OK, missing=0`.

Pitfall validado: responder “Zeus/Atena/Ares/agente legado online” quando Rodolfo perguntou se “recuperou tudo que estava fora” é incompleto e irrita, porque ele já sabe que os serviços estão online; a pergunta é sobre integridade dos patches/configs locais.

### Diagnóstico de título ruim em auto-thread

Quando Rodolfo perguntar por que uma thread não foi renomeada, ou por que o título ficou genérico/truncado, não assumir erro de Discord/permissão. Ver `references/discord-auto-thread-title-diagnostics.md`.

Pitfall validado em 2026-06-13: não recomputar em `run.py` o título provisório da thread a partir do `message` do gateway para decidir se pode renomear. Esse texto pode vir mutado com `[Rodolfo Mattei]`, `[READ-ONLY RECENT CHANNEL CONTEXT]`, `[New message — ACTIONABLE USER REQUEST]`, enriquecimento de mídia/documento/STT ou batching; não há garantia byte-a-byte com o `message.content` usado em `adapter.py:_auto_create_thread`. A solução segura é salvar no adapter o `thread_name` provisório exato usado na criação (`thread_id -> thread_name`) e, no guard de rename por IA, comparar o nome atual do Discord contra esse valor salvo. Se o valor não existir, falhar fechado e não renomear. Detalhe: `references/discord-file-attachments-and-thread-title-rename-2026-06-13.md`.

Localização atual da lógica de nome de thread Discord no Hermes MGS:
- `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py` é o arquivo principal do adapter Discord plugin.
- `_auto_thread_name_from_message(...)` decide o título inicial/semântico determinístico.
- `_auto_create_thread(...)` chama `message.create_thread(name=thread_name, ...)` e cria a thread com esse nome.
- O fluxo em `_handle_message(...)` decide se auto-thread roda ou é pulado por reply, DM, voice-linked, `DISCORD_NO_THREAD_CHANNELS`, `[REPORT-INFRA]`, etc.
- `/root/.hermes/hermes-agent/gateway/run.py` ainda contém helpers `_rename_discord_thread_for_session_title(...)` e `_schedule_discord_thread_title_rename(...)`, mas no fluxo MGS o callback de auto-title pós-resposta para Discord fica desativado para não renomear thread antiga/follow-up. Não confundir esses helpers com a origem normal do título inicial.

