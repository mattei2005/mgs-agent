---
name: eggbev-daily-reporting
description: "Redireciona Diário Eggbev para a skill compartilhada."
version: 2.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, compatibility, daily-reporting]
    related_skills: [chatpion-bot-campaign-operations]
---

# Eggbev Daily Compatibility Redirect

Compatibilidade para referências históricas. O mecanismo read-only ativo está em `chatpion-bot-campaign-operations`; fontes, períodos, layout, runners e schedule permanecem no contrato da operação.

## Procedure

1. Carregue a skill compartilhada.
2. Resolva o consumidor da operação.
3. Use somente `daily_reporting` e o prompt exato.
4. Mantenha ausência ou staleness como `N/D` e zero write.

## Verification

Registry, contrato e prompt devem apontar para a skill compartilhada.
