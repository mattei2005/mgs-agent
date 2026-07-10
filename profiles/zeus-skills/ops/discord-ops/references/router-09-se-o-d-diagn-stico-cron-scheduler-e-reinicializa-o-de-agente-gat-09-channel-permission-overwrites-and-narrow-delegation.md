### Channel permission overwrites and narrow delegation

When Rodolfo asks Zeus to let another agent (Ares/Hera/Atena) manage future user access to a specific Discord channel, treat it as a channel-scoped permission delegation, not a global admin grant. Validate scope first: list/check the category children before applying category-level changes. If the category contains unrelated infra/admin channels, stop and confirm a narrower channel-only scope.

For Discord API `PUT /channels/{channel_id}/permissions/{overwrite_id}`, `MANAGE_CHANNELS` alone is not enough. The delegated bot also needs effective `MANAGE_ROLES` in that channel context to edit permission overwrites; otherwise validation with the delegated bot token can return `403 Forbidden` even if Zeus/admin can set the overwrite. Use the delegated bot token for final validation, not only Zeus/admin.

Validated narrow pattern:
- Apply bot overwrite on the target channel only: `VIEW_CHANNEL + MANAGE_CHANNELS + MANAGE_ROLES` when the bot must edit channel permission overwrites.
- Add/read users with overwrite `type: 1`, `allow: VIEW_CHANNEL + READ_MESSAGE_HISTORY` (`66560`), `deny: 0`.
- Validate idempotently using the delegated bot token: `PUT /channels/{channel_id}/permissions/{known_user_id}` returns HTTP `204`, then `GET /channels/{channel_id}` confirms the overwrite.
- Register audit log and inventory under `discord_permissions`; explain clearly that `MANAGE_ROLES` is channel-scoped for overwrites, not global role administration.

Reference: `references/discord-channel-permission-overwrites-ares-logs-aquisicao-2026-06-19.md`.

