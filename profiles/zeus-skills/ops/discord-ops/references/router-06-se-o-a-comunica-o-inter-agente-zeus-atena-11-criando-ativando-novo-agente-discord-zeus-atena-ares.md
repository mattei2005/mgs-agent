### Criando/ativando novo agente Discord (Zeus/Atena/Ares)

Quando criar um novo agente Hermes no Discord, validar o token próprio no 1Password antes de escrever `.env` ou subir systemd. Ver `references/new-discord-agent-1p-flow.md`.

Checklist curto:
- O item `Discord Bot - <Agent>` deve ter campo customizado `discord_bot_token` não vazio; reportar só `len=X`, nunca o valor.
- O item `Discord Webhook - <Agent> Channel` pode ter `webhook_url` e `canal`, mas webhook **não** substitui bot token.
- Usar `set -a; source /root/mgs-agent/.env; set +a` antes de `op`, para exportar `OP_SERVICE_ACCOUNT_TOKEN`.
- Se `op://MGS Conteúdo/...` falhar por acento/espaço, resolver `vault_id`/`item_id` e usar referência por ID.
- Instalar `/etc/systemd/system/<agent>-gateway.service` exige confirmação crítica explícita; só depois validar `systemctl is-active` + logs.

