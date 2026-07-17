# Discord new-thread title guardrails — 2026-06-07

## Incident

Rodolfo corrected the interpretation of the “do not rename existing threads” rule. A new agente legado thread (`1513332390804721730`) was auto-created with the deterministic fallback title:

```text
Pedir Criativo Teste Mas Coloque
```

Rodolfo expected a new thread to still get the normal semantic/GPT-style title. The desired title for that example was:

```text
Criativo de Teste
```

## Lesson

The policy is not “never rename Discord threads”. It is:

```text
New auto-created thread  -> may receive exactly one semantic rename after first response.
Existing/open thread     -> must never be renamed by follow-up/reset/idle/session-title churn.
```

Removing the Discord `title_callback` entirely fixes old-thread churn but regresses new-thread naming.

## Correct implementation pattern

In `gateway/run.py`, keep the Discord `maybe_auto_title(..., title_callback=...)` path for `source.platform == Platform.DISCORD and source.chat_type == "thread"`, but pass a clean actionable first user message into the guard.

The rename coroutine should only edit when all are true:

1. Source is a Discord thread.
2. Thread ID resolves to a channel with `.edit(...)`.
3. Thread owner is the current bot (`channel.owner_id == client.user.id`) when those fields are available.
4. Thread is recent (short post-create window, e.g. 30 minutes). If age cannot be trusted, skip rather than risk an old-thread rename.
5. Current name equals the deterministic initial title:
   `adapter._auto_thread_name_from_message(clean_actionable_user_message)`, sanitized the same way as the generated title.
6. Generated title is non-empty and differs from current name.

If any check fails, log a skip reason and do not mutate the thread.

## Validation checklist

```bash
cd /root/.hermes/hermes-agent
python3 -m py_compile gateway/run.py plugins/platforms/discord/adapter.py
```

For a reported thread ID:

```bash
set -a; source /root/.hermes/profiles/<agent>/.env; set +a
curl -sS -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/channels/<THREAD_ID>" \
  | jq '{id,name,parent_id,owner_id,type,thread_metadata}'
```

Check logs for:

```text
Discord GPT-style thread title applied: ...
Discord GPT-style thread title skipped: ... reason=...
```

## Reporting language

Use this distinction explicitly:

```text
Thread nova: pode ganhar título semântico uma vez.
Thread já aberta: não renomeia por follow-up/reset/pausa.
```

Avoid saying “não renomeia mais thread” without the new-thread exception; Rodolfo will interpret that as breaking the desired ChatGPT-like behavior.
