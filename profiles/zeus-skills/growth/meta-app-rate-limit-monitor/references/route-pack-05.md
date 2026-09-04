## Production Cron Implementation

### Current B001-5, B004-5, B007-3 and B011-3 cutovers — 2026-09-03

Rodolfo explicitly replaced restricted `B001-4` with `B001-5`, restricted `B004-4` with `B004-5`, restricted `B007-2` with `B007-3`, and restricted `B011-2` with `B011-3`, then asked Zeus to update and reactivate each complete monitor route.

- `B001-5` uses `BOT B001-5 Token - Debora Monteiro Lima`, channel `1521251196294135858` (`b001-2-app-status`) and `expected_sheet_roles=14`.
- `B004-5` uses `BOT B004-5 Token - Heloisa Barbosa Almeida`, channel `1521251334496456815` (`b004-3-app-status`) and `expected_sheet_roles=11`.
- `B007-3` uses `BOT B007-3 Token - Max Tin Masela`, channel `1520510823426949313` (`b007-app-status`) and `expected_sheet_roles=20`.
- `B011-3` uses `BOT B011-3 Token - ISrael Saucedo`, channel `1537256907373289575` (`b011-app-status`) and `expected_sheet_roles=15`.
- Fresh isolated preflight/canary proved app metadata, paginated `/roles`, `/me` and `debug_token` HTTP 200 for all four apps; every token is valid, app-bound and uses a new app ID; every returned role identity resolved with zero unresolved IDs.
- Production started from fresh app-scoped state: B001-4, B004-4, B007-2 and B011-2 were moved to retired metadata and no predecessor role ID, restriction error or cooldown was reused.
- The Service Account Sheet has zero predecessor rows and exact current assignments: 14 rows for B001-5, 11 for B004-5, 20 for B007-3 and 15 for B011-3, with no blank or duplicate segurador identity. Validated production parity was B001-5 9 present/5 X, B004-5 3 present/8 X, B007-3 3 present/17 X and B011-3 2 present/13 X; role acceptance remains live and later cycles may increase these counts.
- Each route was baselined under temporary alert-only containment, completed a second clean scoped cycle with zero errors and zero duplicate delivery, then was removed from both pause sets. The shared cron remains enabled and the pause sets are empty.
- After an isolated canary, every production command must set `MGS_META_APP_ROLES_STATE=/root/mgs-agent/data/meta-app-role-monitor-state.json` and `MGS_META_APP_ROLE_ALERT_PAUSE_PATH=/root/mgs-agent/data/meta-app-role-alert-pause.json` explicitly. Hermes terminal environment persists across calls, so relying on an implicit default can accidentally continue writing to the canary state/pause paths. A nonzero post-run assertion requires readback of both paths before any retry.
- Backups: `/root/mgs-agent/backups/meta-app-b0014-to-b0015-cutover-20260903-114204/`, `/root/mgs-agent/backups/meta-app-b0044-to-b0045-cutover-20260903-122500/`, `/root/mgs-agent/backups/meta-app-b0072-to-b0073-cutover-20260903-115111/` and `/root/mgs-agent/backups/meta-app-b0112-to-b0113-cutover-20260903-120732/`.

### Current B003-3, B005-4, B006-4, B008-3 and B010-3 cutovers — 2026-09-02

Rodolfo replaced five restricted/deleted app generations, updated their 1Password items and explicitly requested each monitor route to be updated and reactivated. Current canonical runtime:

- `B003-3` uses `BOT B003-3 Token - Dhidin Distro`, channel `1521251246860931223` (`b003-2-app-status`) and `expected_sheet_roles=13`;
- `B005-4` uses `BOT B005-4 Token - Taina Rocha Silveira`, channel `1521251961662341160` (`b005-3-app-status`) and `expected_sheet_roles=14`;
- `B006-4` uses `BOT B006-4 Token - Indah`, channel `1521252068319297666` (`b006-2-app-status`) and `expected_sheet_roles=15`;
- `B008-3` uses `BOT B008-3 Token - Refi Aldiyansyah`, channel `1521252172929564744` (`b008-2-app-status`) and `expected_sheet_roles=9`;
- `B010-3` uses `BOT B010-3 Token - Huy Phạm`, channel `1521252369331916902` (`b010-2-app-status`) and `expected_sheet_roles=13`.

For all five apps, fresh isolated preflight proved app metadata, paginated `/roles`, `/me` and `debug_token` HTTP 200; every token is valid and app-bound; every returned role identity resolved with zero unresolved IDs. First production baselines started at 2/13, 2/14, 1/15, 2/9 and 3/13. By the validated scheduled-cycle snapshot at `2026-09-02T10:47:06-04:00`, normal role acceptances had advanced the live counts to 7/13, 2/14, 1/15, 2/9 and 12/13. These counts are live onboarding state and must not be frozen because role acceptances can occur during the cutover itself.

