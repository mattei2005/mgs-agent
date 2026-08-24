## Production Cron Implementation

### Current B007-2 cutover — 2026-08-24

Rodolfo explicitly replaced B007 with B007-2, updated the existing 1Password item and asked Zeus to re-enable the generic monitor, reconcile the canonical Sheet and send one real live alert to the existing B007 channel.

- Current app key: `B007-2`; predecessor `B007` is retired from the active registry.
- Current item: `BOT B007-2 Token - Alex Silva Araujo`; its `app_name` metadata must be `B007-2`. Required `app_id`, `access_token` and `app_secret` stay secret and must only be validated for presence/readability.
- Existing channel remains `1520510823426949313` (`b007-app-status`); manager-facing alerts must display `Meta APP - B007-2`.
- Fresh preflight proved app metadata, `/roles`, `/me` and `debug_token` HTTP 200; the user token is valid and app-bound; all 18 roles resolve to names and the live token profile is Alex Silva Araujo.
- The canonical Sheet already uses `NO APP = B007-2`: 19 rows total, 18 current Meta roles present and `An Na` intentionally preserved as the single `X`/removed row. Store `expected_sheet_roles=18`, not 19, because the marked removed row is not a pending role acceptance.
- Production must not reuse either the retired B007 state or the older stale B007-2 state whose app-scoped role IDs belong to a different historical app ID. Back up state, clear both keys under the monitor lock, baseline B007-2 while its app-channel delivery is contained, require 18 roles, `safe_for_sheet=true`, 18 present, one marked, zero writes when already reconciled, zero errors and zero Discord messages.
- After the baseline passes, clear the manual app pause and run `MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1` with the exact current item. Require the canonical native embed plus complete current-user and movement blocks, then verify every physical Discord message by channel readback.
- Hermes cron job `0cc7ed1e587e` remains the shared registry-driven `meta-app-roles-watch`; do not pause it globally. After cutover, B007-2 is unpaused while unaffected apps continue normally.
- Hermes non-TTY pitfall: `op item edit` can consume the gateway pipe as JSON and fail with `invalid JSON provided`. For a user-authorized non-secret metadata correction, execute the exact field assignment in a real PTY, suppress command output, then read back only the intended non-secret field and credential-presence booleans. Never print token/secret values.

### Current B013-3 cutover — 2026-08-21

Rodolfo explicitly replaced `B013-2` with `B013-3`, updated the exact 1Password item and authorized the dedicated DTR/ChatPion monitor, cron activation and a real alert after preflight.

- Current item: `BOT B013-3 Token - PERFIL NOVO - 192`; required fields present, `app_name=B013-3`, and alert channel ID `1522830283240505385`.
- App metadata, `/me`, `debug_token` and `/roles` return HTTP 200; the user token is valid and app-bound; three app roles are visible.
- The canonical Sheet uses `NO APP = B013-3`. The target set advanced from 30 rows during preflight to 31 rows at production cutover; always reload the Sheet immediately before classification.
- Full read-only preflight after the token correction proved 30/30 linked, zero confirmed unlinked, zero unknown, 301 DTR pages, 293 Graph pages and 279 pages subscribed to B013-3; no Sheet write, Discord post or state persistence.
- Production later observed 31 targets because `William Nogueira` had been added to the live Sheet after preflight. The first force-live cycle saw 30 linked and William temporarily not linked; the next fresh cycle validated William as linked, converging to 31/31, zero failures/unknowns, 324 DTR pages, 316 Graph pages and 302 subscribed pages.
- The generic `/roles` monitor must exclude `B013-3` in `ACTIVE_APP_CONFIGS`, `DTR_ONLY_APP_ITEMS` and `ROLE_RECONCILIATION_EXCLUDED_APPS`. During cutover, registry activation happened before this exclusion changed and one generic cycle marked linked B013-3 rows with X. Zeus immediately patched the exclusion and the dedicated B013-3 cycle cleared all 30 incorrect markers by live readback. This containment is mandatory ordering for future replacements: patch both monitor routes before exposing the new registry key.
- Production state is freshly baselined for B013-3 after backing up the B013-2 state; never reuse predecessor link statuses as the new app baseline.
- B013-3 reuses channel ID `1522830283240505385`; the live channel name remains `b013-2-app-status` until a separate rename is authorized. Manager-facing titles must say `Meta APP - B013-3`.
- Job `498fb0d95e10` remains `b013-dtr-link-watch`, schedule `2-59/9 0,8-23 * * *`, `no_agent`, `deliver=local`. Activation requires `enabled=true`, `state=scheduled`, then one scheduled-cycle readback.
- The first scheduled B013-3 cycle failed before any DTR or Sheet write because the Sheets metadata read timed out after a single 25-second attempt. `sheets_request` now performs up to three bounded attempts for `TimeoutError`, `socket.timeout`, `URLError`, HTTP 429 and HTTP 5xx with short backoff; non-retryable HTTP errors still fail closed. Validate shell/embedded Python plus a one-target real dry-run, then require the next scheduled cycle to finish `ok` before closure.
- The alert request can legitimately produce two chronological families if the first production snapshot proves an unlinked target and a later fresh cycle proves its recovery. Do not delete either family without Critical Subset confirmation; report the final state and both exact message families.

