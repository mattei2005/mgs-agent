# Discord thread titles — one AI rename after first reply

## Context

MGS wants Discord thread titles to behave like ChatGPT/Telegram topics:

1. Discord creates a new thread immediately with a provisional deterministic title from `plugins/platforms/discord/adapter.py::_auto_thread_name_from_message(...)`.
2. After the first assistant response, Hermes `agent/title_generator.py::maybe_auto_title(...)` generates a better AI title using the main runtime model.
3. Discord should apply that AI title exactly once, only for a newly auto-created thread.
4. Follow-ups in old threads, idle/reset-created Hermes sessions, bot-external threads, and manually renamed threads must not be renamed.

## Correct architecture

Do **not** remove or weaken `_auto_thread_name_from_message(...)`; Discord needs a title before the LLM response exists.

Do **not** change the Telegram path; it is the model/reference implementation.

Reconnect Discord to the existing title callback path in `gateway/run.py` near the post-response auto-title block:

```python
if self._is_telegram_topic_lane(source):
    maybe_auto_title_kwargs["title_callback"] = lambda title: self._schedule_telegram_topic_title_rename(
        source,
        effective_session_id,
        title,
    )
elif self._is_discord_thread_lane(source):
    _discord_title_message = re.split(r"\[New message[^\]]*\]\n", message)[-1].strip()
    _discord_title_message = re.sub(r"^\[[^\]]+\]\s*", "", _discord_title_message).strip()
    maybe_auto_title_kwargs["title_callback"] = lambda title: self._schedule_discord_thread_title_rename(
        source,
        effective_session_id,
        title,
        _discord_title_message,
    )
```

The safety guard should live in the actual rename path, because `maybe_auto_title(...)` runs in a background thread and the callback schedules async work.

## Required guard: `_discord_thread_safe_to_autorename(...)`

Return `True` only when all are true:

1. Source is a Discord thread lane (`_is_discord_thread_lane(source)`).
2. Adapter/client/thread are available and editable.
3. Optional but recommended: thread owner is the current bot, when `owner_id` is available.
4. Thread is new enough, e.g. `channel.created_at <= 1800s`. This blocks old-thread follow-up/session-reset renames.
5. Current Discord thread name still equals the provisional title generated from the actionable first user message:
   - Extract the actionable message from the gateway `message` by removing `[READ-ONLY ...]` context and `[New message...]` wrapper.
   - Recompute `adapter._auto_thread_name_from_message(message_content)`.
   - Sanitize with `_sanitize_discord_thread_title(...)`.
   - Compare to current thread name.
6. If current name differs, skip. This preserves manual titles and prevents a second AI rename after the first successful one.

## Implementation notes

- Extend `_schedule_discord_thread_title_rename(..., message_content="")` and `_rename_discord_thread_for_session_title(..., message_content="")` instead of rewriting them from scratch.
- `_rename_discord_thread_for_session_title(...)` should call `await _discord_thread_safe_to_autorename(...)` immediately before fetching/editing the title.
- Keep logs explicit for skipped reasons: `not_new`, `non_initial_title`, `not_bot_owned`, `missing_initial_title_check`.
- Update the MGS comment in `run.py` from “never rename once thread exists” to “provisional regex title at creation, one guarded AI rename after first reply.”

## Validation plan after approval

1. Apply patch to `gateway/run.py` only.
2. `python3 -m py_compile /root/.hermes/hermes-agent/gateway/run.py`.
3. Save a reapply patch under `/root/mgs-agent/patches/hermes/`.
4. Restart only the approved gateway(s).
5. Create a new test thread in Discord and confirm:
   - initial title is provisional regex title;
   - after first answer, log shows one `Discord thread renamed...` and thread title changes.
6. Send a follow-up in the same thread; confirm no second rename and a skip reason if the callback fires.
7. Test or inspect an old thread; confirm `not_new` or `non_initial_title` prevents rename.

## Pitfall

A previous defensive patch fully disconnected Discord from `maybe_auto_title(...)`. That avoided old-thread renames but also killed the desired first-response AI title. The correct fix is not “Discord never renames”; it is “Discord renames exactly once, guarded by age + provisional-title match.”