The canonical Service Account Sheet already used the new generation labels and had zero predecessor rows. Parity at that snapshot was: B003-3 7 present/6 X, B005-4 2 present/12 X, B006-4 1 present/14 X, B008-3 2 present/7 X, and B010-3 12 present/1 X. Present identities are blank and every absent assigned identity is X. During B006-4 onboarding, `Bruna Andrade` disappeared from the live Sheet between preflight and production, reducing the active assignment set from 16 to 15; audit, inventory and REPORT-INFRA had no attribution evidence, so the runtime reconciled to the authoritative 15-row readback and records the change as concurrent/unattributed rather than an anomaly.

Production state was reset per generation: B003-2, B005-3, B006-3, B008-2 and B010-2 were retired to backup/retired metadata and their app-scoped role IDs, cooldowns and restriction errors were not reused. Each first production baseline was silent and each immediate second scoped cycle completed with zero errors and no duplicate alert/Sheet write. The full-registry and later scheduled cycles processed all 12 items with zero errors; real subsequent role acceptances generated the normal B003-3/B010-3 addition alerts. B010-3 briefly reached `call_count=97%` (`critical`) at 10:44 ET and the monitor delivered the normal rate-limit notice; the next scheduled cycle at 10:47 ET read `call_count=10%` (`ok`), proving rolling-window recovery without a credential/cutover failure. The shared cron `0cc7ed1e587e` remains enabled/scheduled, and the manual app-alert pause is now empty.

Isolated cutover canaries must use a unique canary lock file. Reusing `/var/lock/meta-app-roles-watch.lock` can make the canary exit 0 without producing `_last_run_summary` while the scheduled monitor holds the lock. Also assert identity resolution and safety invariants rather than a frozen role count: new role acceptances may legitimately change `current_count` between preflight and canary.

Backups: `/root/mgs-agent/backups/meta-app-b0032-to-b0033-cutover-20260902-095948/`, `/root/mgs-agent/backups/meta-app-b0063-to-b0064-cutover-20260902-101524/`, `/root/mgs-agent/backups/meta-app-b0082-to-b0083-cutover-20260902-102442/`, and `/root/mgs-agent/backups/meta-app-b0102-to-b0103-cutover-20260902-103211/`.

### Current B012-2 cutover — 2026-09-01

Rodolfo explicitly replaced retired `B012` with `B012-2`, updated the exact 1Password item and renamed the existing app-status channel.

- Current app key: `B012-2`; predecessor `B012` is retired from the active registry.
- Current item: `BOT B012-2 Token - Bình Hòa Trần`; `app_name=B012-2` and the required credential fields are readable without exposing values.
- Existing channel ID remains `1537256951879172136`; live channel name and registry mapping are `b012-2-app-status`.
- Fresh isolated preflight proved app metadata, `/roles`, `/me` and `debug_token` healthy; the token is valid and app-bound; all eight roles resolve to names with zero unresolved identities and `safe_for_sheet=true`.
- The canonical Service Account Sheet was already migrated before the runtime cutover: `NO APP=B012-2` has eight rows, `NO APP=B012` has zero, all eight assignments match the fresh role set, there are zero duplicates/blanks and zero `X` markers. No Sheet write was required.
- Store `expected_sheet_roles=8`. Production must start B012-2 from a fresh state and must not reuse B012 app-scoped role IDs or its restriction/error cooldowns. Preserve the predecessor only in the verified cutover backup and retired-state metadata.
- Cron job `0cc7ed1e587e` remains the shared registry-driven `meta-app-roles-watch`; B012-2 uses the normal B001–B012 `/roles` and Sheet-reconciliation path. The first baseline must be silent, error-free and write-free when the live Sheet is already converged; future real role changes alert normally.
- Pre-cutover B012 restriction and missing-item alerts are predecessor history. Do not delete those Discord messages without the Critical Subset confirmation.
- Cutover backup: `/root/mgs-agent/backups/meta-app-b012-to-b0122-cutover-20260901-110638/`, with SHA-256 manifest verified.

### Current B013-5 cutover — 2026-09-04

Rodolfo replaced restricted `B013-4` with `B013-5`, updated the exact 1Password item, moved the canonical Sheet assignments and explicitly requested validation plus one real alert.