### Current B001-3 cutover — 2026-08-21

Rodolfo explicitly replaced retired `B001-2` with `B001-3`, updated the existing 1Password item credentials and requested a live Sheet reconciliation plus a real alert. Current canonical runtime:

- app key and manager-facing alert title: `B001-3`;
- existing 1Password item title remains `BOT B001-2 Token - Adriano Alves`, but its non-secret `app_name` field is `B001-3`; resolve the exact pinned title from the registry and fail closed unless the item metadata says `B001-3`;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; the token is valid and app-bound;
- the canonical Sheet, read through the MGS Service Account, has 17 current `NO APP = B001-3` rows, no duplicate or blank segurador identity;
- the fresh app exposes 15 accepted roles and all 15 names resolve individually. `Adriano Alves` and `Alnashri Lumandung Maja` are the two Sheet assignments not yet present in current Meta `/roles`;
- store `expected_sheet_roles=17` in the registry. While accepted roles remain below 17, `safe_for_sheet=false` must preserve all 17 Sheet markers and block automatic X writes; this is pending role acceptance, not proof of removal;
- production state migrates from stale `B001-2` to `B001-3`; never reuse predecessor app-scoped role IDs as a baseline;
- B001-3 reuses channel ID `1521251196294135858`. The live channel name remains `b001-2-app-status` until a separate rename is authorized; alerts must still display `Meta APP - B001-3`;
- Rodolfo's live-alert request uses `MGS_META_APP_ROLES_FORCE_LIVE_ALERT=1` with the existing exact item title, after the production registry key is already `B001-3`. Require the standard native embed + complete current-users table + movement table, then verify all messages by Discord readback;
- recurring `meta-app-roles-watch` remains enabled. B001-3 is unpaused; the dedicated B013-3 cron is active independently.

Final closure is intentionally two-stage: the requested live alert may be sent from the accurate 15/17 state, but production Sheet reconciliation remains fail-closed until a later fresh cycle proves 17/17 accepted and resolved. Do not declare 100% correspondence before that gate passes.

### Current B004-3 cutover — 2026-08-17

Rodolfo explicitly replaced retired `B004-2` with `B004-3`, updated the current 1Password item and authorized the generic Meta roles cron to be re-enabled. Current canonical runtime:

- app key: `B004-3`;
- 1Password item: `BOT B004-3 Token - Beatriz Santos`;
- Discord channel ID remains `1521251334496456815` and the live channel was normalized from `b004-3app-status` to `b004-3-app-status`;
- live token profile/admin is `Beatriz Santos`;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; token is valid and app-bound;
- the canonical Sheet has 12 `NO APP = B004-3` assignments read through the MGS Service Account;
- initial preflight observed 5 accepted roles; before production closure all 12 expected roles were accepted and individually resolved to 12 names;
- `expected_sheet_roles=12` is stored in the canonical registry. If a future cycle returns fewer accepted roles, `safe_for_sheet=false` blocks Sheet X writes while role-change alerts and health checks continue;
- production state migrated from stale `B004-2` to `B004-3`; the generic app pause list is now empty;
- final scoped readback requires 12/12 roles resolved, four Graph checks healthy, `consecutive_errors=0`, 12/12 Sheet rows present, `identity_blocked_rows=0`, `updated=false`, `alerts_sent=0`, and `errors_count=0`.

