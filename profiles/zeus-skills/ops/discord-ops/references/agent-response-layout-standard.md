# MGS agent response layout standard

Session learning: Rodolfo corrected the agents' Discord response layout preference. The desired behavior is a visual layout pattern, not a fixed schema.

## Rule

When an agent response contains structured or comparable information, use a context-specific aligned table in a monospaced `text` block.

Examples of structured/comparable information:
- status rows
- pending tasks
- site lists
- campaign metrics
- validation results
- user/access lists
- errors grouped by source
- multi-step execution summaries

## Important distinction

Do not copy column names from examples. Headers must be chosen from the current thread/topic.

Wrong interpretation:
- Always use `Campanha | Estado | Custo | Conv | CPS | CTR | Status`
- Always use `ID | Área | Tarefa | Bloqueio`

Correct interpretation:
- Use the same visual style: aligned columns, separators, easy scanning.
- Choose columns that fit the current subject.

## Preferred Discord shape

```text
[Short title]

[Optional 1-3 line summary]

Context field       | Context field       | Context field
--------------------|---------------------|----------------
real value          | real value          | real value
real value          | real value          | real value
```

## Practical rules

- Use this when there are 3+ comparable rows or when a response has multiple parallel fields.
- Keep prose short; let the table carry the structured data.
- Use `text` code blocks when Discord Markdown tables render cramped or visually weak.
- Truncate long values with `...` to preserve alignment.
- Do not wrap mentions that need to ping users inside code blocks.
- If an internal Hermes/tool warning appears in the UI (for example "File-mutation verifier" or patch validation noise), do **not** assume Rodolfo understands it. Translate it into operational meaning immediately: what happened, whether it affected the result, what you verified afterward, and current state. Avoid repeating the raw warning unless needed as evidence.

## Post-update / regression audit checklist

When Rodolfo notices raw Markdown tables after a Hermes update, do not assume the Hermes renderer changed. First distinguish:

```text
Layer                     | What to verify
--------------------------|-----------------------------------------------------
Runtime renderer           | Discord adapter usually sends Markdown as-is
Profile prompt/SOUL        | Each active agent has the aligned `text` table rule
Agent behavior             | The agent may have ignored an existing rule
Config sync                | Active profile and `/root/mgs-agent/profiles/*` match
New agents                 | Check newer profiles too; they may lack old style rules
```

Audit all active MGS agents (Zeus, Atena, Ares, agente legado, future agents) for the style rule, not only the agent that made the bad response. In the 2026-06-07 post-update audit, Zeus/Atena/Ares had the rule but agente legado did not; the correct fix was adding the rule to agente legado's SOUL and syncing/versioning it, not changing Hermes runtime.

## Files updated in the originating session

- `/root/mgs-agent/AGENT.md` — MGS-wide master rule.
- `/root/.hermes/profiles/zeus/SOUL.md` — Zeus active profile rule.
- `/root/.hermes/profiles/atena/SOUL.md` — Atena active profile rule.
- Synced copies: `/root/mgs-agent/profiles/zeus-soul.md`, `/root/mgs-agent/profiles/atena-soul.md`.

Use this reference when editing future agents' SOUL.md or writing profile style guidance.