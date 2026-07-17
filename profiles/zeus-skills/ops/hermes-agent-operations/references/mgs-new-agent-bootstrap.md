# MGS New Agent Bootstrap — Hermes Profile + Discord Channel

Use when Rodolfo asks to start a new MGS agent (e.g. Ares) after creating the Discord channel.

## Validated pattern

1. Create the Hermes profile from an existing MGS profile, usually Zeus for admin-style defaults:
   ```bash
   hermes profile create <agent> --clone-from zeus --description '<role description>'
   ```
2. Immediately sanitize the cloned `.env`:
   - Do **not** let the new profile inherit Zeus/Atena `DISCORD_BOT_TOKEN`.
   - Set `DISCORD_BOT_TOKEN=` empty until a dedicated bot token exists.
   - Set `DISCORD_ALLOWED_CHANNELS`, `DISCORD_HOME_CHANNEL`, and `DISCORD_FREE_RESPONSE_CHANNELS` to the new channel ID only.
   - Keep `DISCORD_ALLOWED_USERS=344196393512075265` unless Rodolfo explicitly adds others.
3. Copy OpenAI Codex OAuth auth from Zeus/root profile if the new agent should use the same GPT-5.5 subscription path. Validate by token length only; never print token values.
4. Edit `<profile>/config.yaml`:
   - `model.provider: openai-codex`
   - `model.default: gpt-5.5`
   - `discord.allowed_channels: <new_channel_id>`
   - `discord.free_response_channels: <new_channel_id>`
   - `discord.auto_thread: true`
   - channel prompt should keep replies in-thread and use the same auto-add policy as Zeus/Atena, scoped to the new channel.
5. Create a concise `<profile>/SOUL.md` with role, mission, authority, safety, communication style, and relation to Zeus/Atena.
6. Update `/root/mgs-agent/data/authorized-users.json` with a new `agents.<agent>` entry. Use the actual Discord channel name from API, not a guessed name.
7. Append an audit event to `/root/mgs-agent/logs/events-audit.jsonl`.
8. Update `/root/mgs-agent/scripts/sync-souls.sh` to include the new profile in both SOUL.md and config.yaml sync loops; run it once and validate the generated `profiles/<agent>-soul.md` and `profiles/<agent>-config.yaml`. Do **not** automatically sync/version bundled or vendor skill categories from the cloned profile; only add MGS-specific custom skill sync blocks when that agent actually has custom MGS skills. Do **not** add broad skill-category sync for the new agent by default: cloned profiles may contain many bundled/hub skills, and syncing them can accidentally version hundreds of inherited files. Add selective skill sync only after the agent has custom MGS-specific skills worth versioning.
9. Validate:
   ```bash
   hermes profile show <agent>
   python3 - <<'PY'
   import yaml, json
   yaml.safe_load(open('/root/.hermes/profiles/<agent>/config.yaml'))
   json.load(open('/root/mgs-agent/data/authorized-users.json'))
   print('OK')
   PY
   ```
10. Do **not** create/enable the systemd gateway until there is a dedicated bot token for that agent. Creating `/etc/systemd/system/<agent>-gateway.service` is a system-file write and requires Critical Subset confirmation.
11. After Rodolfo creates the Discord application/bot and saves the token in 1Password or the profile `.env`, continue with `references/mgs-new-agent-discord-activation.md` for token validation, channel-access validation, Message Content Intent, systemd activation, and live Discord test.

## Pitfalls

- Cloning from Zeus copies `DISCORD_BOT_TOKEN`; starting the new gateway with that token would make the new agent impersonate Zeus. Blank the token before any gateway start.
- The Discord channel ID is not enough for registry quality. Query the Discord API read-only and record the actual channel name.
- Do not start the new profile's gateway with Zeus/Atena credentials as a smoke test. Validation can stop at profile/config/auth checks until the real bot exists.
- `sync-souls.sh` only versioned Zeus/Atena originally. New persistent agents must be added or their SOUL/config will not be versioned.
- Avoid broad inherited skill sync on new agents. Cloning from Zeus/root can bring bundled creative/productivity/etc. skills; syncing a whole category like `legacy-agent/skills/creative` may commit hundreds of non-MGS files. Keep initial versioning to SOUL/config; add custom skill sync later and narrowly.
- Auto-commit can race with bootstrap mistakes. After running `sync-souls.sh`, check `git status --short` before final report; if accidental files were committed, remove them cleanly and verify origin/main is synchronized before saying the repo is clean.