- Current item: `BOT B013-5 Token - Yani Diana Delima`; `app_name=B013-5`, required fields are present, and the dedicated channel remains `1522830283240505385` (`b013-2-app-status`).
- App metadata, `/me`, `debug_token` and app-token `/roles` returned HTTP 200; the user token is valid and app-bound, metadata name is B013-5, and `/roles` returned two roles.
- The canonical Service Account Sheet has 39 exact `NO APP=B013-5` rows, zero blank bot users/seguradores and zero duplicate segurador names. Repeated bot users are valid because one DTR login can contain multiple seguradores.
- The dedicated script now pins the exact B013-5 item, requires `app_name=B013-5`, reads only `NO APP=B013-5`, renders `Meta APP - B013-5`, preserves the existing channel and retains the `INVEST 3D` column.
- Production started from a fresh B013-5 state; no B013-4 account verdict, cooldown or confirmation incident was reused. Rollback backup: `/root/mgs-agent/backups/meta-app-b0134-to-b0135-cutover-20260904T181435-0400/`.
- Full read-only preflight: 39 targets, nine linked, 29 confirmed unlinked and one unknown; app capability healthy; 50 DTR pages, 50 Graph pages and 50 connected pages; no Sheet write, Discord post or production state persistence.
- First production baseline: nine linked, 29 confirmed unlinked and one unknown; 28 Sheet cells updated, 29 current B013-5 rows marked, one unknown preserved, zero alerts.
- Second production cycle: nine linked, 30 confirmed unlinked, zero unknown, healthy capability and zero Sheet writes. The one fresh unknown→confirmed transition generated the single canonical real alert family requested by Rodolfo; four physical messages were verified in Discord with `Meta APP - B013-5`, `INVEST 3D` in BRL, current users and all confirmed removals. Message IDs: `1545563123954749512`, `1545563153734176948`, `1545563154807922820`, `1545563155810353232`.
- Cron `498fb0d95e10` was resumed only after both production cycles passed. Its first scheduled post-resume cycle completed with the same 9/30/0 state, healthy capability, zero Sheet writes and zero alerts.

### Historical B013-4 cutover — 2026-08-29

Rodolfo explicitly replaced `B013-3` with `B013-4`, updated the new 1Password item and authorized Zeus to update the complete dedicated route and reactivate its cron.

- Current item: `BOT B013-4 Token - Dayanna Regis`; required fields are readable, `app_name=B013-4`, and alert channel ID remains `1522830283240505385` (`b013-2-app-status`).
- App metadata, `/me` and `debug_token` return HTTP 200; the token is valid and app-bound. `/roles` must use the app access token for this app: that route returns HTTP 200 with four roles, while the user-token call correctly returns OAuthException 15 requiring an app access token.
- The canonical Sheet was already migrated before cutover: `NO APP = B013-4` has 31 rows and `NO APP = B013-3` has zero.
- `meta-app-roles-watch.sh` now excludes every current/future B013 replacement generation by lineage prefix instead of one hard-coded suffix. Its active app set, DTR-only item set and Sheet reconciliation exclusion all derive from the registry, so exposing B013-4 cannot route it through generic `/roles` reconciliation.
- Dedicated runtime `/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh` pins the exact B013-4 item, requires `app_name=B013-4`, selects only `NO APP=B013-4`, keeps the existing channel, state path and alert UX, and renders manager-facing titles as B013-4.
- Preserve the B013-3 state only in the cutover backup; production starts B013-4 with a fresh empty account baseline. Never reuse B013-3 link verdicts as B013-4 state.
- Full read-only preflight: 31 targets, 4 linked, 27 confirmed unlinked, zero unknown; 26 DTR pages, 22 Graph pages and 22 subscribed pages; app capability healthy; no Sheet write, Discord post or production state persistence.
- First production baseline: 31 targets, 4 linked, 27 confirmed unlinked, zero unknown; capability healthy; Sheet converged to 27 X and four blank rows; 28 cells changed; zero alerts because the new generation was being baselined.
- First scheduled cycle after reactivation completed `ok`: seven linked, 24 confirmed unlinked, zero unknown; capability healthy; three newly linked rows cleared X and the monitor emitted one canonical four-message addition family, verified by Discord message IDs `1543425383423148085`, `1543425384865857607`, `1543425385620967507`, and `1543425386896166944`.
- The immediately following scheduled cycle also completed `ok` and advanced live convergence to 18 linked, 13 confirmed unlinked and zero unknown; capability remained healthy with 220 DTR pages, 205 Graph pages and 195 subscribed pages. Eleven more rows cleared X and a second chronological four-message addition family was verified by Discord readback (`1543427107491807293`, `1543427108775141516`, `1543427109698011186`, `1543427110692192276`). Preserve both accurate families.
- Closure snapshot at `2026-08-29T21:17:22-04:00`: a third scheduled cycle completed `ok` with 29 linked, two confirmed unlinked and zero unknown; capability stayed healthy with 306 DTR pages, 284 Graph pages and 270 subscribed pages. Eleven more rows cleared X and the chronological four-message family was verified by Discord readback (`1543429388161253460`, `1543429389386256496`, `1543429390422249634`, `1543429391546196083`). The two remaining profiles stay monitored and must clear automatically when reconnected.
- Cron job `498fb0d95e10` remains `b013-dtr-link-watch`, schedule `2-59/9 0,8-23 * * *`, `no_agent`, `deliver=local`, now `enabled=true` and `state=scheduled`. Each later successful reconnection must clear X and alert as an addition; unresolved accounts remain monitored rather than being silently absorbed.
- Cutover backup: `/root/mgs-agent/backups/meta-app-b0133-to-b0134-cutover-20260829-204023/`, with verified SHA-256 manifest.

Historical note: the B013-3 cutover below is superseded for active runtime but remains evidence of its 2026-08-21 migration.

