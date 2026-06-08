# Discord GPT-style semantic thread titles

## Trigger

Use this when Rodolfo reports that Discord thread names only look good for a few hardcoded subjects, or asks for ChatGPT-like/GPT-style thread naming across Zeus, Atena, Ares, or future MGS agents.

## User expectation

Rodolfo expects thread titles to behave like ChatGPT: every new thread should be renamed according to the real subject/intention of the first prompt, not merely truncated from the first words. Examples:

```text
Prompt/subject                                  Desired style
----------------------------------------------  ------------------------------
horário em Dubai e Alemanha                     Horário Dubai Alemanha
varredura na VPS para arquivos de backup         Backups na VPS
script Node criado pelo Ares                     Script Node do Ares
melhorias no sistema de saúde                    Melhorias no sistema de saúde
sistema financeiro atual                         Sistema financeiro atual
```

## Root cause pattern

The Discord gateway may have two title layers:

1. **Pre-create deterministic title** in `plugins/platforms/discord/adapter.py` (`_auto_thread_name_from_message`) used when a Discord thread is created immediately.
2. **Hermes auto-title/session title** in `agent/title_generator.py`, called from `gateway/run.py` after the first user/assistant exchange.

If only layer 1 is connected to Discord thread naming, titles look intelligent only for hardcoded rules. Unknown topics fall back to a truncated first sentence, e.g. `Ola zeus, me fale o horario que esta`.

## Correct architecture

Use a hybrid:

- Keep deterministic pre-create rules for fast/critical MGS cases.
- After the first response in a **newly auto-created thread**, let Hermes/GPT-style `maybe_auto_title(...)` generate the semantic session title.
- Add/keep a Discord `title_callback` in `gateway/run.py` that schedules a best-effort Discord thread rename, but gate it tightly.
- Do **not** solve old-thread rename bugs by removing the Discord callback entirely; that breaks the expected new-thread semantic rename.
- Preserve manual/moderator/existing-thread titles by only overwriting when all guardrails pass:
  - source is a Discord thread;
  - thread is bot-owned / auto-created by the current bot;
  - thread is recent (short post-creation window, e.g. ~30 minutes);
  - current name still equals the deterministic first-message title from `_auto_thread_name_from_message(clean_actionable_user_message)`;
  - generated title differs and is Discord-safe.
- If any guardrail fails, skip silently/log at info/debug and never mutate the thread name.

## Patch shape

In `plugins/platforms/discord/adapter.py`:

- Add `rename_thread_title(thread_id, title, message_content=None)`.
- Sanitize title to one line, trim to Discord-safe length.
- Resolve channel via `get_channel(...)` then `fetch_channel(...)`.
- Require `discord.Thread`.
- If `message_content` is provided, call `_thread_title_is_generic(current, message_content)` before editing.
- Edit with reason like `MGS GPT-style semantic thread title`.

In `gateway/run.py`:

- Add `_rename_discord_thread_for_session_title(...)` coroutine.
- Add `_schedule_discord_thread_title_rename(...)`, mirroring the existing Telegram topic auto-title callback pattern.
- In the `maybe_auto_title_kwargs` block after first exchange, pass a **clean actionable user message** to the Discord rename guard, not the whole gateway prompt/backfill:

```python
elif source.platform == Platform.DISCORD and source.chat_type == "thread":
    # `message` may include Discord history backfill/read-only context. For
    # overwrite safety, compare the current thread name against only the
    # actionable user prompt; otherwise first-message fallback titles can look
    # "manual" and GPT-style rename gets skipped.
    _discord_title_message = re.split(r"\[New message[^\]]*\]\n", message)[-1].strip()
    _discord_title_message = re.sub(r"^\[[^\]]+\]\s*", "", _discord_title_message).strip()
    maybe_auto_title_kwargs["title_callback"] = lambda title: self._schedule_discord_thread_title_rename(
        source,
        effective_session_id,
        title,
        _discord_title_message,
    )
```

## Validation

Before reporting ready:

```bash
cd /root/.hermes/hermes-agent
python3 -m py_compile plugins/platforms/discord/adapter.py gateway/run.py
```

Also test the guard behavior locally by instantiating `DiscordAdapter` without `__init__` and calling `_thread_title_is_generic(...)`:

```text
Current title fallback like "Ola zeus, me fale o horario que esta" -> generic=True
Manual/GPT title like "Horário Dubai Alemanha"                  -> generic=False
Fallback like "Faca varredura na vps e liste todos os"           -> generic=True
```

Test the enriched Discord prompt cleanup too. Regression signature: logs show a good GPT title was generated but rename skipped with `reason=non-generic current title` even though the current title is just the initial fallback. Simulate a prompt containing read-only history plus `[New message ...]` and verify the extracted message is only the actionable user text and the fallback title returns `generic=True`.

Example validated regression:

```text
Thread:       1512462156837159110
User prompt:  o que voce acha que da pra melhorar na MGS ?
Fallback:     O que voce acha que da pra melhorar
GPT title:    Melhorias Operacionais na MGS
Bad log:      GPT-style thread title skipped ... reason=non-generic current title
Fix proof:    extracted actionable prompt + fallback guard => generic=True
```

## Activation and reporting

If Rodolfo asks to prepare without restart, write the patch to disk and save a reapply patch under `/root/mgs-agent/patches/hermes/`, but do **not** restart. Report clearly:

```text
Código no disco: sim
py_compile: OK
Gateway rodando: ainda versão antiga em memória
Pendente para ativar: restart controlado dos gateways afetados
```

If he authorizes activation, restart affected gateways only after syntax validation and then test a new Discord thread in the channel.

## Pitfalls

- Do not claim the behavior is active until the gateway has restarted; Python runtime still uses code loaded in memory.
- Do not rely only on hardcoded `_auto_thread_name_from_message` rules. That repeats the original bug: only known topics look intelligent.
- Do not overwrite short, specific manual thread titles.
- Do not pass full Discord backfill/history prompts into the manual-title guard. The guard must compare against the clean actionable user message only; otherwise fallback titles derived from the first prompt can be misclassified as manual and block the correct GPT-style rename.
- When a user says “it still did not work” and provides a thread ID, verify the exact `GPT-style thread title ...` log for that thread before changing heuristics. A skip log with `generated='<good title>'` proves the LLM title worked and the bug is in the rename/guard layer.
- Do not add a cron/LLM self-check for this during the same restart unless explicitly needed; it can collide with gateway drain and confuse the active thread.
