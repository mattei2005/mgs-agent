# Discord attachments + AI thread title rename guardrails — 2026-06-13

## 1. File delivery pitfall: `MEDIA:` path shown as text

Observed in Zeus Discord thread `1515200717961560195`: replying with a bare final-response line like:

```text
MEDIA:/root/.hermes/hermes-agent/agent/title_generator.py
```

rendered as literal text in Discord instead of a native attachment. Rodolfo explicitly corrected the workflow: when he asks to "manda/envia/anexa um arquivo", the file must appear as a Discord attachment, not as a path.

### Required handling

- Treat natural-language file requests as a request for a **native Discord attachment**.
- Prefer sending via the platform delivery path/tool that actually uploads the file; do not assume a final-response `MEDIA:` line will attach.
- If the original extension is awkward or the file is source code, create a safe copy such as `/tmp/.../name.py.txt` and/or a `.tar.gz` containing the original file, then attach those.
- If a send returns success but the user says it did not attach, verify the target/thread and retry with the exact listed target, not a guessed channel/thread id.
- Do not keep explaining; apologize once and re-send the file correctly.

## 2. Discord AI thread-title rename: avoid recomputing provisional title from gateway-mutated text

Rodolfo reviewed the proposed fix for Discord thread title renaming. The original idea of recomputing `_auto_thread_name_from_message()` in `run.py` from the gateway `message` string is unsafe.

### Evidence from code

`adapter.py` creates the provisional title from raw/normalized Discord message content:

```text
adapter.py:_auto_create_thread
content = (message.content or "").strip()
thread_name = self._auto_thread_name_from_message(content)
```

But `run.py` receives a later normalized `message_text` that may be mutated:

- Shared multi-user prefix: `[Rodolfo Mattei] ...`
- History backfill wrapper:
  ```text
  [READ-ONLY RECENT CHANNEL CONTEXT — NON-ACTIONABLE]
  ...

  [New message — ACTIONABLE USER REQUEST]
  [Rodolfo Mattei] actual message
  ```
- Older history may contain `[New message]` instead of the newer marker.
- Media/document enrichment, STT, context-reference preprocessing, and batching may also change text.

Therefore byte-for-byte equivalence between `adapter.py` content and `run.py` message is not guaranteed. Recomputing the provisional title can make `current_name != expected_initial` forever and turn the patch into a silent no-op.

### Safer design

- In `adapter.py:_auto_create_thread`, immediately after creating the thread, persist in memory the exact provisional title actually used:
  ```python
  self._auto_thread_initial_titles[str(thread.id)] = thread_name
  ```
- In `run.py` safety guard, compare Discord `current_name` against that saved value, not against a recomputation.
- If the saved value is missing (gateway restart, human-created thread, old thread), fail closed and do not rename.
- Keep other guards:
  - `maybe_auto_title()` user-message count gate (`user_msg_count > 2` skips).
  - `auto_title_session()` skips sessions that already have a title.
  - Discord thread `created_at` age window, e.g. 1800 seconds.
  - Bot ownership check and manual rename check.
- For the text passed to `title_generator.py`, strip channel-context scaffolding and sender prefix so the title model sees the actual user request, not gateway metadata.

### Test plan after applying

1. `python3 -m py_compile` on modified files.
2. Save a reappliable patch under `/root/mgs-agent/patches/hermes/`.
3. Restart only approved gateways.
4. Create a new Discord thread: verify provisional regex title first, then one AI rename after first response.
5. Send follow-up in same thread: verify no second rename and log shows skip (`non_initial_title`, `not_new`, or missing provisional record as appropriate).
6. Test a manually renamed thread: verify no overwrite.
