# Shared Drive cutover for interdependent Google Sheets

## Trigger

Use when MGS wants to eliminate personal-user OAuth by moving or reauthorizing operational Google Sheets under a Workspace Shared Drive and Service Account.

## Distinguish three operations

- **Share with a Service Account:** enables API access but the file remains owned/stored in My Drive.
- **Add a shortcut to Shared Drive:** changes discoverability only; ownership and storage do not move.
- **Move the file into Shared Drive:** changes the parent/organizational ownership. Drive API performs this with `files.update(fileId, addParents, removeParents)`, so the same file resource/ID is retained; however permissions, `IMPORTRANGE` authorization, triggers, protections, and external collaborators still require readback.

Sharing plus Service Account authentication is the conservative way to remove human OAuth without touching formula topology.

## Dependency-first inventory

Do not accept a user-named list as the complete migration set until formulas are scanned. Build the graph from live data:

1. Locate spreadsheet IDs in active scripts, crons, configs, routed skills, and on-demand work procedures.
2. Resolve every ID with Drive API and classify My Drive versus Shared Drive.
3. Read spreadsheet metadata and all formulas in batched requests (`values:batchGet`, `valueRenderOption=FORMULA`). Avoid per-tab requests that can exhaust quota.
4. Extract every literal `IMPORTRANGE` source ID and recursively resolve it.
5. Count formulas, `IMPORTRANGE` cells/calls, tabs, named ranges, and existing formatted errors by tab.
6. Separate current-period errors from historical debt. A migration gate compares before/after deltas; it must not claim old `#DIV/0!` or `#REF!` errors were created by cutover.
7. Include apparently retired/ignored sheets when active formulas still reference them. Operational status does not remove formula dependency.

A set with bidirectional references is one strongly connected cluster. Do not migrate only the visible principal and manager sheets while leaving hidden historical or auxiliary dependencies unexamined.

## Conservative route: no file move

Use this when the business goal is authentication durability rather than organizational ownership:

1. Share every spreadsheet in the dependency closure with the approved Service Account at the minimum write role required.
2. Enable Drive and Sheets APIs in the Service Account project.
3. Validate Drive metadata plus Sheets read and bounded write/readback through the exact runtime identity.
4. Change scripts from personal OAuth to Service Account authentication.
5. Run affected crons/runners and compare formulas/values to the baseline.
6. Keep file IDs, tabs, formulas, and My Drive ownership unchanged.
7. Retain personal OAuth only as rollback until all consumers pass; remove it under the credential gate later.

This removes refresh-token revocation risk from automation while avoiding a formula cutover.

## Safe permission rollout before auth cutover

Treat permission rollout and runtime-auth cutover as separate transactions:

1. Build the complete dependency closure and query current permissions plus Service Account Drive visibility before writing. Record a root-only manifest with file IDs, prior target-role state, and later-created permission IDs for rollback; never store the Service Account JSON or tokens.
2. Pick the smallest current-period-clean spreadsheet as the canary. Create the Service Account permission at `writer` with notifications disabled.
3. Read back the permission through the owner identity and require: target permission present, role `writer`, Service Account Drive HTTP 200, `canEdit=true`, and `canModifyContent=true`.
4. Only then apply the same idempotent check/create/readback loop to the rest of the dependency closure. Skip an already-correct permission rather than creating duplicates.
5. Re-read every operational/reference Sheet through the Service Account Drive identity and compare the current-period formula counts and formatted-error baseline through the still-working reader. Permission changes must not change file IDs, tabs, formulas, or values.
6. Probe `spreadsheets.get` with a Service Account token. If Drive succeeds but Sheets returns 403 because `sheets.googleapis.com` is disabled, permission rollout succeeded but the authentication cutover is **not complete**. Keep production on OAuth until an administrator enables the API.
7. After Sheets HTTP 200, use an unused, unprotected cell for a bounded sentinel: capture original formula/value, write a unique marker, read it back, restore/clear to the exact original state, and read back again. Do not use a production formula cell.
8. Switch consumers one at a time, smoke the exact runner/cron, and retain OAuth only as rollback. Revocation/removal of the OAuth credential requires its own credential gate.

Service Usage diagnosis must distinguish:

- `ACCESS_TOKEN_SCOPE_INSUFFICIENT` → token scope problem; obtain `cloud-platform` through the approved flow.
- `PERMISSION_DENIED` / missing `serviceusage.services.enable` with a cloud-platform token → IAM problem for API activation; use an authorized GCP administrator or the direct Cloud Console API-library page. Do not churn the refresh token to solve missing IAM.
- API shown as **Enabled**, but an explicit `x-goog-user-project=<project-number>` probe returns missing `serviceusage.services.use` → caller-consumer IAM is absent. Grant the Service Account least-privilege **Service Usage Consumer** (`roles/serviceusage.serviceUsageConsumer`), allow propagation, and retry `spreadsheets.get`. Do not substitute Service Usage Admin.

The generic Sheets 403 can continue saying “disabled or recently enabled” even after activation when the consumer IAM gate is missing. After a bounded propagation wait, use the explicit quota-project probe once instead of looping on the same error.

## Transactional move route

Never promise absolute zero risk before a canary. The acceptable guarantee is procedural: no cutover is declared if parity fails, and rollback is preserved.

1. Test a synthetic linked Sheet pair first: move one file into the target Shared Drive and verify the same ID plus working `IMPORTRANGE`/permissions.
2. Capture native backups/copies, Drive metadata, parent IDs, permissions, formula/value snapshots, named ranges, protections, merges, data validation, charts, and trigger/App Script inventory.
3. Freeze writes for a short maintenance window.
4. Move the complete dependency cluster in one window when it is strongly connected; avoid a multi-day partial state.
5. After each move require:
   - same spreadsheet ID;
   - target `driveId` and expected parent;
   - Service Account read/write capability;
   - formula-count and formula-hash parity;
   - unchanged external IDs in `IMPORTRANGE`;
   - no new formatted-error delta;
   - current-period key-cell/value parity;
   - preserved human access and protections.
6. Run every affected script/cron against the moved resources.
7. Roll back or stop immediately on permission, formula, trigger, or value drift. Do not repair hundreds of formulas opportunistically during cutover unless the exact repair scope was separately authorized and backed up.

## MGS finance case learned in July 2026

A live audit of the finance cluster showed why dependency closure matters:

- seven primary/current-history spreadsheets contained 563,215 formulas and 1,453 cells containing `IMPORTRANGE`;
- the visible six-file set expanded to a ten-file dependency cluster after resolving historical and auxiliary IDs;
- current July 2026 tabs were clean while older tabs contained pre-existing errors;
- the current principal file covered 2026, while a separate 87-tab historical file covered 2019–2025;
- an operationally ignored former-manager sheet was still referenced by formulas.

The recommended route was to leave the finance cluster in My Drive, share the complete closure with the Service Account, and switch runtime authentication. Simpler operational Sheets could move independently after their own readback gates.

## Reporting

Tell Rodolfo:

- whether the goal is merely OAuth independence or full organizational ownership;
- exact active, historical, auxiliary, and stale counts;
- which files already work through Service Account;
- whether IDs can remain unchanged;
- what is proven versus what requires a canary;
- explicitly that no Google file was moved during a read-only audit.