# MGS New Agent Discord Bot Token + Gateway Activation

Session-derived reference for bringing a newly bootstrapped MGS Hermes profile online as a Discord bot after the profile/config/SOUL already exist.

## Scope

Use after the safe Phase 1 bootstrap from `references/mgs-new-agent-bootstrap.md` is complete and Rodolfo has created the Discord application/bot and channel.

## Required data from Rodolfo

```text
Discord channel ID
Discord application/bot ID
Permissions integer
Confirmation that bot token is saved in 1Password or already written to the profile .env
```

Never ask Rodolfo to paste the token in chat.

## Recommended Discord OAuth permissions

Minimum practical set for an MGS agent channel:

```text
View Channels
Send Messages
Create Public Threads
Send Messages in Threads
Embed Links
Attach Files
Read Message History
Add Reactions
Use Slash Commands
Manage Threads
```

Do not grant Administrator by default.

## 1Password token pattern

Preferred item pattern:

```text
Vault: MGS Conteúdo
Item: Discord Bot - <Agent>
Field: discord_bot_token
```

Because the interactive `op` account may not be configured in non-interactive/root sessions, source `/root/mgs-agent/.env` for `OP_SERVICE_ACCOUNT_TOKEN` before calling `op`:

```bash
set -a
source /root/mgs-agent/.env
set +a
op item get "Discord Bot - agente legado" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields discord_bot_token --reveal
```

Do not print the token. Validate only `len`, decoded bot ID, and Discord API identity.

## Token validation without leaking secret

Discord bot tokens encode the bot/application ID in the first token segment. Validate that it matches the expected application ID, then probe `/users/@me`.

Report shape:

```text
item=Discord Bot - agente legado
field=discord_bot_token
token_len=72
decoded_bot_id=<expected_id>
api_bot_id=<expected_id>
api_username=agente legado
env_written=/root/.hermes/profiles/legacy-agent/.env
```

## Channel validation

Probe the target channel with the bot token:

```text
GET https://discord.com/api/v10/channels/<channel_id>
Authorization: Bot <token>
```

Outcomes:

```text
200 OK              bot can see the channel
403 Missing Access  bot is in the guild but lacks channel/category View Channel access
401 Unauthorized    token wrong/revoked
```

If `/users/@me/guilds` shows the MGS guild but channel returns `403 Missing Access`, the fix is server/channel permissions, not token. Add the bot/member on the channel or category and explicitly allow at least `View Channel`, `Send Messages`, `Create Public Threads`, `Send Messages in Threads`, and `Read Message History`.

## Gateway service creation

Use the existing Ares/Zeus service as template:

```ini
[Unit]
Description=Hermes Gateway — agente legado (MGS Digital Corp)
After=network-online.target
Wants=network-online.target

[Service]
KillMode=mixed
TimeoutStopSec=300
RestartForceExitStatus=75
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.hermes/profiles/legacy-agent/.env
Environment="PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/.local/bin/hermes -p legacy-agent gateway run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=legacy-agent-gateway

[Install]
WantedBy=multi-user.target
```

Creating `/etc/systemd/system/<agent>-gateway.service` is a Critical Subset/system-file write; require explicit confirmation before executing.

## Privileged intents pitfall

If logs show:

```text
PrivilegedIntentsRequired: requesting privileged intents that have not been explicitly enabled in the developer portal
```

then enable **Message Content Intent** in Discord Developer Portal → Application → Bot → Privileged Gateway Intents. Presence and Server Members intents are not needed by default for numeric allowlists.

If the service starts looping/failing on this, stop and disable it until the intent is enabled:

```bash
systemctl disable --now <agent>-gateway.service
systemctl reset-failed <agent>-gateway.service
```

## End-to-end validation

After `systemctl enable --now`:

```bash
systemctl is-enabled <agent>-gateway.service
systemctl is-active <agent>-gateway.service
journalctl -u <agent>-gateway.service --since '2 minutes ago' --no-pager -o short-iso
hermes profile show <agent>
```

Expected log evidence:

```text
[Discord] Connected as <Agent>#NNNN
✓ discord connected
Gateway running with 1 platform(s)
Channel directory built: N target(s)
```

Then send a real message mentioning the bot in its channel. Confirm logs show:

```text
inbound message
OpenAI client created provider=openai-codex model=gpt-5.5
response ready
Sending response
auto-thread member sync / thread renamed if applicable
```

Only then report the agent as operational.

## Audit log

Append events for:

```text
agent app registered / permissions recorded
token validated and written
channel access validation pass/fail
gateway created/started
gateway live validated
```

Never include token values in audit logs.
