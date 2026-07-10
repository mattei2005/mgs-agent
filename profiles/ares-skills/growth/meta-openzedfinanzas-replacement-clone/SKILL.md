---
name: meta-openzedfinanzas-replacement-clone
description: "Clone/replacement da campanha OpenzedFinanzas Meta Ads: estrutura real da campanha Patricia Flores loser, nomenclatura RPL, seleção de criativos vencedores, budget USD 25 e validações de clone."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, replacement, clone, openzedfinanzas, campaign-structure, mgs]
---

# Meta OpenzedFinanzas Replacement Clone

Use esta skill quando Rodolfo pedir para clonar/replacement de campanhas da conta Meta `OpenzedFinanzas-ES-CC-ES-03`.

## Progressive disclosure — mandatory

1. Identify the exact branch below before loading details.
2. Load one primary reference first.
3. Load another reference only when the first requires it or live evidence changes the branch.
4. Never load every reference, the full catalog, or broad source ranges “for context.”
5. For repeated lookups, search the exact symbol/path and aggregate results before returning them to model context.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Routing index

- **Conta/operação** → `references/router-01-conta-opera-o.md`
- **Campanha loser mapeada** → `references/router-02-campanha-loser-mapeada.md`
- **Estrutura real da campanha** → `references/router-03-estrutura-real-da-campanha.md`
- **Nomenclatura operacional: scale vs replacement** → `references/router-04-nomenclatura-operacional-scale-vs-replacement.md`
- **Padrão de nomenclatura Meta — escala, ads e criativos** → `references/router-05-padr-o-de-nomenclatura-meta-escala-ads-e-criativos.md`
- **Regras de clone** → `references/router-06-regras-de-clone.md`
- **Source mirror obrigatório antes de writes EU/financeiro** → `references/router-07-source-mirror-obrigat-rio-antes-de-writes-eu-financeiro.md`
- **Script canônico** → `references/router-08-script-can-nico.md`
- **Criativos vencedores do dry-run inicial** → `references/router-09-criativos-vencedores-do-dry-run-inicial.md`
- **Tentativa real 2026-06-18** → `references/router-10-tentativa-real-2026-06-18.md`
- **Prioridade operacional: separar “replacement Ares” de “clone fiel”** → `references/router-11-prioridade-operacional-separar-replacement-ares-de-clone-fiel.md`
- **Correção aprendida com playbook externo de clone** → `references/router-12-corre-o-aprendida-com-playbook-externo-de-clone.md`
- **Diagnóstico token/app, página alternativa e camada `POST /ads`** → `references/router-13-meta-runtime-diagnostics.md`
- **Comunicação com Rodolfo em troubleshooting Meta** → `references/router-14-comunica-o-com-rodolfo-em-troubleshooting-meta.md`
- **Preferência operacional do Rodolfo para testes de clone** → `references/router-15-prefer-ncia-operacional-do-rodolfo-para-testes-de-clone.md`
- **Pitfalls** → `references/router-16-pitfalls.md`

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Reduce tool output above roughly 5 KB before any additional broad lookup.
- Preserve exact procedures in topical references; keep this `SKILL.md` as the routing layer.
- Validate the real result before reporting success.
