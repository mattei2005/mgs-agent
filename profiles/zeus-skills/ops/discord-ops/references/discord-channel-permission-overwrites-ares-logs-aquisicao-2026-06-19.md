# Discord channel permission overwrites — Ares logs-aquisicao (2026-06-19)

## Context
Rodolfo asked Zeus to let Ares handle future access changes for the `logs-aquisicao` channel. The first instinct was to grant Ares `VIEW_CHANNEL + MANAGE_CHANNELS` on the channel, but an idempotent validation using the Ares bot token returned `403 Forbidden` when trying to `PUT /channels/{channel_id}/permissions/{user_id}`.

## Durable lesson
Editing permission overwrites for a Discord channel requires the effective `MANAGE_ROLES` permission in that channel context. `MANAGE_CHANNELS` alone is not enough for `PUT /channels/{channel_id}/permissions/{overwrite_id}`.

For narrow channel-scoped delegation, grant the bot only on the target channel:

- `VIEW_CHANNEL` (`1024`)
- `MANAGE_CHANNELS` (`16`) when it needs channel-management capability
- `MANAGE_ROLES` (`268435456`) to edit permission overwrites

Example allow bitmask for Ares on `logs-aquisicao`:

```text
VIEW_CHANNEL + MANAGE_CHANNELS + MANAGE_ROLES = 268436496
```

This does not mean granting server-wide admin; the overwrite is scoped to the channel. Still report it clearly because `MANAGE_ROLES` is sensitive.

## Validation pattern
1. Use Zeus/admin token to apply the bot overwrite on the target channel.
2. Validate with the delegated bot token, not only Zeus:
   - idempotent `PUT /channels/{channel_id}/permissions/{known_user_id}` with the same existing overwrite
   - expect HTTP `204`
3. `GET /channels/{channel_id}` with delegated bot token and confirm the target user overwrite is present.
4. Register audit log and infra inventory under `discord_permissions`.

## Scope pitfall
Before applying category-level delegation, inspect the category children. In this case `logs-aquisicao` was under `🚨 INFRA ALERTS`, which also contained `alerts-infra`, `alerts-yoast`, and `alerts-hermes-news`. Rodolfo narrowed the authorization to the single channel after seeing the category was broader than acquisition logs.

Rule: if a requested category contains unrelated infra/admin channels, stop and confirm a narrower scope before applying permissions.
