---
name: meta-ads-governance-guardrails
description: "Redirect de compatibilidade para os guardrails Meta consolidados em meta-ads-intraday-operations."
version: 2.0.0
author: MGS Digital Corp
license: internal
metadata:
  hermes:
    tags: [meta-ads, governance, guardrails, compatibility, mgs]
---

# Meta Ads Governance — Redirect

Esta skill não é um fluxo operacional separado.

A fonte procedural canônica para autorização, modos `read_only`/`dry_run`/`recommend`/`controlled_write`, token, budget, billing, rate limit, auditoria e validação pós-write é:

```text
meta-ads-intraday-operations/SKILL.md
## Governança Meta consolidada
```

Ao receber assunto de governança Meta:

1. carregar `meta-ads-intraday-operations`;
2. aplicar a seção **Governança Meta consolidada**;
3. carregar a operação/conta real e suas permissões;
4. não inferir autorização de write a partir deste redirect;
5. validar qualquer ação real por GET/readback e audit.

Este redirect é preservado apenas para links e rotas históricas que ainda usem o nome antigo. Não duplicar regras aqui.