Identity-resolution correction: Meta can return HTTP 500 for the multi-ID user-token lookup even while each individual `/{role_id}?fields=id,name` succeeds. The monitor now tries bounded multi-ID first, reuses exact same-ID names from prior state, and individually resolves only genuinely new unresolved IDs up to a hard cap of 20. This makes replacement-app onboarding self-healing without creating a per-cycle N+1 quota drain. Persist `cache_resolved_count`, individual request/resolution counts and statuses in state; when unresolved identities exceed the cap, fail closed for Sheet reconciliation.

### Current B006-3 cutover — 2026-08-17

Rodolfo explicitly replaced retired `B006-2` with `B006-3` and re-enabled this app inside the generic Meta roles cron. Current canonical runtime:

- app key: `B006-3`;
- 1Password item: `BOT B006-3 Token - Isidoro Cristina Barbosa Martins`;
- reused Discord channel ID: `1521252068319297666`; the live channel name remains `b006-2-app-status` until a separate rename is authorized;
- live token/profile and the sole accepted `administrators` role resolve to `Gia Huy`; do not infer the operational admin from the 1Password title when `/me` and `/roles` prove a different profile;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; token is valid and app-bound;
- the isolated cutover `/roles` baseline started with one accepted admin; subsequent scheduled production cycles observed additional accepted roles and delivered the corresponding additions alerts. Treat the count as live state, not as a frozen baseline;
- after all 15 expected B006-3 roles were accepted, resolve every app-scoped role ID individually with the validated user token, require 15/15 names, and freeze the exact ID-signature baseline. The generic multi-ID read can return HTTP 200 with per-ID errors under the app token or HTTP 500 under the user token even while individual reads succeed; never treat the outer multi-ID HTTP status alone as identity proof;
- the final scoped production readback must show 15 resolved names, `safe_for_sheet=true`, 15/15 assigned Sheet rows present, `identity_blocked_rows=0`, zero Sheet writes, zero alerts, and zero errors;
- the canonical Sheet, read through the MGS Service Account, has 15 `NO APP = B006-3` rows and zero writes were made during cutover validation;
- only `B004-2` remains in the manual app-alert pause; `B006-3` is unpaused;
- production state must migrate `B006-3` over stale `B006-2` and must not reuse the old B006-2 confirmed 17-role baseline because Meta role IDs are app-scoped. Build the B006-3 baseline from fresh accepted roles and alert subsequent additions/removals.

Validation pitfall: `MGS_META_APP_ROLES_DRY_RUN=1` does not persist the temporary state or print the final run summary. For an isolated end-to-end validation, use a temporary state path, disable Sheet writes, and run normal mode with `B006-3` present in a temporary manual pause file; then require all four checks healthy, `consecutive_errors=0`, a nonzero fresh `current_count`, `alerts_sent=0`, and no Discord delivery. After that gate, run the exact production item once without forcing an alert and read back production state plus the canonical pause file.

Active Hermes cron job:

```text
Job name       meta-app-roles-watch
Job ID         0cc7ed1e587e
Schedule       */3 0,8-23 * * *  (a cada 3 minutos, das 08:00 até 00:59 ET; sem execução entre 01:00 e 07:59)
Mode           no_agent script, deliver=local (silent on OK)
Script         /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh
Lock           /var/lock/meta-app-roles-watch.lock (skip if previous run still active)
Stagger        4 segundos adicionais entre B001-B010, configurável por MGS_META_APP_ROLE_STAGGER_SECONDS
Scope          Registry-driven current B001-B010 replacement lineage, including B001-3/B004-3/B005-3/B006-3. B013-3 is excluded from this script’s /roles alert path and handled by b013-dtr-link-watch.
Channels       B001-3 1521251196294135858 (live channel name still b001-2-app-status); B002-2 1521251220130496723; B003-2 1521251246860931223; B004-3 1521251334496456815; B005-3 1521251961662341160; B006-3 1521252068319297666; B007 1520510823426949313; B008-2 1521252172929564744; B009-2 1521252284623884288; B010-2 1521252369331916902
```

