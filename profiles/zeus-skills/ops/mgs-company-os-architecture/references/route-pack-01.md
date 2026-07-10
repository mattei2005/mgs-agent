## When to use

Use this skill when Rodolfo asks about:

- Structuring the MGS as a company before creating or expanding agents.
- Reorganizing `/root/mgs-agent` outside individual agent profiles.
- Defining official areas, routes, permissions, sources of truth, and agent responsibilities.
- Turning ad-hoc scripts/docs/skills/data into a coherent operating system.
- Deciding whether files should be kept, moved, renamed, archived, consolidated, or left untouched.
- Comparing the current MGS structure with external agent/company architecture training or examples.

## Core principle

Do **not** start by moving or renaming files. Start with a blueprint and a read-only inventory.

The MGS already has real production state: sites, permissions, content pipelines, WordPress tooling, crons, logs, Hermes patches, and agent profiles. Reorganization must be incremental and reversible.

Preferred framing:

```text
We are not rebuilding from zero.
We are adding a company operating layer above the current operational foundation,
then migrating safely in small approved blocks.
```

## Canonical sequence

### 1. Read-only current-state inventory

Inspect `/root/mgs-agent` while excluding agent-specific profile content unless Rodolfo explicitly asks for it.

Default exclusions:

```text
/root/.hermes/profiles/zeus/
/root/.hermes/profiles/atena/
/root/.hermes/profiles/ares/
/root/mgs-agent/profiles/
logs/runtime-heavy files unless needed
```

Classify the structural base by top-level function:

```text
context/      conceptual company knowledge
 data/        operational data, state, inventories
 docs/        documentation, pendencies, changelog, crons
 scripts/     automations, monitors, runners, importers
 skills/      reusable procedures for agents
 patches/     local Hermes/MGS patches
 backups/     safety copies and old pre-change states
 experiments/ spikes/proofs of concept
 tools/       auxiliary tooling
 api/         internal APIs
```

### 2. Create a blueprint before operational changes

The first deliverable should usually be:

```text
/root/mgs-agent/context/company-os.md
```

For ongoing operation, also maintain a lightweight navigation map:

```text
/root/mgs-agent/context/mgs-os-map.md
```

Purpose of `mgs-os-map.md`: a map-of-maps for Zeus to choose the right source before broad searching. It should map question classes to canonical files/folders/agents (e.g. “Atena fez X?” → Atena logs + article tracker + WP; “permissão real?” → `data/authorized-users.json`; “cron ativo?” → `docs/CRONS.md` + crontab real). Keep the full map in `context/`, not embedded wholesale in SOUL. SOUL should carry only a compact pointer/rule: consult `context/mgs-os-map.md` before `search_files` for structure-related questions.

Mark it clearly as a **proposal** until Rodolfo approves it as canonical.

Minimum sections:

```text
1. Objective
2. Operating principles
3. Official MGS areas
4. Agent map
5. Current sources of truth
6. Target sources of truth
7. Operational routes
8. Permissions matrix
9. File classification taxonomy
10. Safe migration plan
11. Decisions pending Rodolfo
12. Next step after approval
```

After the blueprint is in place, keep the derived docs aligned rather than letting each drift:

```text
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

If Rodolfo answers “ok” after a recommendation or execution report for a low-risk additive Company OS step, treat it as approval/continuation for that same phase/block context. If the message is a reply, anchor interpretation to the quoted message and previous execution report before acting. Still do not move/remove runtime files or alter agents without explicit scope/approval.

Discord thread discipline for Company OS work: do not rename an already-open restructuring thread while it keeps the same objective. Short messages like `Ok`, `vamos continuar`, or `prossegue` never trigger a thread rename and should inherit the current Company OS sequence until Rodolfo explicitly finalizes or changes objective. If a title ever truly needs to be created/changed because of a clear durable topic change, keep it in the dominant language of the workstream/user message — normally PT-BR for Rodolfo's MGS OS threads. Never translate an active PT-BR restructuring thread title into Spanish/English because of a generic title heuristic.

