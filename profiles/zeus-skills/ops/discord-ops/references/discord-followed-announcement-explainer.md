# Discord followed announcement channel → Zeus explainer

Use this pattern when Rodolfo creates a Discord channel that follows an upstream announcements channel (Discord `Follow` / crosspost) and wants Zeus to explain every new upstream post below the announcement.

## Proven production pattern

Do **not** add the announcements channel directly to Zeus/Atena `allowed_channels` unless the user explicitly wants normal agent conversation there. A followed announcement channel is better handled by a small poller cron owned by Zeus:

1. Verify bot access with Discord API `GET /channels/{channel_id}` using both Zeus and Atena tokens.
2. Confirm current gateway `allowed_channels` for both profiles; channel membership/access does not mean the gateway listens there.
3. Create a script under `/root/mgs-agent/scripts/` that:
   - polls `/channels/{channel_id}/messages?limit=N`;
   - keeps a state file with `last_seen_id` and `processed` reply IDs;
   - skips its own bot messages and Discord follow/system messages as needed;
   - extracts `content`, embeds, fields, attachments;
   - runs `hermes -p zeus -z` with a constrained PT-BR executive prompt;
   - posts a Discord message reply with `message_reference` so the explanation appears directly below the upstream announcement;
   - uses `allowed_mentions: {"parse": []}` to avoid accidental pings.
4. Initialize state to the current newest message so old follow/setup messages are not reprocessed.
5. Add cron with `flock -n`, e.g. every 5 minutes, logging to `/root/mgs-agent/logs/`.
6. Validate with: `py_compile`, `--init`, `--dry-run`, manual execution, crontab grep, JSON validation for inventory.
7. Register script/cron/state in `infra-inventory.json` and regenerate `docs/CRONS.md` when applicable.
8. Runtime state files that update every poll should be ignored in `.gitignore`; do not keep auto-committing `last_seen_id` churn.

## Why this is safer than adding the channel to normal gateway listening

- Announcements are usually bot/webhook/crosspost messages; Hermes bot handling and mention rules can be noisy.
- A normal gateway listener can create auto-threads or respond conversationally in a channel intended as a clean feed.
- Atena should usually stay out of Hermes/admin announcement flows; Zeus owns explanation of Hermes/platform changes.
- A poller gives deterministic idempotency and reply placement without changing agent interaction scope.

## Pitfalls

- Discord access check only proves the bot can read the channel; it does **not** prove Hermes gateway will process messages. Check `discord.allowed_channels` separately.
- Follow setup messages can have type `12`; initialize state after setup and skip system/follow noise.
- A cron that invokes `hermes -z` may consume model budget. Keep the prompt short and the poll interval reasonable.
- Keep `HERMES_BACKGROUND_NOTIFICATIONS=off` in the subprocess environment to avoid background notification noise.
- Do not mention Rodolfo in each explanation unless he explicitly wants push notifications for every upstream announcement.