### Historical B007-2 cutover — 2026-08-24

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

### Historical B013-3 cutover — 2026-08-21

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

### Historical B001-4 and current B002-3 cutovers — 2026-08-28

Rodolfo explicitly replaced retired `B001-3` with `B001-4` and retired `B002-2` with `B002-3`. Current canonical runtime:

- B001-4 item: `BOT B001-4 Token - Aline Rosse`, `app_name=B001-4`, channel ID `1521251196294135858` (live name remains `b001-2-app-status`), and `expected_sheet_roles=16`;
- B002-3 item: `BOT B002-3 Token - Khánh Chi Phùng`, `app_name=B002-3`, channel ID `1521251220130496723` (live name remains `b002-2-app-status`), and `expected_sheet_roles=10`;
- both replacements pass app metadata, `/roles`, `/me`, and `debug_token` with HTTP 200; each token is valid and bound to the exact new app ID;
- the canonical Sheet, read only through the MGS Service Account, has 16 current `NO APP = B001-4` rows and 10 current `NO APP = B002-3` rows, with no blank or duplicate segurador identity;
- the first production baselines expose 2/16 accepted B001-4 roles and 1/10 accepted B002-3 roles, with every currently visible identity resolved;
- while accepted roles remain below the expected counts, `safe_for_sheet=false` must preserve all existing Sheet markers and block automatic X writes. This is pending role acceptance, not proof of removal;
- production state was reset and rebuilt from the new app-scoped IDs; never reuse B001-3 or B002-2 role IDs/baselines for the replacement apps;
- baseline under temporary app-scoped notification containment produced zero errors, zero alerts and zero Sheet writes; after a second clean cycle the containment was cleared so future accepted roles alert normally;
- recurring `meta-app-roles-watch` remains enabled. B001-4 and B002-3 are active and unpaused; B013-4 stays on the dedicated DTR route.

Historical note: the B001-3 cutover from 2026-08-21 closed its own predecessor migration but is now superseded by B001-4. Do not treat its 17-role expectation or app-scoped IDs as current.

### Historical B004-4 cutover — 2026-08-28

Rodolfo explicitly replaced retired `B004-3` with `B004-4`. Current canonical runtime:

- app key: `B004-4`;
- 1Password item: `BOT B004-4 Token - Joao Matheus`, with `app_name=B004-4`;
- Discord channel ID remains `1521251334496456815`; the live channel name remains `b004-3-app-status` until a separate rename is authorized;
- live token profile is `Joao Matheus`;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; token is valid and bound to the exact B004-4 app ID;
- the canonical Sheet has 12 `NO APP = B004-4` assignments, with no blank or duplicate segurador identity;
- the first production baseline exposes 1/12 accepted role, resolved to Joao Matheus. Store `expected_sheet_roles=12`; while 11 roles remain pending, `safe_for_sheet=false` blocks Sheet X writes;
- production state was reset and rebuilt from B004-4 app-scoped IDs; never reuse B004-3 IDs or its completed 12-role baseline;
- temporary B004-3/B004-4 notification containment was cleared only after two scoped cycles proved four healthy Graph checks, zero errors, zero alerts and zero Sheet writes;
- B004-4 is active and unpaused so future accepted roles alert normally.

Historical note: B004-3 previously completed 12/12, but that app and its role IDs are retired and must not be treated as current.

### Current B009-3 cutover — 2026-08-28

Rodolfo explicitly replaced retired `B009-2` with `B009-3`. Current canonical runtime:

- app key: `B009-3`;
- 1Password item: `BOT B009-3 Token - Amoey Pnr`, with `app_name=B009-3`;
- Discord channel ID remains `1521252284623884288`; the live channel name remains `b009-2-app-status` until a separate rename is authorized;
- live token profile is `Amoey Pnr`;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; token is valid and bound to the exact B009-3 app ID;
- the canonical Sheet has 17 `NO APP = B009-3` assignments, with no blank or duplicate segurador identity;
- the first production baseline exposes 1/17 accepted role, resolved to Amoey Pnr. Store `expected_sheet_roles=17`; while 16 roles remain pending, `safe_for_sheet=false` blocks Sheet X writes;
- production state was reset and rebuilt from B009-3 app-scoped IDs; never reuse the deleted B009-2 app state, IDs, errors or cooldowns;
- temporary B009-2/B009-3 notification containment was cleared only after two scoped cycles proved four healthy Graph checks, zero errors, zero alerts and zero Sheet writes;
- the next full registry-driven cycle loaded the exact B009-3 item and kept it healthy with `consecutive_errors=0`; the then-remaining B011 deleted-app error was later superseded by B011-2;
- B009-3 is active and unpaused so future accepted roles alert normally.

Historical note: B009-2 had entered Meta restriction/deletion and accumulated 29 errors before replacement. It is retired and must not remain in the active registry.

### Historical B011-2 cutover — 2026-08-28

