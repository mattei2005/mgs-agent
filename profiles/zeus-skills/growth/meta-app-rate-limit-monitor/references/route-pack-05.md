## Production Cron Implementation

Active Hermes cron job:

```text
Job name       meta-app-roles-watch
Job ID         0cc7ed1e587e
Schedule       */3 0,8-23 * * *  (a cada 3 minutos, das 08:00 até 00:59 ET; sem execução entre 01:00 e 07:59)
Mode           no_agent script, deliver=local (silent on OK)
Script         /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh
Lock           /var/lock/meta-app-roles-watch.lock (skip if previous run still active)
Stagger        4 segundos adicionais entre B001-B010, configurável por MGS_META_APP_ROLE_STAGGER_SECONDS
Scope          B001-B010 + B005-2 role/admin monitoring only. B013 is excluded from this script’s /roles alert path and handled by b013-dtr-link-watch.
Channels       B001 1521251196294135858; B002 1521251220130496723; B003 1521251246860931223; B004 1521251334496456815; B005-2 1521251961662341160; B006-2 1521252068319297666; B007 1520510823426949313; B008 1521252172929564744; B009 1521252284623884288; B010 1521252369331916902
```

Use the Meta roles cron for B001–B010/B005-2. B013 remains in the 11-channel operating plan, but uses a separate slower route because its users are fetched through DTR/ChatPion + Meta `debug_token`, not `/app/roles`.

Operational close-loop rule for transient Meta API checks: an isolated `user_token_me` HTTP 500/502/503/504 while `app_metadata`, `roles`, and `debug_token` are OK is not enough to classify the app as disconnected. Alert it as `ATENÇÃO` / Meta Graph instability, persist a concrete `last_check_incident_at`/`last_check_incident_kind`, then on the next healthy cycle post `Meta App Health Recuperado — Bxxx` in the same app channel with `RECUPERADO`, checks OK, and `Nenhuma ação operacional necessária pela Ially`. Persist `last_check_recovered_at` so the recovery notice is sent once per incident. Do **not** trigger recovery from historical `alerts.checks.critical` timestamps alone; old alert state without a matching `last_check_incident_at` is not an open incident. Manual operator close-loop after Rodolfo validates an app can use `MGS_META_APP_ROLES_FORCE_RECOVERY_NOTICE=1` with `MGS_META_APP_ROLE_ITEMS='BOT Bxxx Token'`.

### Temporary app-scoped notification pause

When Rodolfo asks to pause only the app channels currently notifying him, do not pause the whole `meta-app-roles-watch` cron if unaffected apps must remain monitored. Write `/root/mgs-agent/data/meta-app-role-alert-pause.json` with the exact app keys and an aware ISO `until` timestamp in `America/New_York`. The production script keeps Graph/Sheet checks and state reconciliation running, suppresses only app-channel Discord delivery for those keys, preserves pre-pause cooldown timestamps, and automatically ignores the pause when `now >= until`; no resume job or gateway restart is needed. Infra/Sheets failure alerts remain independent and are not suppressed by an app-channel pause.

Required validation: JSON parse, shell + inline-Python syntax, isolated `post_webhook` gate test proving HTTP delivery is bypassed for one paused app, production state readback showing the exact active app set and expiry, and Discord readback showing no new message in a paused channel. Inventory, audit, backup, and REPORT-INFRA remain mandatory because this touches profile script/data/skill infrastructure.

Active B013 Hermes cron job:

```text
Job name       b013-dtr-link-watch
Job ID         498fb0d95e10
Schedule       2-59/9 0,8-23 * * *  (aprox. a cada 9 minutos, offset de 2 minutos para não iniciar junto com o Meta; das 08:00 até 00:59 ET)
Mode           no_agent script, deliver=local (silent on OK)
Script         /root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh
Lock           /var/lock/b013-dtr-link-watch.lock (skip if previous run still active)
Runtime        Último observado ~6m; manter o `flock` não bloqueante para impedir sobreposição.
```

