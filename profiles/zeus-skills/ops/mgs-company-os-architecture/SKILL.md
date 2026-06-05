---
name: mgs-company-os-architecture
description: "Use when Rodolfo asks to organize, redesign, audit, or migrate the MGS company operating structure: areas, agents, sources of truth, routing, permissions, context files, scripts, skills, docs, and safe phased restructuring before adding more agents."
tags: [mgs, company-os, architecture, operations, agents, governance, sources-of-truth, migration, inventory, zeus, atena, ares]
related_skills: [discord-ops, hermes-agent-operations, log-monitor-discord-alert]
---

# MGS Company OS Architecture

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

### 3. Recommended initial MGS areas

Use the CEO-described real operating model as the starting point. The current canonical proposal is:

```text
Area                         Function
---------------------------- -------------------------------------------------
Executive / Management        Direction, strategy, priorities, daily meetings,
                              decisions, coordination and governance.
Content Operations            REC/P1, SEO support articles, categories,
                              WordPress editorial, daily content and QA.
Growth / Media Buying         Facebook Ads, Google Ads, SMS, media buyers,
                              campaign costs, acquisition and ROI.
Creative Operations           Kelly, Canva, ChatGPT, TopView.ai, Grok/other AI,
                              static/video creatives and asset handoff.
Revenue / AdOps               Smart Bidding, ActiveView, AdManager/AdX,
                              approval, ad blocks, pricing rules and AdOps.
Finance / BI                  Financial close, spreadsheets, revenue, costs,
                              invalid traffic, commissions, salaries and ROI.
Tech / WordPress / Infra      WordPress setup, plugins, pixels, VPS, Hermes,
                              agents, crons, scripts, patches and monitoring.
Security / Access             Credentials, tokens, user permissions, dashboards,
                              APIs, hardening and risk policy.
```

Durable MGS facts from the CEO explanation:
- Rodolfo and Geizian are partners. Rodolfo owns management, finance, WordPress/technical structure, pixels, partner-network relationship and strategy. Geizian manages the content/campaign managers day to day.
- Raquel owns Content Operations and should supervise Atena.
- Kelly owns creative production and currently uses AI/Canva workflows for managers.
- There are five managers operating sites/campaigns and interacting with AdOps.
- Smart Bidding is the main operational dashboard for sites, campaigns, ROI, ad blocks, APIs and permissions.
- ActiveView is now an exception/legacy-active network: only `openzed`, `cliquet`, and their subdomains are not technologically migrated to Smart Bidding.
- Finance runs monthly: period day 1–30, Google payment around day 21–23, Rodolfo checks Facebook Business Manager spend, invalid traffic, Smart Bidding/ActiveView reports, commissions, salaries and expenses in his spreadsheet.

### 4. Recommended agent map

```text
Agent   Primary area    Role
------- --------------- ------------------------------------------------------
Zeus    Executive/Ops   General Manager, governance, routing, audit, escalation
Atena   Content         Editorial production, REC/P1, WordPress, content QA
Ares    Growth/Ads      Campaigns, acquisition, tracking, ads, funnels
Future  TBD             Specialist agents created only after mission/scope exist
```

Rule: **agent creation follows company architecture**. Do not create a new agent until its area, mission, sources of truth, permissions, and escalation paths are explicit.

### 5. Sources-of-truth distinction

Keep this separation clear:

```text
context/   explains how the company works
 data/     stores operational state and facts used by systems
 scripts/  performs deterministic actions
 skills/   teaches agents procedures
 docs/     records history, plans, pendencies, changelog
 logs/     audit/runtime trail
 patches/  local runtime modifications
```

Pitfall: do not let `SOUL.md`, ad-hoc prompts, or individual skills become the only place where company structure exists. Company architecture belongs in `context/` and is then referenced by agents.

### 6. Safe migration stages

Use staged gates:

```text
Phase 1   Blueprint                     no runtime changes
Phase 2   Classified inventory           one line per relevant path
Phase 3   New canonical context files     additive only
Phase 4   Agent reference updates         controlled, validated after each agent
Phase 5   Cleanup/archival                explicit Rodolfo approval per block
```

Never combine broad reorganization with gateway restarts, cron rewrites, or production changes unless Rodolfo explicitly authorizes that combined scope.

### 7. Inventory deliverable format

After the blueprint, generate a migration inventory, usually under:

```text
/root/mgs-agent/docs/mgs-structure-inventory.md
```

Preferred columns:

```text
Path | Classe | Dono | Área | Status | Ação recomendada
```

Allowed actions:

```text
manter
não tocar
mover
renomear
consolidar
arquivar
remover depois
revisar com Rodolfo
```

Use `não tocar` for sensitive live state such as `data/sites.json`, `data/authorized-users.json`, active runners, active crons, and Hermes patches unless there is a specific approved plan.

### 8. Executive communication pattern

When reporting to Rodolfo, be direct and structured. Prefer aligned monospace tables for comparable data.

Good pattern:

```text
Parte                         Veredito
----------------------------- --------------------------------------------------
Existe estrutura?              Sim.
Está centralizada como empresa? Não.
Dá para reaproveitar?           Sim, bastante.
Precisa trocar tudo?            Não.
Precisa reorganizar?            Sim.
```

Avoid overexplaining. Give an operational opinion and the next concrete step.

## Pitfalls

- **Moving before mapping**: creates broken imports, stale references, and agent confusion.
- **Treating current structure as garbage**: many existing MGS files are production-critical and should be wrapped, not replaced.
- **Letting agent prompts be the architecture**: prompts should consume the company OS, not be the only source of it.
- **Mixing concept and runtime**: `context/` is not `data/`; `docs/` is not `scripts/`.
- **Deleting backups/experiments too early**: classify first, archive later, delete only after explicit approval.
- **Updating agents too early**: validate blueprint with Rodolfo before changing Zeus/Atena/Ares behavior.

## Verification checklist

Before reporting completion of a company-OS step:

- The deliverable exists at the declared path.
- It is clearly marked proposal/canonical as appropriate.
- No runtime file was changed unless explicitly approved.
- Sensitive sources of truth were not modified accidentally.
- Next step is concrete and low-risk.

## References

- `references/company-os-blueprint-session-2026-06-05.md` — session-specific origin: Bruno course context, current `/root/mgs-agent` structural counts, and first blueprint pattern.
- `references/company-os-ceo-operating-model-2026-06-05.md` — CEO-described real MGS operating model: partners, Raquel/Kelly/gestores, Smart Bidding/ActiveView, finance cycle, campaigns, creative flow, and agent implications.
