---
name: eggbev-roas-operations
description: "Redireciona ROAS Eggbev para a skill compartilhada."
version: 2.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, compatibility, roas]
    related_skills: [chatpion-bot-campaign-operations]
---

# Eggbev ROAS Compatibility Redirect

Compatibilidade para referências históricas. O mecanismo ativo está em `chatpion-bot-campaign-operations`; thresholds, fases, horários, budgets, runners e estados permanecem no contrato Eggbev.

## Procedure

1. Carregue a skill compartilhada.
2. Resolva o consumidor da operação.
3. Use somente `roas_cycle` e o prompt exato.
4. Nunca propague um valor Eggbev a outro consumidor.

## Verification

Registry, contrato e prompt devem apontar para a skill compartilhada; o threshold vigente deve vir do contrato da operação.
