## SEÇÃO B — Roles Managed (não deletáveis via API)

### O Problema

Roles com `managed: true` são criados quando um bot é adicionado ao server. A API **não permite deletar**:
```
DELETE /guilds/{guild_id}/roles/{role_id} → HTTP 400: "Cannot delete a managed role"
```

### Como Identificar

```bash
curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/guilds/{GUILD_ID}/roles" \
  | jq '.[] | select(.id == "{ROLE_ID}") | {name, managed}'
# managed: true → não deletável; managed: false → pode deletar
```

### Características

- Criados automaticamente quando bot é adicionado
- Nome = nome do bot (ex: "Zeus", "Atena")
- `mentionable: false` por padrão
- Removidos apenas quando o bot é removido do server

### Alternativa Operacional

Parar de mencionar o role — usar **user mention direto** (`<@BOT_ID>` + `<@344196393512075265>`). O role continua existindo mas inofensivo. **Por que não usar role mention:** a role `mentionable: false` e não dispara push notification para Rodolfo. User mention direto é o que realmente notifica.

---
