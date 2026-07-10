### Novo agente Discord/Hermes — bootstrap de bot, token e service

Quando criar um novo agente MGS com bot/canal próprios (ex: Ares), seguir o playbook `references/new-discord-agent-bootstrap.md`. Ele cobre: scopes OAuth2 (`bot` + `applications.commands`), permissões mínimas, campo 1Password `discord_bot_token`, `.env`, service systemd pelo template Zeus/Atena, e validação separada de gateway online vs bot realmente membro do servidor/canal.

Pitfall crítico validado: `Connected as <Agent>#...` prova token/gateway, mas não prova acesso ao servidor. Se `GET /channels/<channel_id>` com o token do novo bot retorna `403 Missing Access` e `GET /guilds/<guild_id>/members/<bot_id>` com bot admin retorna `404 Unknown Member`, o bot ainda não foi convidado ao servidor ou o invite não concluiu.

