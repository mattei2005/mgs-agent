# New Discord agent bootstrap — bot token, gateway service, channel threads

Use this when creating a new MGS Discord/Hermes agent profile (e.g. Ares) or bringing a new bot online.

## 1. Discord OAuth invite settings

In Discord Developer Portal → Application → OAuth2 → URL Generator:

```text
Scopes:
[x] bot
[x] applications.commands

Bot permissions:
[x] View Channels
[x] Send Messages
[x] Create Public Threads
[x] Create Private Threads
[x] Send Messages in Threads
[x] Read Message History
[x] Add Reactions
[x] Use Slash Commands
[x] Attach Files
[x] Embed Links
[ ] Mention Everyone
[ ] Manage Channels
[ ] Manage Threads     # not needed unless a later validation proves it
[ ] Administrator
```

After the bot is invited, validate membership from an existing admin bot token before troubleshooting gateway code:

```bash
GET /guilds/{guild_id}/members/{new_bot_id}
# 404 Unknown Member => invite not completed
```

## 2. 1Password item shape

Bot token item:

```text
Vault: MGS Conteúdo
Item: Discord Bot - <Agent>
Field: discord_bot_token
```

Webhook item, if used:

```text
Vault: MGS Conteúdo
Item: Discord Webhook - <Agent> Channel
Fields:
- webhook_url
- canal
```

Do not print secret values. Report only item name, field name, and `len=N`.

1Password CLI pitfall: if vault names contain accents/spaces, `op://vault/item/field` references can fail. Prefer `op item get --vault 'MGS Conteúdo' --format json`, or use vault/item IDs for `op read`.

## 3. Profile `.env` minimum

Set the bot token and channel isolation:

```text
DISCORD_BOT_TOKEN=<from 1P discord_bot_token>
DISCORD_ALLOWED_USERS=344196393512075265
DISCORD_ALLOWED_CHANNELS=<agent_channel_id>
DISCORD_HOME_CHANNEL=<agent_channel_id>
DISCORD_REQUIRE_MENTION=false
DISCORD_AUTO_THREAD=true
DISCORD_ALLOW_BOTS=mentions
DISCORD_FREE_RESPONSE_CHANNELS=<agent_channel_id>
DISCORD_THREAD_REQUIRE_MENTION=true
DISCORD_THREAD_AUTO_ADD_USERS=344196393512075265
BROWSER_DISABLE_SCREENSHOTS=true
```

`DISCORD_THREAD_AUTO_ADD_USERS` is the durable fix for private channel threads where Rodolfo must be added/subscribed. It avoids relying on agent-side `execute_code` bootstrap that cannot access `DISCORD_BOT_TOKEN` because Hermes scrubs provider credentials in tool sandboxes.

## 4. Channel permission overwrite

Private agent channels may deny `View Channel` to `@everyone`, so the newly invited bot can still be in the guild but see `403 Missing Access` for the channel. Add a bot/user overwrite for the new bot with at least:

```text
View Channels
Send Messages
Create Public Threads
Create Private Threads
Send Messages in Threads
Read Message History
Add Reactions
Use Slash Commands
Attach Files
Embed Links
```

Validation:

```bash
GET /channels/<agent_channel_id>                  # using new bot token => 200
GET /channels/<agent_channel_id>/messages?limit=3 # using new bot token => 200
```

## 5. Systemd service template

Mirror Zeus/Atena services:

```ini
[Unit]
Description=Hermes Gateway — <Agent> (MGS Digital Corp)
After=network-online.target
Wants=network-online.target

[Service]
KillMode=mixed
TimeoutStopSec=300
RestartForceExitStatus=75
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.hermes/profiles/<agent>/.env
Environment="PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/.local/bin/hermes -p <agent> gateway run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=<agent>-gateway

[Install]
WantedBy=multi-user.target
```

Critical subset: creating/modifying `/etc/systemd/system/<agent>-gateway.service` requires confirmation before applying.

Validation sequence:

```bash
systemd-analyze verify /etc/systemd/system/<agent>-gateway.service
systemctl daemon-reload
systemctl enable <agent>-gateway.service
systemctl restart <agent>-gateway.service
systemctl is-active <agent>-gateway.service
systemctl show <agent>-gateway.service -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u <agent>-gateway.service -n 120 --no-pager
```

Expected logs:

```text
[Discord] Connected as <Agent>#....
✓ discord connected
Gateway running with 1 platform(s)
```

## 6. Auto-thread/member validation

Send a real mention from an existing bot/user in the parent channel. The bot should create a thread, respond inside it, and add Rodolfo as a thread member.

Validate via API with the new bot token:

```bash
GET /channels/<thread_id>
GET /channels/<thread_id>/thread-members/344196393512075265
GET /channels/<thread_id>/messages?limit=5
```

Expected:

```text
thread OK
rodolfo_member OK
messages include new bot response
agent.log: Auto-thread member sync ... added=['344196393512075265'] failed=[]
```

## 7. Reporting shape

Use concise executive report:

```text
Item                         Resultado
---------------------------- -----------------------------------------------
.env                         OK, token configurado len=N
Service file                 criado: /etc/systemd/system/<agent>-gateway.service
systemd verify               OK
Service state                active/running
Discord login                OK: <Agent>#....
Gateway                      OK: running with 1 platform
Channel access               OK
Thread auto-create           OK
Rodolfo auto-add             OK
Smoke test                   PASS
```

End with `Próximo passo pendente:` naming the next integration or remaining blocker.
