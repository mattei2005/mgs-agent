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

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Postura operacional → Validação pós-update obrigatória** → `references/route-pack-01.md`
- **Pitfalls de update** → `references/route-pack-02.md`
- **2. Web tooling nativo, search/extract e MCP → Pitfalls de provider/OAuth** → `references/route-pack-03.md`
- **4. Reporting templates → 8. References and support files** → `references/route-pack-04.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