Use the Meta roles cron for the current registry-driven B001–B012 app lineage. B013-3 remains on the separate DTR/ChatPion route because its users are fetched through DTR/ChatPion + Meta `debug_token`, not `/app/roles`.

### Shared-admin alert policy for B001–B012 — effective 2026-08-18

Rodolfo confirmed that every segurador in B001–B012 is an app administrator, so these apps have no unique operational `admin do app`. The profile behind the monitor token remains useful credential metadata, but it is not a manager-facing owner or an app-health dependency.

- Keep `user_token_me` in state as informational diagnostics only; for B001–B012 it must not trigger `ATENÇÃO`, `CRÍTICO`, or recovery notices.
- Omit `Perfil admin do app` / `ADMIN` from rate-limit, health, recovery, snapshot, forced-live, and automatic role-change embeds for B001–B012.
- Continue alerting from actual app signals: `app_metadata`, `/roles`, usage severity, script failures, identity-resolution safety, and Sheet reconciliation. Keep `debug_token`/token metadata in state under the existing fail-closed rules.
- Do not remove the registry `admin` value solely for this presentation rule; it can remain as credential/profile metadata and must not be interpreted as a unique owner.
- When activating this policy over an open incident caused only by `user_token_me`, close that incident silently in state so the monitor does not emit a now-obsolete recovery alert.

### Direct-traffic profiles excluded from role verification — effective 2026-08-18

Rodolfo designated the following Sheet identities for direct-traffic strategy, not Meta app-role verification: `Ninda Nak Mapa`, `Reginaldo Novaes Santiago`, `Arruda Arruda`, `Pasgal ID`, `PERFIL NOVO - 193 - backup 192`, and `PERFIL NOVO - 192 - usando para apps pagos 11/08`.

The canonical set lives in `data/meta-app-registry.json` under `verification_ignored_profiles.identities`. Match normalized exact identity against Sheet `Segurador`, `User`, or `USUARIO`, and against Meta role name/ID when available. For these identities only:

- suppress added/removed role deltas and remove stale `last_removed`/`cumulative_removed` entries on the next successful cycle;
- do not create or preserve an `X` in `Removidos acumulado`; the full Sheet reconciler clears the marker and counts the row under `ignored_verification_rows`;
- omit ignored Sheet rows from manual/live accumulated-removal lists;
- continue scanning and alerting every other segurador in the same apps normally;
- do not treat this ignore set as a global page or user authorization change.

### Temporary app-scoped notification pause

When Rodolfo asks to pause only selected app channels, do not pause the whole `meta-app-roles-watch` cron if unaffected apps must remain monitored. Write `/root/mgs-agent/data/meta-app-role-alert-pause.json` with the exact app keys and one of two explicit modes:

- `mode=until`: include an aware ISO `until` timestamp in `America/New_York`; the pause expires automatically when `now >= until`.
- `mode=manual`: omit `until`; keep the selected app-channel deliveries suppressed until Rodolfo explicitly reports that the apps were replaced/recovered and asks to re-enable them.

The production script keeps Graph/Sheet checks and state reconciliation running, suppresses only app-channel Discord delivery for those keys, preserves cooldown timestamps, and reports the active pause mode in `_last_run_summary.active_alert_pause`. No resume cron or gateway restart is needed. Infra/Sheets failure alerts remain independent and are not suppressed by an app-channel pause. A force-live operator run must not bypass a manual pause unless Rodolfo explicitly requests an alert for that paused app in the same current instruction; use an isolated override path only for that one foreground run and never mutate the canonical pause unintentionally.

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

For “todos os 11 canais”, validate the registry-driven current set: `B001-3`, `B002-2`, `B003-2`, `B004-3`, `B005-3`, `B006-3`, `B007`, `B008-2`, `B009-2`, `B010-2`, and `B013-3`. B013-3 routes to the dedicated DTR/ChatPion monitor at channel ID `1522830283240505385`; there must be no stale alternate runtime state, script, Sheet label, or alert title.

