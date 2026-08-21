---
name: paid-acquisition-operations
description: "Operações de aquisição paga/ads para MGS: estruturar operações piloto, taxonomia de criativos, Drive de assets, inventário, credenciais read-only/controlled-write, e guardrails antes de Meta/Google Ads em produção."
version: 1.1.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [ads, growth, meta-ads, google-drive, creatives, taxonomy, mgs]
---

# Paid Acquisition Operations — MGS/Ares

Use esta skill quando Rodolfo pedir para estruturar, auditar ou operacionalizar campanhas pagas, criativos, Drive, inventário, tracking ou integrações Meta/Google Ads. O padrão é **processo primeiro, credencial depois, execução por último**.

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Criar/clonar campanhas Meta, lotes e alta escala** → `meta-campaign-engine-v3/SKILL.md`
- **Princípios → Caminho oficial: Canva Connect API** → `references/route-pack-01.md`
- **Fallback Canva local + intake atual `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`** → `references/route-pack-02.md`
- **Precedentes históricos de `UPLOAD_CANVAS` + Meta Ads intraday** → `references/route-pack-03.md`
- **Regras de decisão de campanha → Referências** → `references/route-pack-04.md`

Campaign Engine v3 é o único executor novo. `paid-acquisition-operations` continua dona do processo/guardrails gerais e não deve criar um runner alternativo por thread ou operação.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.
