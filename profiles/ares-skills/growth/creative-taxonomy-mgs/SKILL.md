---
name: creative-taxonomy-mgs
description: "Taxonomia operacional de criativos MGS para aquisição paga: nomenclatura de arquivos, campos obrigatórios, P_ORIENT, inventário, status, validação e regras de classificação antes de usar assets em campanhas."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [mgs, ads, creatives, taxonomy, naming, drive, meta-ads]
    related_skills: [paid-acquisition-operations]
---

# Creative Taxonomy MGS

## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Objetivo** → `references/router-01-objetivo.md`
- **Quando usar** → `references/router-02-quando-usar.md`
- **Modelo oficial do nome de arquivo** → `references/router-03-modelo-oficial-do-nome-de-arquivo.md`
- **Campos do nome** → `references/router-04-campos-do-nome.md`
- **Verticais** → `references/router-05-verticais.md`
- **FORMAT** → `references/router-06-format.md`
- **ANGLE** → `references/router-07-angle.md`
- **P_ORIENT** → `references/router-08-p-orient.md`
- **Orientation, placement e dimensões** → `references/router-09-orientation-placement-e-dimens-es.md`
- **Status e ciclo de vida** → `references/router-10-status-e-ciclo-de-vida.md`
- **Entrada operacional via Hera** → `references/router-11-entrada-operacional-via-hera.md`
- **Estrutura Drive recomendada** → `references/router-12-estrutura-drive-recomendada.md`
- **Inventário mínimo** → `references/router-13-invent-rio-m-nimo.md`
- **Procedimento seguro de classificação** → `references/router-14-procedimento-seguro-de-classifica-o.md`
- **Sanitização antes de campanha** → `references/router-15-sanitiza-o-antes-de-campanha.md`
- **Regras de segurança** → `references/router-16-regras-de-seguran-a.md`
- **Checklist de validação** → `references/router-17-checklist-de-valida-o.md`
- **Pitfalls comuns** → `references/router-18-pitfalls-comuns.md`
- **Referências internas** → `references/router-19-refer-ncias-internas.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
