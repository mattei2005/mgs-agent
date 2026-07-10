---
name: hermes-agent-operations
description: "Umbrella operacional para Hermes Agent no VPS MGS: updates seguros, inspeção/configuração de web tooling, providers/modelos OAuth, políticas de custo, validação de gateways Zeus/Atena e cuidados pós-migração."
tags: [hermes, operations, update, providers, oauth, web-search, web-extract, gateway, zeus, atena, mgs, memory, honcho]
related_skills: [discord-ops, log-monitor-discord-alert]
---

# Hermes Agent Operations — MGS Umbrella

Use esta skill para qualquer operação envolvendo Hermes Agent no VPS MGS: update, rollback, configuração, providers/modelos, OAuth, web tooling, gateway Discord, health-checks, migração de runtime e troubleshooting operacional.

Referência rápida adicionada: `references/hermes-staged-update-validation-mgs.md` cobre o workflow MGS de update/restart em fases: pré-check read-only, backup, preservação/compatibilidade de patches locais, validação de gateways/crons/testes e relatório executivo com ressalvas.

## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Postura operacional** → `references/router-01-postura-operacional.md`
- **Ambiente MGS conhecido** → `references/router-02-ambiente-mgs-conhecido.md`
- **1. Update seguro do Hermes** → `references/router-03-1-update-seguro-do-hermes.md`
- **2. Web tooling nativo, search/extract e MCP** → `references/router-04-2-web-tooling-nativo-search-extract-e-mcp.md`
- **3. Providers, modelos e OpenAI Codex OAuth** → `references/router-05-3-providers-modelos-e-openai-codex-oauth.md`
- **4. Reporting templates** → `references/router-06-4-reporting-templates.md`
- **5. New MGS agent bootstrap** → `references/router-07-5-new-mgs-agent-bootstrap.md`
- **6. Agent memory / conclusion layers** → `references/router-08-6-agent-memory-conclusion-layers.md`
- **7. Git / auto-commit / auto-push do `/root/mgs-agent`** → `references/router-09-7-git-auto-commit-auto-push-do-root-mgs-agent.md`
- **8. References and support files** → `references/router-10-8-references-and-support-files.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
