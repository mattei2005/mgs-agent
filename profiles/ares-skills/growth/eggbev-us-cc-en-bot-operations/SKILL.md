---
name: eggbev-us-cc-en-bot-operations
description: "Redireciona Eggbev para a estratégia BOT compartilhada."
version: 2.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, compatibility, bot, messenger]
    related_skills: [chatpion-bot-campaign-operations]
---

# Eggbev BOT Compatibility Redirect

Compatibilidade para referências históricas. A fonte procedural ativa é `chatpion-bot-campaign-operations`; identidade, valores, authority, runners, threads e estados continuam no contrato `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`.

## When to Use

Use somente quando uma referência antiga carregar esta skill pelo nome.

## Procedure

1. Carregue `chatpion-bot-campaign-operations`.
2. Resolva `Eggbev-US-CC-EN-BOT` no consumer registry.
3. Abra apenas a rota pedida do contrato da operação.
4. Não trate esta camada como política independente.

## Verification

A rota ativa, o contrato e o prompt devem apontar para `chatpion-bot-campaign-operations`.