Important UX correction: if Rodolfo explicitly says **"manda um alerta no canal Bxxx"** or **"ativa o cron e faz ele mandar um alerta"** for B001–B010/B005-2, use `MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1` with `MGS_META_APP_ROLE_ITEMS='BOT Bxxx Token'`. This forces the same polished 3-message app-roles layout with the current users list: (1) native embed `Meta APP - Bxxx`, (2) `👥 USUÁRIOS ATUAIS` code block, (3) removidos/adicionados/acumulados code block. It uses live Meta Graph + live sheet reconciliation and must not display cached state deltas: forced live alerts show `REMOVIDOS AGORA`/`ADICIONADOS AGORA` as empty unless the same fresh run proves otherwise, and `REMOVIDOS ACUMULADOS` must come from the live sheet X/reconciliation layer, not `state.cumulative_removed`. It does not enable snapshot mode, does not forge a delta, and does not corrupt state. Do **not** hand-build a generic embed. A force-live run must suppress the automatic state-delta alert for that same app/run; otherwise one operator request can emit both alert families, duplicate the message and burst the Discord rate limit. Direct Discord posts must catch HTTP 429, honor `retry_after`/rate-limit headers, and retry with a bounded attempt count before failing closed. Split tables may make the final layout exceed three physical messages; delivery completeness and readback are mandatory.

For B013 alert validation, never use `meta-app-roles-watch.sh`; use:

```bash
MGS_B013_DTR_FORCE_LIVE_ALERT=1 /root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh
```

If the same B013 run detects material link changes and `FORCE_LIVE_ALERT=1`, the automatic fresh change alert is the single canonical delivery: it already contains current users, added/removed transitions, confirmed removals and unknowns. Suppress the second force-snapshot family for that run, but keep the embed description as `Alerta live solicitado` because the operator initiated the run. A manual force with no material change still sends one fresh snapshot. After any delivery bug, keep the accurate change alert, delete only the duplicate snapshot messages, verify readback and persist `alerts_sent=1`.

B013 summary cards must visually follow the accepted B010 native embed: title `Meta APP - B013`, one concise live-data description, yellow `ATENÇÃO` only when pending profiles exist, and compact inline fields in this order: `ESTADO`, `CONTAGEM`, `PENDENTES`, `PÁGINAS`, `DTR`, `META`. Keep DTR/Graph diagnostics out of the prose. The three-message layout remains: native summary embed, complete current-user table, then movements/confirmed removals. A force-live snapshot must not replay cached additions; show `ADICIONADOS AGORA` as `Nenhum.` unless that same fresh run proves a real addition. Omit the entire inconclusive section when there are no inconclusive profiles.

For “todos os 11 canais”, validate the operational set as: B001, B002, B003, B004, B005-2, B006-2, B007, B008, B009, B010, B013. B013 routes to `#b013-app-status` / `1522830283240505385`; there must be no stale alternate runtime state, script, sheet label, or alert title.

On 2026-08-06 Rodolfo retired B012 after the Meta app became inactive and activated B013 as the DTR/ChatPion replacement. The existing Discord channel retained ID `1522830283240505385` and was renamed to `#b013-app-status`. The current `BOT B013 Token` item reuses the immutable production item ID previously pinned by the B012 monitor; the old B012 runtime therefore had to be paused before cutover to prevent it from evaluating B012 rows with B013 credentials. The separate `BOT B013` reserve item remains non-operational. Production pins the unique current `BOT B013 Token` item by immutable ID and fails closed on title/identity drift. B013 is one of the 11 operational channels, not a reserve or a `/roles` app.

Hard guard implemented in `meta-app-roles-watch.sh`: `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` alone is ignored/blocked. Snapshot only becomes effective if `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT` is also set. This prevents accidental manual resend with snapshot after Rodolfo asks for a real alert.

The production monitor cadence is:

> Supersessão explícita de Rodolfo em 2026-07-31: a cadência horária de 2026-07-10 foi substituída. B001-B010 agora executam a cada 3 minutos entre 08:00 e 00:59 ET, com stagger interno padrão de 4 segundos entre apps. B013 executa aproximadamente a cada 9 minutos na mesma janela, com offset de 2 minutos e `flock` não bloqueante. Não executar entre 01:00 e 07:59 ET. A regra anterior de Meta em `:04` e B013 em `:24` fica preservada apenas como histórico supersedido.

