# Smart Bidding Messenger invalid-token monitor

Use this procedure when MGS needs to mirror Smart Bidding alerts titled `Messenger user token invalid` into a dedicated Discord channel.

## Source and scope

- Authenticated read-only source: `GET https://api.jbfdigital.com.br/notification`.
- Filter exactly `COMPANY in {digital-trust, digital-trust-2}` and `TITLE == Messenger user token invalid`.
- Parse `BODY` only as a JSON list. Fail closed on malformed or empty bodies.
- The body provides `user_id`, `user_name`, `user_email`, `segurador_id`, `segurador_name` and `source` (`page_token` or `canary`).
- Never read, persist, print or validate the underlying Facebook tokens.

## Page-count enrichment

1. Open the canonical headed/Xvfb Smart Bidding session and capture only the dashboard authorization header in memory.
2. Read `/company` and collect active `publisherId` values.
3. Read `/campaigns/Messenger` for the complete publisher scope.
4. Count rows by exact `(MESSENGER_USER_ID, COMPANY, publisher-domain)`; use user-only count only as an explicitly labelled fallback.
5. Persist only aggregate counts, not campaign rows or password/token fields.

## Delivery contract

- Dedicated channel: `#seguradores-token-fb` (`1521350832426188961`).
- Zeus bot transport; one embed per affected Messenger user, maximum 10 embeds per Discord message.
- `content` empty and `allowed_mentions.parse=[]`. This matches `#paginas-restritas`: 627 inspected messages contained zero direct mentions.
- Keep the embed compact: put the uppercased site/domain first in the title (`SITE — Token Messenger inválido`).
- Show only three fields: `User`, `Segurador` and `Páginas`. Do not add explanatory description, company, visible source, action text or a separate detection-time field.
- Preserve only compact footer/timestamp metadata for audit and dedupe.
- Canary titles must start with `CANÁRIO`, while keeping the site immediately after the prefix.
- After POST, GET the exact message and verify target channel, empty content, expected embed count and zero mentions.

## State and idempotency

- Deduplicate by numeric SB notification ID.
- On first production run, seed a baseline at the maximum current ID and do not replay historical alerts.
- Persist an outbox/pending intent before delivery. After every delivered chunk, persist its Discord message ID.
- On restart, GET and verify already delivered chunks, then resume only missing chunks.
- Advance `last_seen_id` and clear pending only after every chunk passes readback.
- State file mode must be `0600`; do not chmod the shared `data/` directory.

## Schedule and validation

- Canonical cadence: `12,27,42,57 * * * *` with `flock -n` and durable `/root/.local/share/mgs/sb-venv/bin/python` under `xvfb-run -a`.
- Stale-log watchdog tolerance: 60 minutes for the explicit 15-minute list.
- Validate with `py_compile`, unit fixtures, mocked Discord POST/GET, live baseline, live no-op and one authorized canary.
- Canary/reference validated 2026-08-26: message `1542340059464728713`, six embeds, empty content, zero mentions.
