# MGS Hera Discord Bootstrap — 2026-06-06

Session-specific notes from bootstrapping the Hera creative agent.

## Scope

Created Hera as a new MGS Hermes profile and Discord gateway candidate:

- Profile: `/root/.hermes/profiles/hera`
- Channel: `#hera-creative-agent` / `1513005743954198538`
- Discord application/bot ID: `1513006098133680290`
- Permission integer used for invite: `328565115968`
- 1Password item: `Discord Bot - Hera`
- 1Password field: `discord_bot_token`

## Safe bootstrap sequence that worked

1. Clone/create profile from Zeus/Hermes profile defaults.
2. Immediately blank inherited `DISCORD_BOT_TOKEN` before any gateway start.
3. Scope `.env` and `config.yaml` to the new channel only.
4. Copy OpenAI Codex auth from Zeus/root and validate token length only.
5. Write a concise new-agent `SOUL.md` with role, scope, handoffs and safety boundaries.
6. Update `data/authorized-users.json` and append an event to `logs/events-audit.jsonl`.
7. Update `scripts/sync-souls.sh` to sync only new agent `SOUL.md` and `config.yaml` unless the new agent has MGS-specific custom skills. Do **not** blindly sync inherited bundled/vendor skill trees into `/root/mgs-agent/profiles/`.
8. Validate profile/config/auth before creating any systemd unit.
9. Only after token/channel validation, create `/etc/systemd/system/<agent>-gateway.service` from the Ares/Zeus template.

## Discord permissions/invite

Minimal Hera-style bot permissions selected:

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

Avoid `Administrator` unless explicitly approved.

## 1Password token retrieval pattern

If `op item get` says no account is configured, source the project service-account env first:

```bash
set -a
source /root/mgs-agent/.env
set +a
op item get 'Discord Bot - Hera' --vault 'MGS Conteúdo' --fields 'discord_bot_token' --reveal
```

Never print the token. Validate by length, token-prefix decoded bot ID, and Discord API `/users/@me`.

## Channel access validation pitfall

A bot may be in the guild and validate via `/users/@me`, but still fail channel access:

```text
GET /channels/<channel_id> -> 403 Missing Access
```

Fix in Discord server/channel settings:

- Add the bot/member explicitly to the channel or category permissions.
- Allow at least `View Channel`, `Send Messages`, `Create Public Threads`, `Send Messages in Threads`, and `Read Message History`.
- If the channel inherits from a category, check category permissions or make the channel unsynced with explicit bot allow.

Only proceed with gateway after `GET /channels/<channel_id>` returns 200 and the expected channel name/guild.

## Privileged intent pitfall

Hermes Discord gateway requests `message_content = True`. If the new bot has not enabled the privileged intent in the Discord Developer Portal, the gateway can start then fail with:

```text
discord.errors.PrivilegedIntentsRequired
requesting privileged intents that have not been explicitly enabled
```

Fix:

```text
Discord Developer Portal
→ Applications
→ <bot>
→ Bot
→ Privileged Gateway Intents
→ Message Content Intent = ON
→ Save Changes
```

Do not enable Presence Intent or Server Members Intent unless there is a separate need.

Operational safety: if this appears after creating the systemd service, stop/disable/reset-failed the service until the intent is enabled to avoid an endless restart loop:

```bash
systemctl disable --now <agent>-gateway.service
systemctl reset-failed <agent>-gateway.service
```

Then re-enable/start after the portal setting is fixed.

## Service template

Use the Ares/Zeus template with the profile-specific env and command:

```ini
[Unit]
Description=Hermes Gateway — Hera (MGS Digital Corp)
After=network-online.target
Wants=network-online.target

[Service]
KillMode=mixed
TimeoutStopSec=300
RestartForceExitStatus=75
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.hermes/profiles/hera/.env
Environment="PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/.local/bin/hermes -p hera gateway run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hera-gateway

[Install]
WantedBy=multi-user.target
```

## Validation order

```text
1. `systemctl is-active <agent>-gateway.service`
2. `hermes profile show <agent>` shows Gateway: running
3. `journalctl -u <agent>-gateway.service` has Discord connected or no fatal intent error
4. Send a real mention test in the agent's channel
5. Confirm response in Discord before reporting end-to-end success
```