Rodolfo explicitly replaced deleted/restricted `B011` with `B011-2` and required all replacement-app credentials plus the recurring real-alert cron to be revalidated. Current canonical runtime:

- app key: `B011-2`;
- 1Password item: `BOT B011-2 Token - Ashley Comf`, with `app_name=B011-2`;
- preserve the predecessor's live Discord channel by reading it from the registry: channel ID `1537256907373289575`, live name `b011-app-status`. Never hardcode or infer a replacement channel ID;
- live token profile is `Ashley Comf`;
- app metadata, `/roles`, `/me`, and `debug_token` return HTTP 200; token is valid and bound to the exact B011-2 app ID;
- the canonical Sheet has 17 `NO APP = B011-2` assignments, with no blank or duplicate segurador identity;
- the first production baseline exposes 1/17 accepted role, resolved to Ashley Comf. Store `expected_sheet_roles=17`; while 16 roles remain pending, `safe_for_sheet=false` blocks Sheet X writes;
- production state was reset and rebuilt from B011-2 app-scoped IDs; never reuse the deleted B011 state, IDs, 42-error incident or cooldowns;
- temporary B011/B011-2 notification containment was cleared only after two scoped cycles proved four healthy Graph checks, zero errors, zero alerts and zero Sheet writes;
- the next full 12-item registry-driven cycle loaded exact items for B001-4, B002-3, B004-4, B009-3 and B011-2; all five passed all four Graph checks with zero consecutive errors, the overall cycle had zero errors, and normal real-alert delivery remained enabled;
- B011-2 is active and unpaused so future accepted roles and real incidents alert normally.

Historical note: B011 had reached 42 consecutive deleted-app errors immediately before the B011-2 full-cycle cutover. It is retired and must not remain in the active registry.

Identity-resolution correction: Meta can return HTTP 500 for the multi-ID user-token lookup even while each individual `/{role_id}?fields=id,name` succeeds. The monitor now tries bounded multi-ID first, reuses exact same-ID names from prior state, and individually resolves only genuinely new unresolved IDs up to a hard cap of 20. This makes replacement-app onboarding self-healing without creating a per-cycle N+1 quota drain. Persist `cache_resolved_count`, individual request/resolution counts and statuses in state; when unresolved identities exceed the cap, fail closed for Sheet reconciliation.

### Historical B006-3 cutover — 2026-08-17

Rodolfo explicitly replaced retired `B006-2` with `B006-3` and re-enabled that generation inside the generic Meta roles cron. Historical runtime at that time:

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
Scope          Registry-driven current B001-B012 replacement lineage. Every B013 generation is excluded from this script’s /roles alert path and handled by b013-dtr-link-watch.
Channels       B001-5 1521251196294135858 (live channel name still b001-2-app-status); B002-3 1521251220130496723 (live channel name still b002-2-app-status); B003-3 1521251246860931223; B004-5 1521251334496456815 (live channel name still b004-3-app-status); B005-4 1521251961662341160; B006-4 1521252068319297666; B007-3 1520510823426949313; B008-3 1521252172929564744; B009-3 1521252284623884288 (live channel name still b009-2-app-status); B010-3 1521252369331916902; B011-3 1537256907373289575; B012-2 1537256951879172136
```

Use the Meta roles cron for the current registry-driven B001–B012 app lineage. B013-5 remains on the separate DTR/ChatPion route because its users are fetched through DTR/ChatPion + Meta `debug_token`, not `/app/roles`. Future B013 replacement suffixes remain on that same dedicated route by lineage.

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

`apps` is the legacy alert-only pause set: the production script keeps Graph/Sheet checks and state reconciliation running, suppresses only app-channel Discord delivery for those keys, preserves cooldown timestamps, and reports the active pause mode in `_last_run_summary.active_alert_pause`. `monitor_apps` is the full app-route pause set: the shared cron remains enabled for unaffected apps, but every listed app is skipped before Graph/Sheet processing until its replacement/recovery is validated and Rodolfo explicitly asks to resume it. No resume cron or gateway restart is needed. Infra/Sheets failure alerts remain independent and are not suppressed by an alert-only pause. A force-live operator run must not bypass either pause unless Rodolfo explicitly requests an alert for that paused app in the same current instruction; use an isolated override path only for that one foreground run and never mutate the canonical pause unintentionally.

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

If the same B013 run detects material link changes and `FORCE_LIVE_ALERT=1`, the automatic fresh change alert is the single canonical delivery. Automatic change alerts are Sheet-scoped: `REMOVIDOS CONFIRMADOS` contains every currently confirmed unlinked profile whose canonical `Segurador × User` row still has the current B013 assignment (currently `NO APP=B013-5`), even when that removal was already shown in an earlier report. If the Sheet reassigns the row to another app, the next B013 cycle retires it from B013 scope and no later B013 report may show it unless it is assigned back. Keep the current pending count in the summary card and the persistent `X` in the Sheet/state until recovery or reassignment. A manual force with no material change uses the same current-state inventory. Suppress the second force-snapshot family when the same run has material changes, but keep the embed description as `Alerta live solicitado` because the operator initiated the run. After any delivery bug, keep the accurate change alert, delete only the duplicate snapshot messages after Critical Subset confirmation, verify readback and persist `alerts_sent=1`.

B013 summary cards must visually follow the accepted B010 native embed: title `Meta APP - B013-5`, one concise live-data description, yellow `ATENÇÃO` only when pending profiles exist, and compact inline fields in this order: `ESTADO`, `CONTAGEM`, `PENDENTES`, `PÁGINAS`, `DTR`, `META`. Keep DTR/Graph diagnostics out of the prose. The three-message layout remains: native summary embed, complete current-user table, then movements/confirmed removals. A force-live snapshot must not replay cached additions; show `ADICIONADOS AGORA` as `Nenhum.` unless that same fresh run proves a real addition. Omit the entire inconclusive section when there are no inconclusive profiles.

For a request covering all current app channels, validate the registry-driven set: the current B001–B012 replacement lineage plus `B013-5`. B013-5 routes to the dedicated DTR/ChatPion monitor at channel ID `1522830283240505385`; there must be no stale alternate runtime state, script, Sheet label, or alert title.

Historical note: on 2026-08-06 Rodolfo retired B012 after the Meta app became inactive and activated the original B013 as the DTR/ChatPion replacement. The existing Discord channel retained ID `1522830283240505385` and was renamed to `#b013-app-status`. At that time, the `BOT B013 Token` item reused the immutable production item ID previously pinned by the B012 monitor; the old B012 runtime therefore had to be paused before cutover to prevent it from evaluating B012 rows with B013 credentials. The separate `BOT B013` reserve item was non-operational. This paragraph is historical only; the active generation is defined in the current cutover section above.

