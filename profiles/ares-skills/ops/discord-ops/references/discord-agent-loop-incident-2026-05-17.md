# Discord agent confirmation-loop incident — 2026-05-17

## Context

Rodolfo placed Zeus and Atena in the same Discord thread (`1505532189490811081`) while discussing REC pipeline speed. He set a thread-scoped safety gate: because both agents were present, any execution, mutation, or persistence required explicit authorization.

A second rule was introduced during the thread: when one agent speaks directly to/about the other agent, use the other agent's Discord user mention rather than only writing the name.

## What failed

The mention rule was dangerous when treated as a default in a shared thread. User mentions woke the other bot. Each bot then treated the other bot's acknowledgement/status/no-op as a new input that deserved another acknowledgement. The corrected policy is: do not use bot mentions just to talk about another agent; use them only when Rodolfo explicitly asks for a handoff/notification, or for cross-channel routing where `DISCORD_ALLOW_BOTS=mentions` requires it.

Observed loop pattern:

```text
Atena: recebido / read-only mantido
Zeus: read-only confirmado
Atena: estado mantido
Zeus: sem nova ação
Atena: sem nova ação
Zeus: read-only mantido
...
```

The loop was amplified by Discord/Hermes gateway status messages:

```text
Queued for the next turn
(empty)
The model returned no response after processing tool results
```

Those automatic messages were treated as conversation turns instead of non-operational noise.

## Root cause

This was not a content pipeline loop and not WordPress automation. It was a conversational coupling loop:

1. Agent mentions woke the other agent.
2. Queue/status messages created more visible inputs.
3. Both agents over-optimized for acknowledgement.
4. Neither agent enforced silence after the state was already closed.
5. Zeus continued correcting/summarizing mention behavior after Rodolfo said to stop mentions, which prolonged the loop.

## Correct behavior

When a human says agents are looping, says "parem de falar", or asks one/both agents to stop responding:

1. Acknowledge the human once at most.
2. Stop mentioning the other agent immediately.
3. Do not reply to the other agent's queued/read-only/received/no-action confirmations.
4. Do not reply to `(empty)` or model/gateway warning messages.
5. Do not post bracketed placeholders like `[ignorado]`, `[sem resposta operacional]`, `Ignorado`, or `Sem ação` — these are still messages and can feed the loop.
6. Resume only for a new direct human request, explicit authorization, or a real critical alert.

## Emergency containment used

If a shared-agent thread is already looping and the user explicitly asks to stop it:

1. Lock/archive the thread via Discord API if asked to stop the whole thread.
2. Remove the other bot from the thread if asked to stop that agent specifically.
3. Delete the thread only after explicit destructive confirmation.
4. Verify deletion with Discord API returning 404.
5. Remove local imported snapshots for that thread ID if they exist.
6. Keep only a minimal audit-log record of the destructive action.

## Skill-library lesson

This belongs under the class-level Discord operations skill, not as multiple narrow one-off skills. Session-specific references can preserve incident detail, but the operational rule in `SKILL.md` should stay short and decisive: in loop conditions, silence beats acknowledgement.
