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
| Auto-thread falha com `Too many requests. Retry in ~300 seconds` após uma primeira thread funcionar | Bucket específico do endpoint de criação de threads; retry fixo de 0,75s descarta o pedido antes da janela real |

### Auto-thread sob rate limit do Discord

Quando o log do gateway mostrar `Auto-thread creation failed after retry` junto de `Too many requests. Retry in N seconds`:

1. Confirmar no Discord e no journal os IDs da mensagem/canal e o `retry_after` real. `rate_limit_per_user: 0` no canal não elimina o bucket próprio do endpoint de criação de threads.
2. Preservar a mensagem humana como starter; não reintroduzir fallback com mensagem-semente do bot.
3. Tratar apenas exceções Discord 429/`RateLimited`, extrair `retry_after`, aguardar essa janela uma vez com pequena margem e então repetir a criação.
4. Serializar as criações por canal pai para evitar várias mensagens acordando e golpeando o mesmo bucket; não usar trava global que bloqueie canais Ares independentes.
5. Manter o retry curto existente apenas para falhas transitórias não-429.
6. Validar com teste usando o `retry_after` observado, classificação da exceção real do `discord.py`, `py_compile`, regressão de auto-thread e guard consolidado MGS.
7. Ativar somente pelo restart seguro do gateway afetado e validar serviço ativo + novo marcador de conexão antes do smoke humano.

### Channel permission overwrites and narrow delegation

When Rodolfo asks Zeus to let another agent (Ares/agente legado/Atena) manage future user access to a specific Discord channel, treat it as a channel-scoped permission delegation, not a global admin grant. Validate scope first: list/check the category children before applying category-level changes. If the category contains unrelated infra/admin channels, stop and confirm a narrower channel-only scope.

For Discord API `PUT /channels/{channel_id}/permissions/{overwrite_id}`, `MANAGE_CHANNELS` alone is not enough. The delegated bot also needs effective `MANAGE_ROLES` in that channel context to edit permission overwrites; otherwise validation with the delegated bot token can return `403 Forbidden` even if Zeus/admin can set the overwrite. Use the delegated bot token for final validation, not only Zeus/admin.

Validated narrow pattern:
- Apply bot overwrite on the target channel only: `VIEW_CHANNEL + MANAGE_CHANNELS + MANAGE_ROLES` when the bot must edit channel permission overwrites.
- Add/read users with overwrite `type: 1`, `allow: VIEW_CHANNEL + READ_MESSAGE_HISTORY` (`66560`), `deny: 0`.
- Validate idempotently using the delegated bot token: `PUT /channels/{channel_id}/permissions/{known_user_id}` returns HTTP `204`, then `GET /channels/{channel_id}` confirms the overwrite.
- Register audit log and inventory under `discord_permissions`; explain clearly that `MANAGE_ROLES` is channel-scoped for overwrites, not global role administration.

Reference: `references/discord-channel-permission-overwrites-ares-logs-aquisicao-2026-06-19.md`.