Hard guard implemented in `meta-app-roles-watch.sh`: `MGS_META_APP_ROLES_FORCE_SNAPSHOT=1` alone is ignored/blocked. Snapshot only becomes effective if `MGS_META_APP_ROLES_ALLOW_SNAPSHOT=EXPLICIT_RODOLFO_SNAPSHOT` is also set. This prevents accidental manual resend with snapshot after Rodolfo asks for a real alert.

### Restriction-alert presentation for B001–B012 — effective 2026-08-21

Rodolfo approved one human-readable production pattern for every current registry-driven B001–B012 app when Meta Graph returns OAuthException 190 `Application has been deleted` on two consecutive cycles. Operationally this means the app remains visible in Meta for Developers under **Restritos**.

- Title: `<current app label> - APP ENTROU EM RESTRIÇÃO`.
- Put five `🚨` plus real role mentions for `Super Admin`, `Gestor de Trafego`, and `Admin` above the native red embed; do not mention only Rodolfo.
- The embed uses plain manager-facing sections: `O que pode acontecer`, `O que fazer agora`, and `Confirmação do monitor`. Keep the raw Meta phrase only in the final confirmation section; do not expose the generic technical monitor error as the main explanation.
- Discord cannot render regular message content below an embed in the same message. Send the lower `🚨🚨🚨🚨🚨.` as the immediately following message; the final period prevents Discord jumbo-emoji sizing.
- Use a dedicated `app_restricted` cooldown key with the daily blocked-app cooldown. Do not change presentation or recipients for unrelated rate-limit, transient API, role-delta, recovery, or generic script-error alerts.
- Scope is the current 12-app role registry: B001-5, B002-3, B003-3, B004-5, B005-4, B006-4, B007-3, B008-3, B009-3, B010-3, B011-3, and B012-2. B013-5 remains excluded on its dedicated DTR/ChatPion route.
- Preview/canary must use the real embed in the current review thread with role notifications suppressed, then compare production-render helper output against Discord readback. Do not send a validation alert to an app-status channel unless Rodolfo explicitly asks.

### Automatic full-route pause after restriction — effective 2026-09-02

Rodolfo superseded the prior manual-only handling: when a current B001–B012 app reaches the confirmed restriction trigger (`OAuthException 190 Application has been deleted` on two consecutive cycles), the monitor must send the first canonical restriction alert and, in the same run, atomically add that app to both `apps` and `monitor_apps` in `data/meta-app-role-alert-pause.json` with `mode=manual`. Starting on the next cycle, skip that app route entirely; keep the shared `meta-app-roles-watch` cron enabled for every unaffected app. Resume only after the replacement/recovery passes its preflight/canary/readback and Rodolfo explicitly requests reactivation.

The immediate pause from message `1544837470687076454` originally covered `B001-4`, `B004-4`, `B007-2`, and `B011-2`. B001-5, B004-5, B007-3 and B011-3 passed replacement cutover and were reactivated on 2026-09-03. Both pause sets are now empty.

The production monitor cadence is:

