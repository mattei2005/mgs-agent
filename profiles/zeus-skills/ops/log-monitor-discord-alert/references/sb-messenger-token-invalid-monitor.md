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
2. Read `/users/Messenger` for `digital-trust` and `digital-trust-2`.
3. Map each alert to the SB Messenger user inside the exact `COMPANY + PUBLISHER_ID` scope. Match `LOGIN == user_email` first; only if there is no unique email match, fall back to a unique `NAME == user_name`. Never combine email and name candidates with one OR because duplicated display names can make an otherwise exact email match look ambiguous. The numeric `user_id` inside the notification body is not the UUID used by campaign rows.
4. Read `/company`, collect active `publisherId` values, then read `/campaigns/Messenger` for the complete publisher scope.
5. Count campaign rows by the matched user UUID in `MESSENGER_USER_ID`. If the user cannot be mapped uniquely, render `Páginas: —` instead of inventing a count.
6. Persist only aggregate counts, not campaign rows or password/token fields.

## Delivery contract

- Dedicated channel: `#seguradores-token-fb` (`1521350832426188961`).
- Zeus bot transport; exactly one Discord message and one embed per affected Messenger user so a ✅ reaction resolves one incident only.
- Every alert and reminder mentions both team roles once: Gestor de Trafego (`1496256346994249912`) and Admin (`1496260941787168848`). Set `allowed_mentions.parse=[]` and explicitly list only those two role IDs.
- Keep the embed compact: put the uppercased site/domain first in the title (`SITE — Token Messenger inválido`).
- Show only three fields: `User`, `Segurador` and `Páginas`. Do not add explanatory description, company, visible source or a separate detection-time field.
- Keep the short content line `<roles> · Reaja ✅ quando resolver.` and compact footer/timestamp metadata for audit and dedupe.
- Canary titles start with `CANÁRIO`. Initial production alerts have no repetition badge. Repeated deliveries use `LEMBRETE #N — SITE — Token Messenger inválido`, where `N` counts only repetitions after the initial alert.
- Repeated-alert footers show `Aberto há Hh · repetido Nx · SB #ID`; keep the initial alert footer compact.
- After POST, GET the exact message and verify target channel, exact content, title, color, footer, fields, one embed and both `mention_roles` IDs.

## State, resolution and idempotency

- Deduplicate initial deliveries by numeric SB notification ID.
- Stable incident key: `company + domain + user_id + segurador_id`.
- A ✅ reaction on the latest Discord message is the explicit resolution signal. Mark the incident resolved and stop reminders.
- If no ✅ exists, repeat the alert after three hours; every repeated message mentions both team roles again and increments `repeat_count` exactly once. A newer SB notification for the same still-active incident is also rendered as the next numbered repetition and resets the three-hour timer.
- After ✅, a later SB notification with the same stable key opens a new lifecycle with `repeat_count=0`; the prior acknowledgement never becomes a permanent ignore.
- Keep `opened_at`, `last_sent_at`, `resolved_at`, `repeat_count`, notification IDs, recent message IDs and the latest sanitized alert snapshot per incident.
- On first production run, seed a baseline at the maximum current ID and do not replay historical alerts or create incidents from history.
- Persist an outbox/pending intent before delivery. After every delivered message, persist its Discord message ID.
- On restart, GET and verify already delivered messages, then resume only missing messages.
- Advance `last_seen_id` and clear pending only after every message passes readback.
- State file mode must be `0600`; do not chmod the shared `data/` directory.

## Schedule and validation

- Canonical cadence: `12,27,42,57 * * * *` with `flock -n` and durable `/root/.local/share/mgs/sb-venv/bin/python` under `xvfb-run -a`.
- Daily channel retention runs at `5 0 * * *` in the host timezone `America/New_York` with a separate `flock` and `--cleanup-old-messages --apply`.
- Retention keeps the current ET calendar day plus the complete previous ET calendar day. It deletes only messages whose embed title normalizes to `Token Messenger inválido` and whose Discord timestamp is before yesterday at `00:00 ET`; unrelated/manual messages are preserved.
- Retention must paginate the full channel, preflight exact IDs, delete sequentially with about 0.45 seconds between requests, honor numeric `retry_after + 0.25s` for up to eight attempts, and repaginate after deletion. Success requires zero eligible messages remaining.
- Retention status is stored independently under `state.retention`; normal monitor success must not erase its failure counter. After three consecutive retention failures, alert Rodolfo in `#alerts-infra` with the exact blocker.
- Stale-log watchdog tolerance: 75 minutes for the explicit 15-minute list.
- Validate with `py_compile`, unit fixtures, mocked Discord POST/GET/reaction/retention handling, live retention dry-run, live retention no-op apply and one authorized canary when delivery itself changes.
- Production channel reset validated 2026-08-26: six current incidents resent as initial alerts (`1542366078020222997` through `1542366086966804523`), all with both role mentions, exact embed readback, `repeat_count=0`, six active incidents and `pending=null`.
