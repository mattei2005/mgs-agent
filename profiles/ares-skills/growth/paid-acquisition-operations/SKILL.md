---
name: paid-acquisition-operations
description: "Operações de aquisição paga/ads para MGS: estruturar operações piloto, taxonomia de criativos, Drive de assets, inventário, credenciais read-only/controlled-write, e guardrails antes de Meta/Google Ads em produção."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [ads, growth, meta-ads, google-drive, creatives, taxonomy, mgs]
---

# Paid Acquisition Operations — MGS/Ares

Use esta skill quando Rodolfo pedir para estruturar, auditar ou operacionalizar campanhas pagas, criativos, Drive, inventário, tracking ou integrações Meta/Google Ads. O padrão é **processo primeiro, credencial depois, execução por último**.

## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Princípios** → `references/router-01-princ-pios.md`
- **Ordem recomendada para uma nova operação** → `references/router-02-ordem-recomendada-para-uma-nova-opera-o.md`
- **Taxonomia base de criativos** → `references/router-03-taxonomia-base-de-criativos.md`
- **Estrutura Drive recomendada** → `references/router-04-estrutura-drive-recomendada.md`
- **Inventário mínimo** → `references/router-05-invent-rio-m-nimo.md`
- **Gate obrigatório de metadados antes de campanha** → `references/router-06-gate-obrigat-rio-de-metadados-antes-de-campanha.md`
- **Tamanhos e placements** → `references/router-07-tamanhos-e-placements.md`
- **Canva Connect / Canva Teams → Drive de criativos** → `references/router-08-canva-connect-canva-teams-drive-de-criativos.md`
- **Canva → Drive de criativos** → `references/router-09-canva-drive-de-criativos.md`
- **Credenciais Google Drive** → `references/router-10-credenciais-google-drive.md`
- **Meta Ads intraday / chatbot operations** → `references/router-11-meta-ads-intraday-chatbot-operations.md`
- **Regras de decisão de campanha** → `references/router-12-regras-de-decis-o-de-campanha.md`
- **Referências** → `references/router-13-refer-ncias.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
