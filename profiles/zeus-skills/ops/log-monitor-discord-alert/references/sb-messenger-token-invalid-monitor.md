# Smart Bidding Messenger invalid-token monitor

Use this procedure when MGS needs to mirror Smart Bidding alerts titled `Messenger user token invalid` into a dedicated Discord channel.

## Source and scope

- Authenticated read-only source: `GET https://api.jbfdigital.com.br/notification`.
- Filter exactly `COMPANY in {digital-trust, digital-trust-2}` and `TITLE == Messenger user token invalid`.
- Parse `BODY` only as a JSON list. Fail closed on malformed or empty bodies.
- The body provides `user_id`, `user_name`, `user_email`, `segurador_id`, `segurador_name` and `source` (`page_token` or `canary`).
- Never read, persist, print or validate the underlying Facebook tokens.

## Post-remediation connection audit — live Page-ID rule

When Rodolfo says he removed, replaced, reconnected or deduplicated the alerted profiles and asks for a fresh status, the Discord alert/state is only the audit population. It is not current connection proof.

- Do not use the monitor state, prior report JSON, cached page counts, Discord embed, replacement account under the same login, or a saved snapshot to classify the alerted segurador.
- Fetch all three surfaces fresh in the same run: current channel alerts for scope, DigitalTRChat live account/Page inventory, and Smart Bidding live `/users/Messenger` plus `/campaigns/Messenger`.
- In Smart Bidding, explicitly select/query **both** company scopes `digital-trust` and `digital-trust-2`, expand all of their publisher IDs, and fail closed unless both are present. Do not accept whatever company checkboxes happened to remain selected in a saved UI session.
- In DigitalTRChat, match the exact `LOGIN + segurador/account name` after Unicode normalization, deduplicate `.account_switch` by immutable `data-id`, switch that ID, and prove the active context. A visible and hidden responsive entry with the same ID is one account, not a duplicate. Only the same normalized name on distinct account IDs is a real DTR duplicate.
- Enumerate every live DTR Page with both identifiers. The Bot List exposes `.page_list_item .fb_page_id` as `#<PAGE_ID pequeno> - <FB_PAGE_ID grande>` and remains usable when a Page has no Completed campaign report.
- For each DTR Page, search the complete live SB Page scope globally by exact `PAGE_ID` **or** exact `FB_PAGE_ID`. Either identifier is sufficient for presence; when both exist they must resolve to the same unique SB row. `LOGIN`, `USER_LOGIN`, `PROFILE_NAME`, Messenger User linkage and `ACTIVE` remain diagnostics, not the presence gate. A null/wrong `PROFILE_NAME` must not turn an existing Page into `PENDENTE_SEM_SB`.
- Classify results as: `OK` when every live DTR Page is found uniquely by small or large ID; `REMOVIDO` when the exact DTR account is absent and no exact residual SB profile row exists; `PENDENTE_SEM_SB` when none of the live DTR Page IDs exists in SB; `PENDENTE_SB_RESIDUAL`; `PENDENTE_DIVERGENCIA_PAGINAS`; or a distinct-ID/duplicate/error state. Report association/User problems separately from Page presence.
- Correction validated 2026-09-03: with both companies selected and both IDs read live, Ione Silva is `23/23`, Michelle Ferreira `4/4`, and Semakin Sadar `23/23`; the earlier `0` counts came from treating `PROFILE_NAME` as the Page-presence gate.
- A ✅ reaction remains the human lifecycle signal, but it is not live health proof. Do not declare the remediation complete while the live Page-ID audit still has a pending state.
- Persist only sanitized IDs/counts/statuses and provenance. Never persist credentials or token values.

## Page-count enrichment

1. Open the canonical headed/Xvfb Smart Bidding session and capture only the dashboard authorization header in memory.
2. Read `/users/Messenger` for `digital-trust` and `digital-trust-2`.
3. Map each alert to the SB Messenger user inside the exact `COMPANY + PUBLISHER_ID` scope. Match `LOGIN == user_email` first; only if there is no unique email match, fall back to a unique `NAME == user_name`. Never combine email and name candidates with one OR because duplicated display names can make an otherwise exact email match look ambiguous. The numeric `user_id` inside the notification body is not the UUID used by campaign rows.
4. Read `/company`, collect active `publisherId` values, then read `/campaigns/Messenger` for the complete publisher scope.
5. Count campaign rows by the matched user UUID in `MESSENGER_USER_ID` and aggregate the same rows by `STATUS`. Normalize known statuses to `Broadcast`, `On-hold`, `Blocked`, `Ready` and `Campaign`; preserve any unknown non-empty status and label blanks as `Sem status`. The status counts must sum exactly to the total or rendering fails closed. If the user cannot be mapped uniquely, render `Total —` and `Status —` instead of inventing a count.
6. Persist only the total and aggregate status counts, not campaign rows or password/token fields.

