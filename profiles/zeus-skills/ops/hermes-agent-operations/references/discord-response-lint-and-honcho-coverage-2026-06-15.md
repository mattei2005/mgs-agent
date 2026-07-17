# Discord response lint + Honcho coverage audit — 2026-06-15

## Trigger

Rodolfo reported repeated broken Discord formatting where replies contained many small fenced blocks and standalone `text` labels rendered in the chat. He explicitly asked for a mechanism to prevent recurrence.

## Durable lesson

For MGS Discord operational reports, language-tagged fences such as ` ```text`, ` ```bash`, or ` ```json` can render poorly or leak the language label as a standalone line. Multiple small code blocks amplify the problem and make executive reports hard to read.

Preferred pattern:

- Use short sections and bullets.
- Avoid language-tagged code fences in final Discord replies.
- If monospace is truly needed, use at most one plain fence with no language tag.
- Do not use raw Markdown pipe tables for Discord reports; use bullets or aligned text.
- For long/drafted reports, run a local lint before sending when practical.

## Mechanism created

Runtime helper:

- `/root/mgs-agent/scripts/discord-response-lint.py`

Capabilities:

- detects language-tagged fences;
- detects standalone `text` lines;
- detects too many fenced blocks;
- detects raw Markdown pipe tables;
- offers `--fix` to remove language tags and standalone `text` lines.

Validation pattern:

```bash
python3 -m py_compile /root/mgs-agent/scripts/discord-response-lint.py
python3 /root/mgs-agent/scripts/discord-response-lint.py --check < draft.md
python3 /root/mgs-agent/scripts/discord-response-lint.py --fix < draft.md > fixed.md
```

## SOUL alignment applied

Zeus live + versioned SOUL gained a rule named `REGRA — Saída Discord sem blocos quebrados` telling Zeus not to use language-tagged fences or many small blocks in Discord reports.

Files patched in that session:

- `/root/.hermes/profiles/zeus/SOUL.md`
- `/root/mgs-agent/profiles/zeus-soul.md`

Future agent work: if the same formatting drift appears in Atena/Ares/agente legado outputs, apply the same class-level rule to those agents' SOULs as well, with backup + live/versioned sync.

## Honcho coverage audit result from same session

Config state observed:

- 2026-06-21 repair: wrapper now supports Zeus/Atena/Ares/agente legado in `AGENT_PROFILES`; cold-storage responses are classified as `status=cold_storage` with manual resume action. Validate with `/root/mgs-agent/scripts/mgs-memory-copilot --agent legacy-agent --json ...` before relying on agente legado coverage.

Conclusion: Honcho is operationally configured as a copiloto/conselheiro for Zeus/Atena/Ares, but not fully for agente legado. Even where configured, it remains hypothesis/context only, not a source of truth, authorizer, executor, publisher, or final decision layer.

## Reminder pattern

When asked to revisit Honcho later, schedule a one-shot cron with a self-contained prompt that restates the current status and asks Rodolfo whether to open a controlled review of:

1. coverage by agent;
2. security/sanitization;
3. canonical sources vs. Honcho;
4. allowed response weight;
5. gradual rollout plan.
