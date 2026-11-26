---
name: mgs-company-os-architecture
description: "Use when Rodolfo asks to organize, redesign, audit, or migrate the MGS company operating structure: areas, agents, sources of truth, routing, permissions, context files, scripts, skills, docs, and safe phased restructuring before adding more agents."
tags: [mgs, company-os, architecture, operations, agents, governance, sources-of-truth, migration, inventory, zeus, atena, ares]
related_skills: [discord-ops, hermes-agent-operations, log-monitor-discord-alert]
---

# MGS Company OS Architecture

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Audit execution and reporting

- Resolve the requested asset boundary before searching: distinguish ad accounts, operational domains, app ownership and credentials. Removing an asset from an agent's remit does not implicitly authorize revoking a shared app or deleting unrelated evidence.
- For a whole-agent audit, load `references/shared-domain-scope-guardrails.md` and freeze a machine-readable coverage manifest before reporting. Keep documented scope, actual credential reach and operating-system isolation as separate findings.
- Report to Rodolfo with the verdict first, followed by numbered **Problema / Causa / Solução** items. Label unproved causes, give verified coverage and exclusions, and distinguish completed audit from unapplied remediation. Ask only for the exact critical transition that remains blocked, not a blanket approval for loosely specified cleanup and credential changes.

## Institutional closure gate

- Validate the canonical knowledge store early when the task will need a checkpoint transition. A malformed record elsewhere can block the shared writer even when the task's own record is valid.
- Make each required closure operation a checked dependency of the next. A later successful shell command must not mask a failed checkpoint update; read back the exact target record before writing an overall success receipt.
- Keep external-operation success separate from institutional closure. If metadata repair is needed, preserve the deployed operation and its receipts, repair only the authorized metadata defect, then retry the canonical writer and complete reporting. Do not rerun a committed operation to repair its bookkeeping.
- Follow the schema-recovery and synchronization checks in `references/institutional-knowledge-continuity.md` before declaring the work fully closed.

## Operational route packs

- **When to use → 2. Create a blueprint before operational changes** → `references/route-pack-01.md`
- **3. Recommended initial MGS areas → 5. Sources-of-truth distinction** → `references/route-pack-02.md`
- **6. Safe migration stages** → `references/route-pack-03.md`
- **7. Inventory deliverable format → Pitfalls** → `references/route-pack-04.md`

- **Pós-cutover de agente unificado: validar thread real, permissões por módulo, naming legado, Drive/inventário e dívida documental** → `references/agent-consolidation-post-cutover-audit.md`
- **Memória institucional, continuidade entre sessões/agentes, registro de decisões, checkpoints e recuperação sem depender de USER/MEMORY** → `references/institutional-knowledge-continuity.md`
- **Guardrails de confidencialidade por allowlist para domínios/ativos compartilháveis entre agentes** → `references/shared-domain-scope-guardrails.md`
- **Referências operacionais → Verification Checklist** → `references/route-pack-05.md`
- **References** → `references/route-pack-06.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
