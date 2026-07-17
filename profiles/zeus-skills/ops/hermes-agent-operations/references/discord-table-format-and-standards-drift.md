# Discord table format + post-update standards drift

Session lesson: after a Hermes update/config migration, Rodolfo noticed a response using raw Markdown table syntax (`|---|---|`) in Discord and asked why it was no longer appearing as the expected visual table.

## Durable rule

For MGS Discord operations, structured/comparable information should be rendered as a monospaced `text` block with aligned columns, not as raw Markdown table syntax.

Correct pattern:

```text
Item       Estado      Observação
---------  ----------  --------------------------------
Provider   OK          openai-codex
Modelo     OK          gpt-5.5
Gateway    OK          active
```

Avoid for operational Discord replies:

```markdown
| Item | Estado | Observação |
|---|---|---|
| Provider | OK | openai-codex |
```

## Why this matters

- Discord clients do not reliably render GitHub-style Markdown tables as a visual table.
- Hermes display settings such as `display.final_response_markdown: strip` are not a reliable fix for Discord table legibility; the Discord adapter sends message content largely as-is.
- Style corrections from Rodolfo are operational standards, not cosmetic preferences. Patch the relevant SOUL/skill so the next session starts with the right format.

## Workflow when format drift is reported

1. Inspect whether the relevant profile SOUL already contains the desired response-format rule.
2. If the rule is permissive (for example, "prefer text block when Markdown looks bad"), make it explicit: Discord operational tables must use `text` blocks.
3. Apply the same class-level wording across active MGS agent SOULs when the rule is MGS-wide.
4. Do not restart gateways solely for SOUL wording changes unless there is a separate reason; new sessions pick it up naturally, and the current session can follow it immediately.
5. If config migration is also in scope, treat it separately: backup, migrate, validate, then optionally restart gracefully.

## Related validation from the session

- `display.final_response_markdown` was `strip` across Zeus/Atena/Ares/agente legado, but the practical issue was the agent choosing Markdown table syntax.
- The fix was to strengthen SOUL wording and then continue using aligned `text` tables.
