# Shared Discord agent thread loop cleanup

Use this reference after a Zeus/Atena or multi-agent Discord thread starts looping, especially when the loop caused rushed skill/memory edits.

## Failure pattern

A shared thread with Rodolfo plus multiple bots can create a conversational feedback loop when agents treat each other's acknowledgements as new work:

```text
Atena: recebido / read-only mantido
Zeus: estado confirmado
Atena: sem nova ação
Zeus: read-only mantido
...
```

Gateway/model noise can amplify it:

```text
queued
(empty)
The model returned no response after processing tool results
```

## Immediate containment

1. Stop bot mentions in that thread unless Rodolfo explicitly asks for a handoff.
2. Reply to Rodolfo once at most; then silence for bot/gateway noise.
3. If Rodolfo asks to stop the whole thread, lock/archive it via Discord API.
4. If Rodolfo asks to stop a specific bot in the thread, remove that bot from the thread.
5. If Rodolfo asks to delete the thread, double-confirm because deletion is destructive; then verify Discord API returns 404.

## Cleanup after the incident

Audit and undo loop-induced rules before they poison future conversations:

1. Search recent changes in both agents' SOUL, skills, and memories for broad rules like:
   - always mention Zeus/Atena in shared threads;
   - speak directly to/about another bot using a mention by default;
   - keep acknowledging read-only/queued/no-op state.
2. Delete narrow one-session skills created during the loop unless they are the canonical umbrella.
3. Consolidate durable behavior into one class-level skill:
   - Zeus: `discord-ops`.
   - Atena: one Discord/thread communication umbrella, not multiple overlapping skills.
4. Replace dangerous mention defaults with this policy:
   - shared thread: plain text names by default;
   - bot mention only if Rodolfo explicitly asks for handoff/notification;
   - cross-channel bot-to-bot routing may require mention if `DISCORD_ALLOW_BOTS=mentions`.
5. Remove memory entries that encode broad bot-mention requirements.
6. Keep one concise incident reference; do not preserve multiple narrow session artifacts.
7. Register the cleanup in audit log with paths changed and backup path.

## Correct durable policy

```text
Situation                                      | Correct behavior
----------------------------------------------|---------------------------------------------
Rodolfo asks a question                        | Reply to Rodolfo
Other bot says queued/read-only/received       | Silence
Other bot emits (empty)/model warning          | Silence
Need to cite another bot                       | Plain text name
Need to wake/route to another bot              | Mention only if explicit or cross-channel required
Rodolfo says stop/looping                      | One short ack max, then silence
```
