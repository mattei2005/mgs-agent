# Agent HOT Operational Maps — Ares/agente legado rollout 2026-06-16

## Trigger

Rodolfo identified that agents were wasting time with broad `search_files` calls such as `search_files: "drive"` in operational threads, especially agente legado/Ares creative and Drive workflows. He asked Zeus to create the same map pattern used by Zeus for other agents, excluding Atena while Atena is being restructured.

## Class-level pattern

For agents with mature enough scope, create a compact HOT map under `context/` that routes common natural-language asks to the first canonical source before any broad search.

Recommended file names:

```text
/root/mgs-agent/context/<agent>-operational-map.md
```

Examples created:

```text
/root/mgs-agent/context/ares-operational-map.md
/root/mgs-agent/context/legacy-agent-operational-map.md
```

Each map should include:

1. Status, owner, agent, function.
2. Rule: open this map before broad `search_files` for generic terms.
3. Principal sources by topic.
4. “Pedido/pergunta → primeira fonte” table.
5. Runtime/script/data paths for that agent.
6. Handoff rules to other agents.
7. Boundaries and escalation.
8. Validation checklist before reporting success.

## Rollout sequence

1. Read the existing MGS OS map first: `/root/mgs-agent/context/mgs-os-map.md`.
2. Inspect the agent’s versioned SOUL and class-level skills.
3. Create/update `context/<agent>-operational-map.md`.
4. Patch `context/mgs-os-map.md` to list the new maps under quick sources and agent sections.
5. Patch both live and versioned SOUL files with a short HOT pointer:
   - `/root/.hermes/profiles/<agent>/SOUL.md`
   - `/root/mgs-agent/profiles/<agent>-soul.md`
6. Keep live/versioned SOUL identical with `cmp`.
7. Validate with `git diff --check`, a secret scan over added lines, audit log append, gateway restart if SOUL changed, systemd active check, and auto-push/`HEAD == origin/main`.

## Scope caution

Do not automatically roll this out to an agent that is under active reconstruction or whose operating model is not stable. In this session Atena was explicitly excluded because Rodolfo was restructuring it.

## Communication pattern

Report concisely:

- maps created;
- SOULs patched live/versioned;
- agents excluded and why;
- validation evidence: cmp, diff check, secret scan, restart status, audit event, git/auto-push.

Avoid long explanations of every file unless Rodolfo asks for file review.