On 2026-08-06 Rodolfo retired B012 after the Meta app became inactive and activated B013 as the DTR/ChatPion replacement. The existing Discord channel retained ID `1522830283240505385` and was renamed to `#b013-app-status`. The current `BOT B013 Token` item reuses the immutable production item ID previously pinned by the B012 monitor; the old B012 runtime therefore had to be paused before cutover to prevent it from evaluating B012 rows with B013 credentials. The separate `BOT B013` reserve item remains non-operational. Production pins the unique current `BOT B013 Token` item by immutable ID and fails closed on title/identity drift. B013 is one of the 11 operational channels, not a reserve or a `/roles` app.

Hard guard implemented in `meta-app-roles-watch.sh`: `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` alone is ignored/blocked. Snapshot only becomes effective if `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT` is also set. This prevents accidental manual resend with snapshot after Rodolfo asks for a real alert.

### Restriction-alert presentation for B001–B012 — effective 2026-08-21

Rodolfo approved one human-readable production pattern for every current registry-driven B001–B012 app when Meta Graph returns OAuthException 190 `Application has been deleted` on two consecutive cycles. Operationally this means the app remains visible in Meta for Developers under **Restritos**.

- Title: `<current app label> - APP ENTROU EM RESTRIÇÃO`.
- Put five `🚨` plus real role mentions for `Super Admin`, `Gestor de Trafego`, and `Admin` above the native red embed; do not mention only Rodolfo.
- The embed uses plain manager-facing sections: `O que pode acontecer`, `O que fazer agora`, and `Confirmação do monitor`. Keep the raw Meta phrase only in the final confirmation section; do not expose the generic technical monitor error as the main explanation.
- Discord cannot render regular message content below an embed in the same message. Send the lower `🚨🚨🚨🚨🚨.` as the immediately following message; the final period prevents Discord jumbo-emoji sizing.
- Use a dedicated `app_restricted` cooldown key with the daily blocked-app cooldown. Do not change presentation or recipients for unrelated rate-limit, transient API, role-delta, recovery, or generic script-error alerts.
- Scope is the current 12-app role registry: B001-3, B002-2, B003-2, B004-3, B005-3, B006-3, B007, B008-2, B009-2, B010-2, B011, and B012. B013-3 remains excluded on its dedicated DTR/ChatPion route.
- Preview/canary must use the real embed in the current review thread with role notifications suppressed, then compare production-render helper output against Discord readback. Do not send a validation alert to an app-status channel unless Rodolfo explicitly asks.

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
Assignment   Current live source is the `NO APP` header after Rodolfo rebuilt the allocation on 2026-08-13; current Bxxx assignments are stored there and `APP PROVISORIO` is blank in the live rows. Resolve by header name, not a fixed column letter, because the sheet layout can shift. The prior N/APP PROVISORIO cutover is historical and superseded by the 2026-08-13 rebuild.
Marker       A / Removidos acumulado
Behavior     Full reconciliation every run: rows with the current app assignment in `NO APP` + Segurador/USUARIO that are absent from current Meta /roles get X; rows present in Meta roles are cleared. Non-app operational notes are preserved as unknown/unassigned and never coerced into an app. cumulative_removed is context/history, not the primary source for X. A confirmed migration set may supply names only while its exact app-scoped role-ID set is unchanged; any ID drift preserves existing markers and fails closed.
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
- B013-3 is the current canonical dedicated DTR app name. Use the exact registry-pinned 1Password item, current `NO APP = B013-3`, `b013-dtr-link-watch.sh`, and state `/root/mgs-agent/data/b013-dtr-link-monitor-state.json`. The script must fail closed unless credential metadata and channel routing still match the registry. Retired B011/B012/B013/B013-2 labels are historical only and must remain excluded from generic `/roles` and Sheet reconciliation.
- For Rodolfo requests like “manda alerta real em todos os 11 canais”, scope is registry-driven: the current B001–B010 replacement lineage plus B013-3. As of 2026-08-21 this is exactly `B001-3`, `B002-2`, `B003-2`, `B004-3`, `B005-3`, `B006-3`, `B007`, `B008-2`, `B009-2`, `B010-2`, and `B013-3`. B013-3 must route through the dedicated DTR monitor, never the Meta `/roles` monitor.
- Current Sheet assignment parsing must preserve alpha and hyphen suffixes such as `B001-3`, `B004-3`, `B005-3`, `B006-3`, and `B013-3`. The live assignment header is `NO APP` after the 2026-08-13 rebuild; do not normalize replacement labels to predecessor app keys, and do not fall back to blank `APP PROVISORIO` rows.
- B013 is an Advanced Access + ChatPion connection app: seguradores are not expected to be app roles/admins. Do not mark B013 sheet rows as removed based on `/roles`; preserve them in `ROLE_RECONCILIATION_EXCLUDED_APPS`. The separate DTR page-token monitor owns B013 reconciliation.
- The default B013 source set is every Sheet row with current `NO APP = B013`, including rows already marked `X`; each row must remain monitored so a valid reconnection clears `X` automatically. `Migracao` is informational unless Rodolfo explicitly requests a filtered audit.
- B013 target-set changes are material events: in an initialized state, a new current `NO APP = B013` identity with no prior account state must alert immediately as `kind=added`, even when its first validation is unknown. An identity that disappears from the current B013 target set must alert as `kind=removed`; remove that stale baseline entry so a future reassignment alerts again as a new addition. Never silently absorb a new B013 target into the baseline. Validate both branches with an isolated state fixture; replay a confirmed missed event from a temporary state path so the canonical production state remains untouched.
- Before classifying a B013 target as `missing_dtr_1p_item`, confirm a metadata-cache miss with exactly one forced live refresh of the canonical 1Password DTR item index. Keep the normal metadata cache for healthy hits; never treat a stale cache miss as proof that the credential is absent.
- Persistent B013-3 unknown alerts use a material signature containing affected identities and failure kinds. Alert immediately when that signature changes, repeat an unchanged incident only after the default 6-hour cooldown, and clear the alert state silently after recovery so a later new incident alerts immediately. The cron cadence must never imply a per-cycle repeat cooldown. These app-operational unknown alerts go only to the dedicated B013 app-status channel; `#alerts-infra` is reserved exclusively for canonical REPORT-INFRA embeds. Rodolfo approved the manager-facing presentation on 2026-08-21: title `B013-3 - POSSÍVEL RESTRIÇÃO`; five `🚨` plus real role mentions for `Super Admin`, `Gestor de Trafego`, and `Admin` above a native yellow embed; fields `Contas afetadas`, `O que isso significa`, `O que fazer agora`, and `Proteção aplicada`; no `fail-closed`, Playwright, Graph API or generic technical checklist in the alert copy. The copy must state that no disconnection is confirmed and that the Sheet was not changed. Send the lower `🚨🚨🚨🚨🚨.` as the immediately following message so the period prevents Discord jumbo sizing. Previews use the real embed in the current review thread with role notifications suppressed and must match production helper output by Discord readback.
- B013 `debug_token` classification is evidence-based: HTTP 200 with `is_valid=true` and matching `app_id` is linked; HTTP 200 invalid/mismatched data is confirmed unlinked. Meta OAuth code 100 with the explicit `App_id in the input_token did not match the Viewing App` message is also confirmed unlinked as `token_app_mismatch`. Invalid-signature/code 190, 5xx and ambiguous transport failures remain `unknown` and preserve the Sheet marker fail-closed.
- Alert message fields must show current app users and one-cycle removed/added deltas. For B001–B012, omit any unique owner/admin profile field because all seguradores are administrators; display the role value `administrators` as `Admin` only where a role label itself is needed.
- If a previously removed profile is added/current again, remove it from `Removidos acumulados` before sending the alert. Match using a composed identity, not only the raw Meta `/roles.user` ID: Meta ID + normalized `Segurador` name + sheet `PERFIL ID` (`USUARIO`). A user must never appear in both `Usuários adicionados` and `Removidos acumulados` in the same alert.
- For user/admin role lists, do **not** put wide tables inside Discord embed fields; mobile/Discord truncates and makes them illegible. Preferred B001–B012 alert UX is: short real Discord embed for summary (`Meta APP - Bxxx`, Estado/Contagem/Uso; no unique Admin field) plus normal message(s) containing monospaced tables.
- Snapshot alerts and automatic role-change alerts must use the SAME 3-message Discord format: (1) short embed `Meta APP - Bxxx` with only Estado/Contagem/Uso for B001–B012 (no unique Admin field); (2) normal message code block for current users, styled with Unicode heavy line separators `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━` around the heading `👥 USUÁRIOS ATUAIS`; (3) separate normal message code block containing only `➖ USUÁRIOS REMOVIDOS AGORA`, `🆕 USUÁRIOS ADICIONADOS AGORA`, and `📦 REMOVIDOS ACUMULADOS`, each styled with the same `━` separator lines. Do not put role lists inside embed fields; do not include the old `Movimentações - Bxxx` / `Ordenado por BOT EMAIL` headings in the second block; do not use `=` separators for this alert family.
- Visual presentation rule for the 3-message app roles alert: the Discord embed/card must remain 100% native/unchanged; the first `Usuários Atuais:` code block must also remain unchanged. Apply visual styling only to the third movement/removals code block, using heavy Unicode line separators `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━` above and below each section title plus section emojis, e.g. `➖ USUÁRIOS REMOVIDOS AGORA`, `🆕 USUÁRIOS ADICIONADOS AGORA`, `📦 REMOVIDOS ACUMULADOS`. Do not replace the native embed with text, do not restyle the first users block, and do not use `=`/dashed/punctuated separators when Rodolfo asks for the pages-restritas-style straight line.
- Fetch `/{app_id}/roles` with full cursor pagination: follow every `paging.next` until absent and never impose a total-role cap. A per-page `limit` is not a complete-result guarantee. The 2026-08-07 B005-2 incident proved that reading only the first 100 roles produced 34 false X markers after the app grew beyond 100 users. Detect repeated `paging.next` URLs and fail closed instead of accepting a partial set. Persist source page count and total resolved identities in state.
- If the Meta Developers UI confirms a role that `/{app_id}/roles` temporarily omits, a UI-only identity override may be used for Sheet reconciliation only while the exact observed raw API role-ID signature remains unchanged. Any unattributed ID drift must set `safe_for_sheet=false` and preserve current X markers. If the hidden identity later appears natively in the API, accept `native_api_visibility_restored` without requiring the old signature. Suppress raw added/removed deltas caused only by visibility oscillation when the same confirmed identity remains present in both operational views.
- Resolve `/roles.user` identities with bounded Graph multi-ID chunks of at most 50 IDs as the primary path. If the outer multi-ID request fails or returns per-ID errors, first reuse exact same-ID names from the previous successful state; then individually query only genuinely new unresolved IDs with the validated user token, bounded to 20 IDs and three retries for transient 403/429/5xx responses. Persist chunk, cache and individual diagnostics. This cache-backed fallback is allowed because it does not repeat N requests every cycle; a fresh replacement app pays the bounded resolution cost once, and subsequent cycles query only new IDs. Above the 20-ID unresolved cap, fail closed instead of consuming quota.
- If every role identity remains unresolved after bounded chunk retries/fallback, set `role_identity_reconciliation.safe_for_sheet=false` and preserve existing Sheet markers. Never convert an all-numeric identity failure into a mass-removal write.
- A Rodolfo-confirmed predecessor→replacement migration may use a set-level identity baseline only when the exact current app-scoped role-ID set equals the confirmed set. Keep raw Graph roles in state, use the confirmed names only for operational display/Sheet reconciliation, and fail closed without Sheet writes on any role-ID drift.
- Role/current-user table columns are standardized across the **11-app operational set** as `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS`. Do not use `STATUS` in B013 current-user tables, and do not omit `PÁGINAS` from B001–B010/B005-2. `BOT EMAIL` comes from Google Sheet tab `Migracao 22/06`, column A / `User`; `PERFIL ID` comes from column K / `USUARIO`; `PÁGINAS` comes from column E / `PG`. Match by `Segurador` name. Prefer sheet `USUARIO`, but if a current Meta role does not match the sheet, display the Meta `/roles.user` ID as fallback instead of `sem ID` so the row remains actionable. Sort rows alphabetically by full `BOT EMAIL` so entries group by site/bot user, but display only the local part before `@` for the entire operational set (e.g. `disparosopenzed@gmail.com` → `disparosopenzed`). Rodolfo explicitly confirmed the domain is irrelevant in B013 too.
- B013 `📦 REMOVIDOS ACUMULADOS` must **not** include `MOTIVO`. If the user appears in accumulated removals, the operational state is already clear: profile/link is off/disconnected. Use the same compact schema `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS` there as well; avoid reason/error text in the manager-facing accumulated list unless Rodolfo explicitly asks for diagnostics.
- Current-user lists must never hide rows with suffixes like `... +N outros`. For B001–B010/B005-2, render every current Meta `/roles` user and split the monospaced table across multiple Discord-safe messages when it exceeds 2000 chars. For B013, `👥 USUÁRIOS ATUAIS` must render only currently linked DTR/ChatPion accounts; disconnected/X profiles must appear only under `📦 REMOVIDOS ACUMULADOS`, never duplicated above as `PENDENTE`. This applies to snapshot/manual live alerts and automatic role-change alerts. See `references/app-rate-limit-alert-schema-standardization-2026-07-06.md` for the session correction and validation pattern.
- If an observation field contains `Perfil antigo: <name>` for the same current `NO APP` assignment, suppress/remove that old profile name from `Removidos acumulados`; planned developer/profile migrations are housekeeping, not active incidents.
- If a profile/segurador in `Removidos acumulados` has been reassigned in the sheet to a different current `NO APP` app key (example: B003 → B013), remove it from the old app’s accumulated removals. Accumulated removals are active incidents only while the sheet still says that user belongs to that app.
- If historical `cumulative_removed` cache becomes polluted across apps, do not reset roles/current snapshots. Backup `/root/mgs-agent/data/meta-app-role-monitor-state.json`, clear only `last_removed`, `last_added`, and `cumulative_removed` for each app, then run `meta-app-roles-watch.sh` once live. This preserves current role baselines while letting full sheet reconciliation keep/write X based on current Meta vs sheet truth.
- Owner-profile housekeeping is not a segurador incident. If Rodolfo confirms an app owner profile was disabled/replaced, update both `APP_OWNER_PROFILES` and the skill owner list, add the old owner to `APP_RETIRED_OWNER_PROFILES_BY_APP`, and suppress that retired owner from `last_removed`/`cumulative_removed`. If a profile is removed from another app because it became owner of a different app (example: Dek Fiyan removed from B004 after becoming B007 owner), suppress that removal from B004 role-change alerts too.
- Role-change/snapshot alerts must be sent only after both passes complete: (1) Meta API snapshot for all apps, then (2) Google Sheet reconciliation/sync using the current `NO APP` assignment, `USUARIO`, `Segurador`, and the migration/observation fields available in the live header set. Rate-limit/token/API-health alerts can still be evaluated from API immediately because they do not depend on the migration sheet. This avoids false-positive role alerts when Ially has already documented a planned migration in the sheet.
- Do not post broad Zeus internal status/correction messages in the B001–B010 app-rate-limit channels. Those channels are for app-specific manager alerts only: role added/removed, app/token/API failure, or rate-limit action. Keep REPORT-INFRA/reconciliation explanations in Zeus/#alerts-infra unless Rodolfo explicitly approves manager-facing wording.
- Messenger page health monitoring is a separate next layer: use segurador tokens for page accessibility/conversations and SB/ChatPion for sends, delivered, subscribers/leads.
- Never print access_token, app_secret, page token, or authorization code.
- Credential checks through 1Password must use 4-attempt confirmation before alerting: a single failed/empty `op` read is not proof that the credential is missing. Retry reads up to four total attempts; alert/report only if the 4th consecutive attempt still fails or returns empty. This applies to all credential fields monitored by scripts, not just Meta app access tokens.
- Persist state before declaring success; state is the anti-duplicate source.
```

Discord alert destinations for app-rate-limit alerts:

```text
B001-3  #b001-2-app-status  1521251196294135858
B013-3  #b013-2-app-status  1522830283240505385
B002  #b002-app-rate-limit   1521251220130496723
B003  #b003-app-rate-limit  1521251246860931223
B004-3  #b004-3-app-status  1521251334496456815
B005-3  #b005-3-app-status  1521251961662341160
B006-3  #b006-2-app-status  1521252068319297666
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