## Delivery contract

- Dedicated channel: `#seguradores-token-fb` (`1521350832426188961`).
- Zeus bot transport; exactly one Discord message and one embed per affected Messenger user so a ✅ reaction resolves one incident only.
- Every initial/new-incident and ET-date-rollover delivery mentions both team roles once: Gestor de Trafego (`1496256346994249912`) and Admin (`1496260941787168848`). Set `allowed_mentions.parse=[]` and explicitly list only those two role IDs.
- Keep the embed compact: put the uppercased site/domain first in the title (`SITE — Token Messenger inválido`).
- Show only three fields: `User`, `Segurador` and `Páginas`. Keep `Páginas` full-width with exactly two compact lines: `Total N`, then `N Broadcast + N On-hold + N Blocked + N Ready + N Campaign`, omitting zero statuses and placing unknown statuses after the known operational order. Do not add explanatory description, company, visible source or a separate detection-time field.
- Keep the short content line `<roles> · Reaja ✅ quando resolver.` and compact footer/timestamp metadata for audit and dedupe.
- Canary titles start with `CANÁRIO`. Production alerts always use the unbadged `SITE — Token Messenger inválido` form.
- Never emit numbered or three-hour reminders. The same stable incident can appear at most once per ET calendar day.
- After POST, GET the exact message and verify target channel, exact content, title, color, footer, fields, one embed and both `mention_roles` IDs.

## State, resolution and idempotency

- Deduplicate source processing by numeric SB notification ID and delivery by stable incident key `company + domain + user_id + segurador_id`.
- A ✅ reaction on the latest Discord message is the explicit resolution signal. At ET rollover and when a newer source notification arrives, read the latest message before deciding whether the lifecycle remains active.
- On the first monitor run after an ET date rollover, send exactly one fresh, unbadged message for every still-active incident. Store the ET date and a resumable daily outbox before delivery so a crash cannot create an uncontrolled duplicate batch.
- During the same ET day, a newer SB notification for an already-active stable key is suppressed from Discord but updates the incident's latest sanitized snapshot and notification-ID history. A genuinely new key is delivered once.
- After ✅, a later SB notification with the same stable key opens a new lifecycle with `repeat_count=0`; the prior acknowledgement never becomes a permanent ignore.
- Keep `opened_at`, `last_sent_at`, `resolved_at`, notification IDs, recent message IDs and the latest sanitized alert snapshot per incident. `repeat_count` remains zero under the daily-only policy.
- On first production run, seed a baseline at the maximum current ID and do not replay historical alerts or create incidents from history.
- Persist an outbox/pending intent before delivery. After every delivered message, persist its Discord message ID.
- On restart, GET and verify already delivered messages, then resume only missing messages.
- Advance `last_seen_id` and clear pending only after every message passes readback.
- State file mode must be `0600`; do not chmod the shared `data/` directory.

## Schedule and validation

- Canonical monitor cadence: `12,27,42,57 * * * *` with `flock -n` and durable `/root/.local/share/mgs/sb-venv/bin/python` under `xvfb-run -a`. The `00:12 ET` run is the normal first daily sweep: it resends each still-active incident once; later runs that day emit only genuinely new/reopened incident keys.
- Daily channel retention runs at `5 0 * * *` in the host timezone `America/New_York` with a separate `flock` and `--cleanup-old-messages --apply`.
- Retention keeps the current ET calendar day plus the complete previous ET calendar day. It deletes only messages whose embed title normalizes to `Token Messenger inválido` and whose Discord timestamp is before yesterday at `00:00 ET`; unrelated/manual messages are preserved. Example: messages from day 29 remain through day 30 and are deleted at `00:05 ET` on day 31.
- Retention must paginate the full channel, preflight exact IDs, delete sequentially with about 0.45 seconds between requests, honor numeric `retry_after + 0.25s` for up to eight attempts, and repaginate after deletion. Success requires zero eligible messages remaining.
- Retention status is stored independently under `state.retention`; normal monitor success must not erase its failure counter. After three consecutive retention failures, alert Rodolfo in `#alerts-infra` with the exact blocker.
- Stale-log watchdog tolerance: 75 minutes for the explicit 15-minute list.
- Validate with `py_compile`, unit fixtures, mocked Discord POST/GET/reaction/retention handling, live retention dry-run, live retention no-op apply and one authorized canary when delivery itself changes.
- Production channel reset validated 2026-08-26: six current incidents resent as initial alerts (`1542366078020222997` through `1542366086966804523`), all with both role mentions, exact embed readback, `repeat_count=0`, six active incidents and `pending=null`.
