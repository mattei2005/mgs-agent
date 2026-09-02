---
name: eggbev-campaign-creation
description: "Redireciona criação Eggbev para a skill compartilhada."
version: 2.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, compatibility, campaign-creation]
    related_skills: [chatpion-bot-campaign-operations]
---

# Eggbev Campaign Creation Compatibility Redirect

Compatibilidade para referências históricas. O procedimento ativo de criação está em `chatpion-bot-campaign-operations`; os valores e runners permanecem no contrato da operação.

## Procedure

1. Carregue a skill compartilhada.
2. Resolva o consumidor da operação.
3. Use somente a rota `campaign_creation` e seu prompt exato.
4. Execute pelo Campaign Engine v3 e pelos gates do contrato vivo.

## Verification

Registry, contrato e prompt devem apontar para a skill compartilhada.
