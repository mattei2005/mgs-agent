---
name: eggbev-page-guardrails
description: "Redireciona guardrails Eggbev à skill compartilhada."
version: 2.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, compatibility, page-guardrails]
    related_skills: [chatpion-bot-campaign-operations]
---

# Eggbev Page Guardrails Compatibility Redirect

Compatibilidade para referências históricas. O mecanismo ativo está em `chatpion-bot-campaign-operations`; métricas, thresholds, holds, denylist, runners e schedules permanecem no contrato da operação.

## Procedure

1. Carregue a skill compartilhada.
2. Resolva o consumidor da operação.
3. Use somente `page_guardrails` e o prompt exato.
4. Nunca copie state, Page ou limite a outro consumidor.

## Verification

Registry, contrato e prompt devem apontar para a skill compartilhada.