> Supersessão explícita de Rodolfo em 2026-07-31: a cadência horária de 2026-07-10 foi substituída. B001-B010 agora executam a cada 3 minutos entre 08:00 e 00:59 ET, com stagger interno padrão de 4 segundos entre apps. B013 executa aproximadamente a cada 9 minutos na mesma janela, com offset de 2 minutos e `flock` não bloqueante. Não executar entre 01:00 e 07:59 ET. A regra anterior de Meta em `:04` e B013 em `:24` fica preservada apenas como histórico supersedido.

```text
Failure mode                         Alert SLA
-----------------------------------  -----------------------------------------
Segurador/admin removed from roles   B001-B010/B005-2: próximo ciclo de 3 minutos entre 08:00 e 00:59 ET
Segurador/admin added to roles       B001-B010/B005-2: próximo ciclo de 3 minutos entre 08:00 e 00:59 ET
B013 DTR/ChatPion link removed       próximo ciclo aproximado de 9 minutos entre 08:00 e 00:59 ET
X-App-Usage >=70%                    alert on severity increase
X-App-Usage >=85%                    risk alert; for B007-3/Openzed act fast
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

Positive-evidence and Sheet-parity rule: an exact current Meta role match by app-scoped ID or normalized `Segurador` name must always clear that row's stale `X`. When app metadata, paginated `/roles` and `debug_token` are healthy and every returned role identity resolves, a count below `expected_sheet_roles` is also a trustworthy present/absent snapshot: current rows stay blank and Sheet-assigned identities absent from Meta receive `X`. The expected-count gate may continue to report pending acceptance, but it must not leave the Sheet stale. Preserve fail-closed markers only for genuine identity ambiguity, partial pagination/lookup, unresolved names or baseline drift. This makes `Removidos acumulado` mirror live app membership and ensures a recovered segurador loses `X` on the next cycle. B011-3 and B012-2 are part of the generic role reconciliation; the registry-selected B013 generation is excluded on the dedicated DTR/page-token route.

If Google auth fails for this cron, validate the canonical Service Account item, `roles/serviceusage.serviceUsageConsumer`, Sheets metadata, sentinel write/readback/restore and `_sheet_removed_sync`. Do not recreate the retired Ares OAuth files.

Implementation rules:

```text
- Empty output is success/silent; no_agent cron sends nothing on OK.
- Do not use cronjob Discord delivery for final alerts; post direct Discord bot messages to the app-specific channel mapping. Fallback webhook is legacy only.
- Auto-discover 1Password items matching BOT Bxxx Token when MGS_META_APP_ROLE_ITEMS is unset.
- Use the 1Password item code (B001/B002/etc.) as the state key; do not trust copied/stale app_name fields. Replacement apps may be named with a suffix like `BOT B005-2 Token`; keep the replacement label visible in alert titles/`App` field/state (`B005-2`), while mapping it to the same operational Discord channel (`#b005-app-rate-limit`). Do not silently display it as `B005`.
- B013-5 is the current canonical dedicated DTR app name. Use the exact registry-pinned 1Password item `BOT B013-5 Token - Yani Diana Delima`, current `NO APP = B013-5`, `b013-dtr-link-watch.sh`, and state `/root/mgs-agent/data/b013-dtr-link-monitor-state.json`. The script must fail closed unless credential metadata and channel routing match the registry. Retired B013/B013-2/B013-3/B013-4 labels are historical only; B013-5 remains excluded on its dedicated route.
- For Rodolfo requests covering all app channels, scope is registry-driven: the current B001–B012 replacement lineage plus B013-5. B013-5 must route through the dedicated DTR monitor, never the Meta `/roles` monitor.
- Current Sheet assignment parsing must preserve alpha and hyphen suffixes such as `B001-5`, `B002-3`, `B003-3`, `B004-5`, `B005-4`, `B006-4`, `B007-3`, `B008-3`, `B009-3`, `B010-3`, and `B013-5`. The live assignment header is `NO APP` after the 2026-08-13 rebuild; do not normalize replacement labels to predecessor app keys, and do not fall back to blank `APP PROVISORIO` rows.
- B013 is an Advanced Access + ChatPion connection lineage: seguradores are not expected to be app roles/admins. Do not mark its Sheet rows as removed based on `/roles`; derive `ROLE_RECONCILIATION_EXCLUDED_APPS` from every registry app whose key starts with `B013`. The separate DTR page-token monitor owns B013 reconciliation.
- The default B013 source set is every Sheet row assigned to the exact current registry B013 key, currently `NO APP = B013-5`, including rows already marked `X`; each row remains monitored so a valid reconnection clears `X` automatically. `Migracao` is informational unless Rodolfo explicitly requests a filtered audit.
- B013 target-set additions are material events: in an initialized state, a new identity assigned to the current registry B013 key with no prior account state must alert immediately as `kind=added`, even when its first validation is unknown. A row that disappears because the canonical Sheet moved it away from B013 is a planned scope change: retire its stale baseline silently so a future reassignment alerts again as a new addition. Never silently absorb a new B013 target into the baseline. Validate both branches with an isolated state fixture; replay a confirmed missed event from a temporary state path so the canonical production state remains untouched.
- Before classifying a B013 target as `missing_dtr_1p_item`, confirm a metadata-cache miss with exactly one forced live refresh of the canonical 1Password DTR item index. Keep the normal metadata cache for healthy hits; never treat a stale cache miss as proof that the credential is absent.
- B013-5 account absence and possible app restriction are separate incidents. If an authenticated DTR inventory no longer contains one Sheet-assigned profile, preserve the Sheet on the first cycle; after two consecutive verified absences classify it as `profile_removed_from_dtr`, send only the normal profile-removal/link-change alert and reconcile `X`. Never use `not_found_in_dtr_switcher` as app-restriction evidence. If the canonical Sheet has already moved the row away from B013-5, retire its baseline silently as planned scope change. `B013-5 - POSSÍVEL RESTRIÇÃO` is reserved for at least three independent bot logins with persistent `debug_token_check_failed` evidence, or the separate app-capability detector's stronger blocked result; one isolated account can never open it. Unknown-alert signatures contain only eligible app-wide identities/failure kinds, repeat unchanged incidents after the default 6-hour cooldown, and clear silently after recovery. These app-operational alerts go only to the dedicated B013 app-status channel; `#alerts-infra` remains exclusive to REPORT-INFRA. Replace each account snapshot instead of merging it so stale prior `debug_token` success cannot survive a new unknown result.
- Every automatic `B013-5 - POSSÍVEL RESTRIÇÃO` incident must trigger an immediate anti-false-positive verification after the initial alert. Confirmation requires both layers: persistent exact `OAuthException 190 / Application has been deleted` evidence on at least three independent bot logins, plus fresh app-token checks of both `/{app_id}` metadata and `/{app_id}/roles` returning the same exact deleted-application response. When both layers pass, immediately send one follow-up alert to the same B013 channel stating `Não é falso positivo`; deduplicate that confirmation for the lifetime of the incident and clear its key only after recovery so a future incident can confirm again. If either fresh route recovers, differs, or fails ambiguously, keep the result inconclusive and do not claim confirmation; retry on a later normal cycle without weakening Sheet fail-closed protection. Never persist or display the app access token.
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
- Role/current-user table columns are standardized across the complete active B001–B013 set as `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS | INVEST 3D`. Do not use `STATUS` in B013 current-user tables, and do not omit `PÁGINAS` or `INVEST 3D` from either monitor route. `INVEST 3D` is the Smart Bidding Messenger Daily `INVESTIMENT` total by exact normalized `PROFILE_NAME` for exactly three calendar dates: the current report date, which may still be partial, plus its two preceding dates. Never substitute or display the seven-day total. Render the monetary value as BRL (`R$`), matching the current Smart Bidding dashboard/Sheet convention. Fetch the metric lazily only when an alert table is actually being rendered; one fetch is reused across every app/table in that monitor run. A source or profile match failure renders `n/d` and must never block or delay the underlying app-health alert beyond the bounded enrichment timeout. `BOT EMAIL` comes from Google Sheet tab `Migracao 22/06`, column A / `User`; `PERFIL ID` comes from column K / `USUARIO`; `PÁGINAS` comes from column E / `PG`. Match by `Segurador` name. Prefer sheet `USUARIO`, but if a current Meta role does not match the sheet, display the Meta `/roles.user` ID as fallback instead of `sem ID` so the row remains actionable. Sort rows alphabetically by full `BOT EMAIL` so entries group by site/bot user, but display only the local part before `@` for the entire operational set (e.g. `disparosopenzed@gmail.com` → `disparosopenzed`). Rodolfo explicitly confirmed the domain is irrelevant in B013 too.
- B013 `📦 REMOVIDOS ACUMULADOS` must **not** include `MOTIVO`. If the user appears in accumulated removals, the operational state is already clear: profile/link is off/disconnected. Use the same compact schema `BOT EMAIL | SEGURADOR | PERFIL ID | PÁGINAS | INVEST 3D` there as well; avoid reason/error text in the manager-facing accumulated list unless Rodolfo explicitly asks for diagnostics.
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
B001-5  #b001-2-app-status  1521251196294135858
B013-5  #b013-2-app-status  1522830283240505385
B002-3  #b002-2-app-status  1521251220130496723
B003-3  #b003-2-app-status  1521251246860931223
B004-5  #b004-3-app-status  1521251334496456815
B005-4  #b005-3-app-status  1521251961662341160
B006-4  #b006-2-app-status  1521252068319297666
B007-3  #b007-app-rate-limit  1520510823426949313
B008-3  #b008-2-app-status  1521252172929564744
B009-3  #b009-2-app-status  1521252284623884288
B010-3  #b010-2-app-status  1521252369331916902
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

Meta App Rate Limit — B007-3/Openzed
...
```

Use aligned compact sections (`Resumo`, `Checks`, `Ação`) instead of raw JSON or prose. See `references/discord-webhook-alert-format.md` for the accepted format and webhook delivery pattern.

