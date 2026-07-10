### Diagnóstico de título ruim em auto-thread

Quando Rodolfo perguntar por que uma thread não foi renomeada, ou por que o título ficou genérico/truncado, não assumir erro de Discord/permissão. Ver `references/discord-auto-thread-title-diagnostics.md`.

Pitfall validado em 2026-06-13: não recomputar em `run.py` o título provisório da thread a partir do `message` do gateway para decidir se pode renomear. Esse texto pode vir mutado com `[Rodolfo Mattei]`, `[READ-ONLY RECENT CHANNEL CONTEXT]`, `[New message — ACTIONABLE USER REQUEST]`, enriquecimento de mídia/documento/STT ou batching; não há garantia byte-a-byte com o `message.content` usado em `adapter.py:_auto_create_thread`. A solução segura é salvar no adapter o `thread_name` provisório exato usado na criação (`thread_id -> thread_name`) e, no guard de rename por IA, comparar o nome atual do Discord contra esse valor salvo. Se o valor não existir, falhar fechado e não renomear. Detalhe: `references/discord-file-attachments-and-thread-title-rename-2026-06-13.md`.

Localização atual da lógica de nome de thread Discord no Hermes MGS:
- `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py` é o arquivo principal do adapter Discord plugin.
- `_auto_thread_name_from_message(...)` decide o título inicial/semântico determinístico.
- `_auto_create_thread(...)` chama `message.create_thread(name=thread_name, ...)` e cria a thread com esse nome.
- O fluxo em `_handle_message(...)` decide se auto-thread roda ou é pulado por reply, DM, voice-linked, `DISCORD_NO_THREAD_CHANNELS`, `[REPORT-INFRA]`, etc.
- `/root/.hermes/hermes-agent/gateway/run.py` ainda contém helpers `_rename_discord_thread_for_session_title(...)` e `_schedule_discord_thread_title_rename(...)`, mas no fluxo MGS o callback de auto-title pós-resposta para Discord fica desativado para não renomear thread antiga/follow-up. Não confundir esses helpers com a origem normal do título inicial.

