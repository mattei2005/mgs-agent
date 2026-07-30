## Detectable Failure Modes

```text
Failure mode                         Detection method
------------------------------------ ------------------------------------------------
Token expired                         /debug_token invalid; OAuth error.
Token permissions changed             /debug_token scopes changed.
App removed/desativado                /{app_id} fails or no longer returns app.
Token lost access to app               Permission/OAuth error on /{app_id}.
Meta API access blocked                code=200 OAuthException "API access blocked" across app/user/debug/roles checks.
Rate limit high                        X-App-Usage crosses thresholds.
Developer/business access changed      /me/businesses changes or disappears.
Business verification changed          verification_status changes.
App admin/segurador removed            /{app_id}/roles diff vs previous state; alert removed names.
Graph API throttling                   Errors such as 613, 4, 17, 32 or throttle messages.
ChatPion/DigitalTrChat delivery issue  Indirect: BD_DELIVEREDS drops vs BD_SENDS.
```

If only one app returns `API access blocked` while B001–B010 siblings still validate, treat it as an app/token/developer restriction, not a 1Password/webhook outage. The monitor should classify this separately from generic script errors and throttle repeated alerts to daily until Meta Developers/token remediation is done, otherwise Rodolfo receives hourly duplicates with no new operational signal.

## App Roles / Segurador Admin Drift

For each app, use App Access Token (`app_id|app_secret`) to query roles:

```text
GET /{app_id}/roles?limit=100
```

The endpoint returns user IDs and roles such as `administrators`. Resolve names with:

```text
GET /{user_id}?fields=id,name
```

Store a previous snapshot per app and compare every monitor run:

```text
State field              Purpose
-----------------------  -----------------------------------------
roles_current            Current list of app admins/seguradores.
roles_previous           Previous successful list.
roles_removed            Names/IDs present before and missing now.
roles_added              Names/IDs newly present.
last_roles_ok_at         Last successful roles query timestamp.
```

Alert logic:

```text
- If a name disappears from /roles: CRITICAL/operational alert.
- Include removed names, current names, and previous count vs current count.
- If roles query fails but app health is OK: warning after 2 consecutive failures.
- If roles query fails and app health also fails: critical app/developer access alert.
```

B007 current production baseline currently returns 21 administrators in `/root/mgs-agent/data/meta-app-role-monitor-state.json`.

Do not hard-code this list in the skill; the state file is the runtime baseline and the cron diffs every run against it.

Interpretation: if a developer/segurador account is blocked and Meta removes it from app roles, the monitor can detect the disappearance by diffing `/roles` against the stored previous snapshot.

Developer account blocked/restricted is usually detected by effect: Graph API errors, token invalidation, app inaccessible, permissions removed, or operational delivery collapse. Do not claim Meta provides a guaranteed simple endpoint for every developer-account restriction unless verified in that exact case.

## Segurador Sheet Reconciliation

When Rodolfo asks whether the Meta `/roles` list matches the migration sheet, compare the Graph API state against the Google Sheet tab `Migracao 22/06`.

Rodolfo clarified the operating model: Ially keeps the sheet as the live intent/source for current segurador→app assignment, and the cron should keep the app-channel listing reconciled against it. If a segurador was intentionally migrated because the old developer/profile had problems, the old row may be deleted and a new row added. In that case, removal from Meta roles is housekeeping, not a permanent anomaly, once the new sheet row can be matched by normalized `Segurador × NO APP`.

Human-error feedback loop: if Ially adds a new segurador row but forgets to fill `NO APP`, the monitor may still show that segurador in `Removidos acumulados` because it cannot reconcile the row to a channel/app. That is useful: the channel becomes the visual audit queue for Ially to fill the missing app. Once `NO APP` is corrected, the next cron should match `Segurador × NO APP` and remove the user from the accumulated removed list when runtime state agrees.

Column rule from Rodolfo:

```text
Column K / USUARIO   = segurador/profile ID to display in operational alerts.
Column L / NO APP    = app assignment B001–B010; use this for reconciliation.
Column M / Migracao  = internal migration label/status (OK v1 / OK v2 etc.); ignore by default.
```

Default comparison uses **all rows with `NO APP` filled**, not only rows where `Migracao` starts with `OK`. Only filter `Migracao` if Rodolfo explicitly asks for OK-only.

Report three buckets per app:

```text
Falta na API     In sheet for that app, but not currently returned by Meta roles.
Sobra na API     Returned by Meta roles, but not assigned to that app in sheet.
Duplicado sheet  Same normalized segurador name appears more than once for the app.
```

Rodolfo clarified the intended reconciliation loop: the sheet maintained by Ially is the operational intent layer. If an old segurador/profile is deleted from the sheet because pages were migrated to a new developer/profile, remove that old identity from `Removidos acumulados` instead of keeping it as an active incident. If a new row is added but `NO APP` is blank, leave the mismatch visible so Ially can correct the app assignment; after she fills `NO APP`, the next cron should match by normalized `Segurador × NO APP` and clear the accumulated removal when runtime is consistent. Observation/name-change notes are informational only.

Rodolfo clarified that each Meta app can also contain an owner/creator profile used to create/isolate the app. These are not seguradores and should not count as `Sobra na API` / cleanup candidates unless Rodolfo changes the policy:

```text
B001 Dale Kuhlman
B002 Lola Lilliana
B003 Siyam Mia
B004 Mst Lija
B005/B005-2 Zmii
B006/B006-2 Crislaine Carvalho
B007 Dek Fiyan
B008 Phạm Minh Thiện
B009 Hindawan Pratama
B010 Lorraynii Criistiinii
```

For B005-2, `Wana Hsh` is the retired former owner profile and must be treated as expected owner housekeeping if removed from Meta `/roles`, not as an active segurador incident. `Zmii` is the current owner/admin profile confirmed by Rodolfo and represented in the migration sheet.

For B006-2, `Mic Vb` is the retired owner of the B006 predecessor and must be treated as expected owner housekeeping if removed from Meta `/roles`. `Crislaine Carvalho` is the current B006-2 owner/admin profile confirmed by Rodolfo and represented in the migration sheet. The renamed Discord channel keeps ID `1521252068319297666`, while monitor state/item identity is canonicalized to `B006-2` / `BOT B006-2 Token`.

Rodolfo confirmed on 2026-07-30 that B006 was disabled after a Meta restriction, B006-2 replaced it, and the new app keeps the exact same 17 seguradores from the last healthy B006 baseline plus the new owner Crislaine Carvalho. Meta currently exposes different app-scoped IDs for those users and resolves only the owner name. The runtime may use the confirmed predecessor set for display and Sheet reconciliation only while the exact confirmed B006-2 role-ID set remains unchanged. Preserve raw Graph roles separately. Any missing/unexpected ID must fail closed: do not infer who changed and do not rewrite Sheet removal markers until the new set is attributed safely.

Different Facebook profiles can share the same display name. Rendering must therefore be app-aware: when the current app's owner name matches a Sheet row assigned to a different app, treat them as separate identities and show the owner as `owner do app` without borrowing the unrelated BOT EMAIL/pages. Keep the original Sheet mapping intact for its assigned app.

B009 and B010 owner profiles are also seguradores with one page each; Rodolfo considers them low risk if blocked permanently. For reconciliation, still treat them as owner exceptions when explaining extras.

Use the current runtime state file (`/root/mgs-agent/data/meta-app-role-monitor-state.json`) or a fresh monitor run for Meta roles; the sheet is the planning/assignment source, while Meta roles are the runtime truth. See `references/segurador-sheet-reconciliation.md` for source URL, owner exceptions, normalization rules, and test alert pattern.