```text
Failure mode                         Alert SLA
-----------------------------------  -----------------------------------------
Segurador/admin removed from roles   B001-B010/B005-2: próximo ciclo de 3 minutos entre 08:00 e 00:59 ET
Segurador/admin added to roles       B001-B010/B005-2: próximo ciclo de 3 minutos entre 08:00 e 00:59 ET
B013 DTR/ChatPion link removed       próximo ciclo aproximado de 9 minutos entre 08:00 e 00:59 ET
X-App-Usage >=70%                    alert on severity increase
X-App-Usage >=85%                    risk alert; for B007/Openzed act fast
X-App-Usage >=95%                    critical alert; repeat after cooldown
App/token/debug check failure        critical alert; indicates app/token/access break
Script/Graph repeated error          alert after 2 consecutive failures
```

State file tracks:

```text
app_name
app_id
roles / roles_count
previous_count / current_count
last_removed / last_added / cumulative_removed
checks.app_metadata / roles / user_token_me / debug_token
usage.raw / parsed / max_pct / max_metric / severity
x_app_usage
consecutive_errors
alerts cooldown timestamps
token_info.valid / scopes / expires_at / type
_sheet_removed_sync / _last_run_summary.sheet_removed_sync
```

Google Sheet sync:

```text
Sheet        Migracao 22/06 (gid 542936436)
Assignment   N / APP PROVISORIO — current app routing source. M / NO APP is historical and must not drive any active monitor.
Marker       A / Removidos acumulado
Behavior     Full reconciliation every run: rows with APP PROVISORIO + Segurador/USUARIO that are absent from current Meta /roles get X; rows present in Meta roles are cleared. Non-app operational notes in N are preserved as unknown/unassigned and never coerced into an app. cumulative_removed is context/history, not the primary source for X. A confirmed migration set may supply names only while its exact app-scoped role-ID set is unchanged; any ID drift preserves existing markers and fails closed.
Auth         Canonical Service Account only for every read/write: item `Google Service Account - MGS Agent`, project `mgs-core-prod`. Public CSV export and personal OAuth fallback are retired.
Write policy Read the tab once through Sheets API, update A2:A{last_row} only when desired values differ, then update the in-run cache and verify by Service Account readback.
Alerting     Sheet read/write failure is CRITICAL: send Discord alert with Rodolfo mention, sheet ID, GID, auth mode, sanitized error, and cooldown. Do not only store `_sheet_removed_sync.error` in state.
```

If Google auth fails for this cron, validate the canonical Service Account item, `roles/serviceusage.serviceUsageConsumer`, Sheets metadata, sentinel write/readback/restore and `_sheet_removed_sync`. Do not recreate the retired Ares OAuth files.

Implementation rules:

