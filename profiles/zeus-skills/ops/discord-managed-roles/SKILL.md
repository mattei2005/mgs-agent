---
name: discord-managed-roles
description: Roles criados automaticamente pelo Discord quando bots são adicionados a um server são "managed" e não podem ser deletados via API. Cobre diagnóstico, limitações e alternativas.
version: 1.0.0
author: Zeus
---

# Discord Managed Roles — Diagnóstico e Limitações

## Trigger

Quando for pedido para deletar um role Discord via API que foi criado automaticamente quando um bot foi adicionado ao server.

## O Problema

Roles com `managed: true` são criados e controlados por uma **integration** (ex: bot Discord). A API do Discord **não permite deletar** esses roles:

```
DELETE /guilds/{guild_id}/roles/{role_id}
→ HTTP 400: "Cannot delete a managed role"
```

Isso acontece silenciosamente se não verificar antes.

## Como Identificar

Antes de qualquer DELETE de role, checar o campo `managed`:

```bash
curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/guilds/{GUILD_ID}/roles" \
  | jq '.[] | select(.id == "{ROLE_ID}") | {name, managed, mentionable, members_count: .member_count}'
```

- `managed: true` → criado por integration (bot) → **não deletável**
- `managed: false` → criado manualmente → pode deletar

## Características dos Managed Roles de Bot

- Criados automaticamente quando bot é adicionado ao server
- Nome = nome do bot (ex: "Zeus", "Atena")
- `mentionable: false` por padrão
- Removidos automaticamente quando o bot é removido do server
- Membros: apenas o próprio bot

## A Única Forma de Remover

Remover o bot do server. O role desaparece junto automaticamente. Não há como deletar o role sem remover o bot.

## Alternativa Operacional

Se o objetivo é parar de usar o role em mentions (ex: formato REPORT-INFRA), basta **parar de mencionar o role** nos documentos e substituir por user mention direto. O role continua existindo mas inofensivo.

**Exemplo MGS:** roles "Zeus" e "Atena" existem no server mas são cosmética imutável. O formato REPORT-INFRA usa user mentions (`<@BOT_ID>` + `<@RODOLFO_ID>`) e ignora os roles completamente.

## Pitfalls

- **Não assumir que todo role pode ser deletado** — sempre checar `managed` antes de tentar DELETE
- **`mentionable: false` não indica managed** — roles manuais também podem ter mentionable=false
- **Roles managed não têm permissões customizáveis** — qualquer tentativa de editar também retorna erro
- **Membros: 1 não é sinal de inutilidade em managed roles** — é comportamento esperado (só o bot)
