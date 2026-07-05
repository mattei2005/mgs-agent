# Discord bot channel removal with managed Administrator role — 2026-07-05

## Context

Rodolfo asked Zeus to remove Atena from Discord channel `vps-status` (`1522444367292268565`). Atena could still read the channel because its bot-created managed role had the Discord `Administrator` bit, which bypasses channel permission overwrites.

## Durable lesson

A channel-level deny does **not** remove access for a bot whose managed role has `Administrator`. For bot isolation by channel, first remove the `Administrator` bit from the bot's managed role, then add explicit channel overwrites.

## Validated sequence

1. Use Zeus/admin bot token for Discord REST writes.
2. Include a Discord-compatible `User-Agent` header on raw REST calls. Without it, Cloudflare/Discord may return `403 error code: 1010` even for valid tokens.
3. Inspect the target channel and the bot/member role assignment.
4. If the bot's managed role has `Administrator`, PATCH the guild role permissions to remove bit `8`.
5. Add explicit deny on the target channel for the bot's managed role:
   - `type: 0` role overwrite
   - `allow: "0"`
   - `deny: "1024"` (`VIEW_CHANNEL`)
6. Preserve the bot's own operational channel by adding a minimal allow overwrite there. For Atena, `allow: "68608"` covered the needed base channel/thread access used in validation.
7. Validate using the target bot token, not Zeus only:
   - target channel GET must return `403 Missing Access`
   - bot home channel GET must still return `200`
8. Append an audit event to `/root/mgs-agent/logs/events-audit.jsonl`.

## Example sanitized result

- Atena role before: `permissions=8863158936010747`, admin bit true.
- Atena role after: `permissions=8863158936010739`, admin bit false.
- Atena GET `vps-status`: `403 Missing Access`.
- Atena GET `atena`: `200 atena`.

## Pitfalls

- Bot-created managed roles cannot be deleted via API, but their permission bitset can be patched when the acting bot has enough authority and role hierarchy allows it.
- Do not rely on Zeus visibility as proof. Always validate with the bot being restricted.
- If removing `Administrator` breaks the bot's own channel, add narrow allow overwrites to the channels it should keep, instead of re-adding Administrator.
