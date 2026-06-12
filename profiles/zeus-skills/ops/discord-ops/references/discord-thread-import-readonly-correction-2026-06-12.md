# Discord thread import — read-only correction (2026-06-12)

## Trigger

Rodolfo asked Zeus to read a specific Discord thread by ID (`1512539907468558477`). Zeus initially answered incorrectly that it could not read a thread by ID. Rodolfo corrected this because Zeus already had a read-only thread import workflow.

## Correct behavior

When Rodolfo provides a Discord thread/channel ID or link and asks whether Zeus can read it, do **not** answer from memory or say the bot cannot read history. Immediately run the canonical importer in read-only mode:

```bash
cd /root/mgs-agent
scripts/import-discord-thread.py --profile zeus --limit 1000 '<THREAD_ID_OR_LINK>'
```

Then read/analyze the generated snapshot:

```text
/root/mgs-agent/data/discord-thread-imports/<thread_id>.md
/root/mgs-agent/data/discord-thread-imports/<thread_id>.json
```

Use `--profile atena` only when the requested thread is private/agent-specific and Atena's bot token is the correct access path.

## Reporting pattern

Report the operational truth precisely:

```text
Thread importada     <id>
Mensagens lidas      <n>
Período              <first timestamp> → <last timestamp>
Snapshot             /root/mgs-agent/data/discord-thread-imports/<id>.md
Modo                 read-only; não postei nem alterei a thread
```

Then summarize the thread and identify the actual continuation point.

## Pitfall to avoid

Do not conflate these two facts:

- True: Zeus does not automatically receive the full old Discord history in active context.
- False: Zeus cannot read an old thread by ID/link.

The correct statement is: Zeus can import a specific accessible thread/channel by ID/link via Discord API/script in read-only mode.

## Follow-up if the conversation is large

If `--limit 200` may miss earlier messages, re-import with a higher limit (`--limit 1000`) before summarizing or deciding where the thread stopped.

## Persistence

If the thread produced an operational summary or correction, update the relevant summary doc/reference and record an audit event. Keep imported snapshots local-only under `data/discord-thread-imports/`; do not version raw Discord history.
