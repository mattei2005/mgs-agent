# Discord auto-thread title diagnostics

Use when Rodolfo asks why a Discord thread was not renamed, or why the title looks generic/truncated.

## Key distinction

Discord thread title creation is gateway-side and deterministic in the MGS patch:

- `_auto_create_thread(...)` creates the Discord thread immediately from the incoming message.
- `_auto_thread_name_from_message(content)` chooses the Discord title before the agent response exists.
- Later `Auxiliary title_generation` log entries usually refer to the internal Hermes session title; they do **not** prove the Discord thread was renamed.

So a thread can be "renamed" by the gateway but still look bad because it fell through to the fallback first-N-words title.

## Read-only diagnosis checklist

1. Fetch the thread object via Discord API and inspect `name`, `parent_id`, `owner_id`, `thread_metadata.create_timestamp`.
2. Check `agent.log` around creation for:
   - `Auto-thread member sync` (thread was created and member sync ran)
   - `Auto-thread title selected` if present in that runtime/log version
   - first `inbound message` for the thread
   - later `Auxiliary title_generation` lines; treat these as internal session title, not Discord rename
3. Inspect active gateway code for `_auto_thread_name_from_message(...)` and confirm whether the first message matches a semantic rule or fell through to `clean_title(text)`.
4. Report separately:
   - current Discord title
   - expected semantic title
   - first message content
   - whether the auto-title rule existed
   - whether member sync/creation succeeded

## Common outcome

If the first message is something like “último push no github foi há 4 dias...” and there is no `github + push/autopush/update` rule, the fallback title becomes a cleaned/truncated first phrase such as `Ultimo push no github foi a ha 4`. That is not a Discord permission failure; it is a missing semantic rule or missing post-response rename path.

## Fix pattern

- Add or broaden a class-level rule in `_auto_thread_name_from_message(...)` for the semantic family, e.g. `github` + `push/autopush/auto-push/atualização` → `GitHub auto-push`.
- For better coverage, implement a post-response `PATCH /channels/{thread_id}` rename when the initial title is generic. Keep it idempotent and avoid repeated renames if the user/moderator manually changed the title.
- Validate with `py_compile`, then restart the affected gateway only with authorization when service restart is required.