```text
- Empty output is success/silent; no_agent cron sends nothing on OK.
- Do not use cronjob Discord delivery for final alerts; post direct Discord bot messages to the app-specific channel mapping. Fallback webhook is legacy only.
- Auto-discover 1Password items matching BOT Bxxx Token when MGS_META_APP_ROLE_ITEMS is unset.
- Use the 1Password item code (B001/B002/etc.) as the state key; do not trust copied/stale app_name fields. Replacement apps may be named with a suffix like `BOT B005-2 Token`; keep the replacement label visible in alert titles/`App` field/state (`B005-2`), while mapping it to the same operational Discord channel (`#b005-app-rate-limit`). Do not silently display it as `B005`.
- B013 is the current canonical app name. Use the unique current `BOT B013 Token` item pinned by immutable ID, `APP PROVISORIO = B013`, `b013-dtr-link-watch.sh`, and state `/root/mgs-agent/data/b013-dtr-link-monitor-state.json`. The script must additionally fail closed unless the item still declares `app_name = B013` and the canonical alert channel ID; immutable-ID pinning alone is insufficient when a replacement reuses the same 1Password item. `BOT B013` is the retired reserve; all B011/B012 runtimes are non-operational and must remain excluded from generic `/roles` and Sheet reconciliation.
- For Rodolfo requests like “manda alerta real em todos os 11 canais”, scope means exactly `B001`, `B013`, `B002`, `B003`, `B004`, `B005-2`, `B006-2`, `B007`, `B008`, `B009`, `B010`. B013 must route through the DTR monitor, never the Meta `/roles` monitor.
- Sheet `APP PROVISORIO` parsing must preserve alpha suffixes such as `B013`; do not normalize `B013` to `B001`. Hyphen suffixes such as `B005-2` must also remain intact.
- B013 is an Advanced Access + ChatPion connection app: seguradores are not expected to be app roles/admins. Do not mark B013 sheet rows as removed based on `/roles`; preserve them in `ROLE_RECONCILIATION_EXCLUDED_APPS`. The separate DTR page-token monitor owns B013 reconciliation.
- The default B013 source set is every Sheet row with `APP PROVISORIO = B013`, including rows already marked `X`; each row must remain monitored so a valid reconnection clears `X` automatically. `Migracao` is informational unless Rodolfo explicitly requests a filtered audit.
- B013 target-set changes are material events: in an initialized state, a new `APP PROVISORIO = B013` identity with no prior account state must alert immediately as `kind=added`, even when its first validation is unknown. An identity that disappears from the current B013 target set must alert as `kind=removed`; remove that stale baseline entry so a future reassignment alerts again as a new addition. Never silently absorb a new B013 target into the baseline. Validate both branches with an isolated state fixture; replay a confirmed missed event from a temporary state path so the canonical production state remains untouched.
- Before classifying a B013 target as `missing_dtr_1p_item`, confirm a metadata-cache miss with exactly one forced live refresh of the canonical 1Password DTR item index. Keep the normal metadata cache for healthy hits; never treat a stale cache miss as proof that the credential is absent.
- Persistent B013 unknown alerts use a material signature containing affected identities and failure kinds. Alert immediately when that signature changes, repeat an unchanged incident only after the default 6-hour cooldown, and clear the alert state silently after recovery so a later new incident alerts immediately. The cron cadence must never imply a per-cycle repeat cooldown.
- B013 `debug_token` classification is evidence-based: HTTP 200 with `is_valid=true` and matching `app_id` is linked; HTTP 200 invalid/mismatched data is confirmed unlinked. Meta OAuth code 100 with the explicit `App_id in the input_token did not match the Viewing App` message is also confirmed unlinked as `token_app_mismatch`. Invalid-signature/code 190, 5xx and ambiguous transport failures remain `unknown` and preserve the Sheet marker fail-closed.
- Alert message fields must show current app users, one-cycle removed/added deltas, and owner/admin profile; display `administrators` as `Admin`.
- If a previously removed profile is added/current again, remove it from `Removidos acumulados` before sending the alert. Match using a composed identity, not only the raw Meta `/roles.user` ID: Meta ID + normalized `Segurador` name + sheet `PERFIL ID` (`USUARIO`). A user must never appear in both `Usuários adicionados` and `Removidos acumulados` in the same alert.
- For user/admin role lists, do **not** put wide tables inside Discord embed fields; mobile/Discord truncates and makes them illegible. Preferred alert UX is: short real Discord embed for summary (`Meta APP - Bxxx`, Estado/Contagem/Admin/Uso) plus normal message(s) containing monospaced tables.
- Snapshot alerts and automatic role-change alerts must use the SAME 3-message Discord format: (1) short embed `Meta APP - Bxxx` with only Estado/Contagem/Admin/Uso, unchanged from the original Discord embed/card layout; (2) normal message code block for current users, styled with Unicode heavy line separators `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━` around the heading `👥 USUÁRIOS ATUAIS`; (3) separate normal message code block containing only `➖ USUÁRIOS REMOVIDOS AGORA`, `🆕 USUÁRIOS ADICIONADOS AGORA`, and `📦 REMOVIDOS ACUMULADOS`, each styled with the same `━` separator lines. Do not put role lists inside embed fields; do not include the old `Movimentações - Bxxx` / `Ordenado por BOT EMAIL` headings in the second block; do not use `=` separators for this alert family.
- Visual presentation rule for the 3-message app roles alert: the Discord embed/card must remain 100% native/unchanged; the first `Usuários Atuais:` code block must also remain unchanged. Apply visual styling only to the third movement/removals code block, using heavy Unicode line separators `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━` above and below each section title plus section emojis, e.g. `➖ USUÁRIOS REMOVIDOS AGORA`, `🆕 USUÁRIOS ADICIONADOS AGORA`, `📦 REMOVIDOS ACUMULADOS`. Do not replace the native embed with text, do not restyle the first users block, and do not use `=`/dashed/punctuated separators when Rodolfo asks for the pages-restritas-style straight line.
- Resolve `/roles.user` identities with bounded Graph multi-ID chunks of at most 50 IDs, never one request per role. One chunk is used for up to 50 roles; B005-2 at 100 roles uses two chunks. Store `requested/resolved/unresolved`, chunk count and statuses. A single 100-ID query is invalid in production because Meta returns HTTP 400 and the alert degrades to numeric IDs/`sem email`. Per-role N+1 resolution is also forbidden because it can consume app quota.
- If every role identity remains unresolved after bounded chunk retries/fallback, set `role_identity_reconciliation.safe_for_sheet=false` and preserve existing Sheet markers. Never convert an all-numeric identity failure into a mass-removal write.
- A Rodolfo-confirmed predecessor→replacement migration may use a set-level identity baseline only when the exact current app-scoped role-ID set equals the confirmed set. Keep raw Graph roles in state, use the confirmed names only for operational display/Sheet reconciliation, and fail closed without Sheet writes on any role-ID drift.
- Role/current-user table columns are standardized across the **11-app operational set** as `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS`. Do not use `STATUS` in B013 current-user tables, and do not omit `PÁGINAS` from B001–B010/B005-2. `BOT EMAIL` comes from Google Sheet tab `Migracao 22/06`, column A / `User`; `PERFIL ID` comes from column K / `USUARIO`; `PÁGINAS` comes from column E / `PG`. Match by `Segurador` name. Prefer sheet `USUARIO`, but if a current Meta role does not match the sheet, display the Meta `/roles.user` ID as fallback instead of `sem ID` so the row remains actionable. Sort rows alphabetically by full `BOT EMAIL` so entries group by site/bot user, but display only the local part before `@` for the entire operational set (e.g. `disparosopenzed@gmail.com` → `disparosopenzed`). Rodolfo explicitly confirmed the domain is irrelevant in B013 too.
- B013 `📦 REMOVIDOS ACUMULADOS` must **not** include `MOTIVO`. If the user appears in accumulated removals, the operational state is already clear: profile/link is off/disconnected. Use the same compact schema `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS` there as well; avoid reason/error text in the manager-facing accumulated list unless Rodolfo explicitly asks for diagnostics.
- Current-user lists must never hide rows with suffixes like `... +N outros`. For B001–B010/B005-2, render every current Meta `/roles` user and split the monospaced table across multiple Discord-safe messages when it exceeds 2000 chars. For B013, `👥 USUÁRIOS ATUAIS` must render only currently linked DTR/ChatPion accounts; disconnected/X profiles must appear only under `📦 REMOVIDOS ACUMULADOS`, never duplicated above as `PENDENTE`. This applies to snapshot/manual live alerts and automatic role-change alerts. See `references/app-rate-limit-alert-schema-standardization-2026-07-06.md` for the session correction and validation pattern.
- If `OBS` contains `Perfil antigo: <name>` for the same `APP PROVISORIO`, suppress/remove that old profile name from `Removidos acumulados`; planned developer/profile migrations are housekeeping, not active incidents.
- If a profile/segurador in `Removidos acumulados` has been reassigned in the sheet to a different `APP PROVISORIO` (example: B003 → B013), remove it from the old app’s accumulated removals. Accumulated removals are active incidents only while the sheet still says that user belongs to that app.
- If historical `cumulative_removed` cache becomes polluted across apps, do not reset roles/current snapshots. Backup `/root/mgs-agent/data/meta-app-role-monitor-state.json`, clear only `last_removed`, `last_added`, and `cumulative_removed` for each app, then run `meta-app-roles-watch.sh` once live. This preserves current role baselines while letting full sheet reconciliation keep/write X based on current Meta vs sheet truth.
- Owner-profile housekeeping is not a segurador incident. If Rodolfo confirms an app owner profile was disabled/replaced, update both `APP_OWNER_PROFILES` and the skill owner list, add the old owner to `APP_RETIRED_OWNER_PROFILES_BY_APP`, and suppress that retired owner from `last_removed`/`cumulative_removed`. If a profile is removed from another app because it became owner of a different app (example: Dek Fiyan removed from B004 after becoming B007 owner), suppress that removal from B004 role-change alerts too.
- Role-change/snapshot alerts must be sent only after both passes complete: (1) Meta API snapshot for all apps, then (2) Google Sheet reconciliation/sync using `APP PROVISORIO`, `USUARIO`, `Segurador`, and `OBS`. Rate-limit/token/API-health alerts can still be evaluated from API immediately because they do not depend on the migration sheet. This avoids false-positive role alerts when Ially has already documented a planned migration in the sheet.
- Do not post broad Zeus internal status/correction messages in the B001–B010 app-rate-limit channels. Those channels are for app-specific manager alerts only: role added/removed, app/token/API failure, or rate-limit action. Keep REPORT-INFRA/reconciliation explanations in Zeus/#alerts-infra unless Rodolfo explicitly approves manager-facing wording.
- Messenger page health monitoring is a separate next layer: use segurador tokens for page accessibility/conversations and SB/ChatPion for sends, delivered, subscribers/leads.
- Never print access_token, app_secret, page token, or authorization code.
- Credential checks through 1Password must use 4-attempt confirmation before alerting: a single failed/empty `op` read is not proof that the credential is missing. Retry reads up to four total attempts; alert/report only if the 4th consecutive attempt still fails or returns empty. This applies to all credential fields monitored by scripts, not just Meta app access tokens.
- Persist state before declaring success; state is the anti-duplicate source.
```

Discord alert destinations for app-rate-limit alerts:

```text
B001  #b001-app-rate-limit  1521251196294135858
B013  #b013-app-status      1522830283240505385
B002  #b002-app-rate-limit   1521251220130496723
B003  #b003-app-rate-limit  1521251246860931223
B004  #b004-app-rate-limit  1521251334496456815
B005-2  #b005-app-rate-limit  1521251961662341160
B006-2  #b006-app-rate-limit  1521252068319297666
B007  #b007-app-rate-limit  1520510823426949313
B008  #b008-app-rate-limit  1521252172929564744
B009  #b009-app-rate-limit  1521252284623884288
B010  #b010-app-rate-limit  1521252369331916902
```

When Rodolfo asks to add humans to these channels, resolve their Discord IDs via guild member search and set explicit user permission overwrites on all 11 channels. Known validated IDs:

```text
Geizian  321263240782807040
Ially    1415413060197290084
```

Minimum access overwrite for monitoring channels:

```text
VIEW_CHANNEL + SEND_MESSAGES + READ_MESSAGE_HISTORY = allow 68608
```

Use Discord API `PUT /channels/{channel_id}/permissions/{user_id}` with payload `{type:1, allow:"68608", deny:"0"}`, verify the overwrite exists on each channel, and append an audit entry to `/root/mgs-agent/logs/events-audit.jsonl`. Do not alter agent authorization registries for simple channel visibility unless Rodolfo specifically asks for executable agent access.

Operational app-rate-limit alerts must **not** go to `#alerts-infra`. Keep `#alerts-infra` only for REPORT-INFRA/inventory changes when creating/modifying skills/scripts/crons/config.

When this monitor script, its skill, cron, config, or inventory is modified, send the `[REPORT-INFRA]` to `#alerts-infra` as its own operational report; do not leave the REPORT-INFRA block only inside the working/user thread. Rodolfo explicitly corrected this during the B001–B010 rollout.

For final production presentation, do **not** use `cronjob(deliver=discord:...)`: it adds `Cronjob Response`, `job_id`, and job-management footer text. Use a direct Discord webhook POST from the monitor script so the message is clean and human-readable.

Webhook standard:

```text
1Password item: Discord Webhook - app-rate-limit
Field:          webhook_url
Expected GET:   channel_id=1520510823426949313, name=app-rate-limit
Expected POST:  HTTP 204
```

If an alert requires push notification, the content should mention Rodolfo at the top:

```text
<@344196393512075265>

Meta App Rate Limit — B007/Openzed
...
```

Use aligned compact sections (`Resumo`, `Checks`, `Ação`) instead of raw JSON or prose. See `references/discord-webhook-alert-format.md` for the accepted format and webhook delivery pattern.

