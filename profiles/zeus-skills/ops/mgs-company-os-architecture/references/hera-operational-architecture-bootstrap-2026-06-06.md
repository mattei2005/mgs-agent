# Hera Operational Architecture Bootstrap — 2026-06-06

Session-specific reference for sequencing Hera after the technical Discord gateway came online.

## Lesson

Do not treat “gateway online” as “agent ready for production.” For a new MGS specialist agent, the correct next step is an operational architecture layer before real work requests.

Rodolfo corrected the sequence when Zeus suggested a real creative test too early. The right order is:

```text
1. Technical bootstrap: profile, SOUL, config, auth, Discord bot, service, live test.
2. Operational context/diagram: dedicated `context/<agent>.md` defining mission, routes, actors, states, handoffs and limits.
3. Align SOUL.md to that operational document.
4. Create class-level skills and templates for the agent's work class.
5. Run 2–3 controlled tests with Rodolfo.
6. Only then add human users such as Kelly/Geizian/gestores.
```

## Hera-specific operational document

Initial document created:

```text
/root/mgs-agent/context/hera-creative-agent.md
```

When Rodolfo asks to review this kind of file, send `MEDIA:/root/mgs-agent/context/hera-creative-agent.md` or the relevant absolute path as an attachment. Do not paste long SOUL/context/skill markdown into Discord unless he explicitly asks for inline content.

Key sections that should exist in similar future agent docs:

```text
Objective
Mission
What the agent does / does not do
People and agents involved
Operational diagram
Request states
Minimum intake fields
Default delivery format
Asset/naming pattern
Source-of-truth / Drive or system rules
Integration with upstream/downstream agents
Escalation rules
Required follow-up artifacts
Pending Rodolfo decisions
Phased rollout plan
```

## Hera class boundaries

```text
Hera creates/organizes creative assets and handoffs.
Ares uses approved creatives in campaigns.
Atena provides editorial/content context when needed.
Zeus governs access, audit, escalation and inter-agent conflict.
Rodolfo approves scope, exceptions and rollout.
```

## Implementation notes from Hera

For the first Hera class-level skill, create only the custom operational skill and templates, then sync/version that exact subtree rather than the entire bundled `creative/` category:

```text
/root/.hermes/profiles/hera/skills/creative/creative-brief-handoff/
/root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/
```

Validation pattern:

```text
- validate SKILL.md frontmatter and template files
- run the selective SOUL/skill sync
- restart the agent gateway so `/skill` autocomplete reloads
- verify logs show Discord connected and expected skill registration count
- record an audit event
```

## Pitfall

A “smoke test” that asks the new agent to perform its domain work can be premature if SOUL/templates/skills/operational docs are not aligned. Prefer an architecture/diagram pass first, then a controlled work test.
