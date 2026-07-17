---
name: google-drive-agent-automation
description: "Operate and troubleshoot Google Drive automation for MGS agents: Service Account vs user OAuth, My Drive vs Shared Drives, preflight checks, quota errors, folder IDs, and safe batch upload/copy flows."
tags: [google-drive, service-account, oauth, shared-drive, quota, ares, automation, batch-upload, ops]
related_skills: [discord-ops, hermes-agent-operations]
---

# Google Drive Agent Automation

## When to use

Use this skill when Rodolfo asks Zeus/Ares/Hera/Atena to debug or enable Google Drive automation, especially:

- Service Account can read/create folders but file upload fails.
- Drive API returns `403 storageQuotaExceeded`.
- A batch creative/content pipeline needs to copy/upload many files.
- A script needs to choose between My Drive, Shared Drive, or real-user OAuth.
- A Google Drive folder ID must be validated before a destructive or large write run.
- A Google Sheet needs column values distributed/updated/colored via API, especially when preserving row grouping by site/bot/gestor matters.
- Rodolfo wants to inventory and migrate only the operational Sheets used by named MGS agents from personal My Drive into the enterprise Shared Drive, without touching unrelated personal content.

## Executive rule

Do **not** treat Drive `canAddChildren=true`, `canEdit=true`, or successful folder creation as proof that uploads will work. For Google Service Accounts, upload viability depends on destination storage model:

```text
Destination type              Service Account upload outcome
----------------------------|----------------------------------------------
Shared Drive                 normally valid if SA has sufficient role
My Drive folder shared to SA  can read/create folders, but file upload may fail
Real-user OAuth in My Drive   valid if the user account has quota/permission
```

## Shared Drive cutover: separate agent health from legacy OAuth consumers

After an operation moves to a canonical Shared Drive, do not infer from a filename or 1Password item such as `ares-google-drive-oauth-client.json` that the owning agent is still using personal OAuth for its primary Drive workflow. First identify the **exact failing consumer** and its credential path.

A common mixed state is:

```text
Ares creative Drive operations   Service Account + Shared Drive   healthy
Legacy Google Sheets writers     user OAuth file                   may fail independently
```

Required checks:

1. Validate the agent's canonical Shared Drive root with its intended Service Account: HTTP 200, `driveId` present, and edit/add capabilities true.
2. Inspect the exact failing script and credential constant. Report it as a Sheet/report consumer when that is what failed; do not tell Rodolfo that “Ares needs Google authentication” merely because the reused OAuth file carries the Ares name.
3. Probe the exact spreadsheet with the Service Account on both surfaces:
   - Drive API metadata (`files.get`) for visibility and capabilities;
   - Sheets API (`spreadsheets.get`) for real API availability.
4. Treat Drive HTTP 200 / `canEdit=true` as insufficient proof that Sheets writes will work. If Sheets returns 403 saying `sheets.googleapis.com` is disabled in the Service Account project, the durable correction is to enable the Sheets API in that project and migrate the writer to Service Account auth. Moving the spreadsheet or reauthorizing personal OAuth alone does not enable the API.
5. Personal OAuth reauthorization may be used as an explicitly authorized short-term recovery when the blocked consumer must run immediately, but describe it as temporary compatibility—not as a requirement of the Shared Drive architecture.
6. After any auth recovery, rerun the **exact blocked consumer** in this order: credential refresh probe → bounded dry-run → apply → external Sheet/state readback. A healthy generic Drive watchdog is not sufficient evidence that the original cron recovered.

## Standard diagnostic sequence

For Hera/MGS quick checks, run the profile watchdog before deeper Drive debugging:

```bash
python3 /root/.hermes/profiles/hera/scripts/drive-auth-watchdog.py
python3 - <<'PY'
import json, datetime
p='/root/mgs-agent/data/hera/drive-auth-watchdog-state.json'
d=json.load(open(p)); s=d.get('signature',{})
print('healthy:', d.get('healthy'))
print('primary_credential:', d.get('primary_credential'))
print('fallback_degraded:', d.get('fallback_degraded'))
print('user:', s.get('user_ok'), s.get('user_state'), s.get('user_http'), s.get('user_error'))
print('service_account:', s.get('sa_ok'), s.get('sa_state'), s.get('sa_http'))
print('last_check:', datetime.datetime.fromtimestamp(d.get('last_check_ts')).isoformat() if d.get('last_check_ts') else None)
PY
```

Interpretation: empty stdout from `drive-auth-watchdog.py` is the healthy/silent path. Hera operational health means at least one real upload credential works. For personal My Drive destinations, Service Account may show folder capabilities but still be blocked for upload (`my_drive_sa_upload_blocked` / `storageQuotaExceeded_risk`); in that case `user_ok=true`, `token_ok`, and `primary_credential=user_oauth` is healthy. If OAuth is `invalid_grant`, generate/send the reauthorization link immediately instead of making Rodolfo ask. If the user asks “Drive auth is OK, right?”, answer from this watchdog/state rather than inferring from absence of logs.

1. Identify the auth mode used by the script:
   - Service Account JSON/JWT.
   - OAuth refresh token for a real user.
   - Domain-wide delegation (only if Workspace/admin configured).
2. Fetch destination root metadata with Drive API `files.get` using:
   - `supportsAllDrives=true`
   - fields: `id,name,driveId,ownedByMe,owners(emailAddress,displayName),capabilities(canAddChildren,canEdit,canModifyContent)`
3. Interpret `driveId`:
   - present = item is in a Shared Drive.
   - absent = item is in My Drive.
4. If Service Account + My Drive + upload needed, fail fast before downloading/processing large queues.
5. Check visible Shared Drives with `drives.list`; zero visible drives means the Service Account has not been added to any Shared Drive.
6. Only run a batch after a one-file smoke test uploads successfully and returns a destination file ID.

## Required preflight for batch upload scripts

Before the script downloads, sanitizes, transforms, or uploads queue items, add a destination preflight:

```text
Condition                                      Action
---------------------------------------------|---------------------------------------------
Service Account + destination has no driveId  stop with clear My Drive quota error
Shared Drive destination                       proceed to one-file smoke test
Real-user OAuth destination                    proceed if token and quota are valid
```

The error should be operational, not just raw HTTP:

```text
DESTINATION_BLOCKED_MY_DRIVE_SERVICE_ACCOUNT:
root '<folder name>' is a My Drive folder owned by <owner>.
Google Service Accounts do not have storage quota for file uploads in My Drive.
Move/use the folder in a Shared Drive or switch this script to real-user OAuth.
```

## Fix options

```text
Fix path                    Best use
--------------------------|--------------------------------------------------
Shared Drive               Best stable automation path for Service Account uploads
Real-user OAuth            Best when files must remain in a personal My Drive
Domain-wide delegation     Only for Workspace setups with admin approval
Manual upload              Last resort; avoid for large queues
```

For MGS creative pipelines, prefer Shared Drive when available because it keeps the agent as a technical operator without depending on a personal account session.

## MGS implementation pattern

For Ares creative Drive flows, keep raw uploaded assets immutable and upload only cleaned/final copies:

```text
Source/raw folder           Keep unchanged
Final/campaign folder       Upload cleaned copy after approval/preflight
Report CSV                  Record source ID, destination ID, hashes, status, error
Large run                   Resume-safe; skip already uploaded IDs
```

Use env overrides rather than hardcoding replacement folder IDs/auth choices when possible:

```text
ARES_DRIVE_ROOT_FOLDER_ID=<shared-drive-backed MGS-AGENTS/CRIATIVOS folder id>
ARES_DRIVE_OP_ITEM=<1Password Service Account item title if different>
ARES_DRIVE_AUTH_MODE=oauth              # when the destination must stay in personal My Drive
ARES_DRIVE_OAUTH_OP_ITEM="Google OAuth - Ares Drive"
```

If Rodolfo says the folder must stay in his personal Google Drive, stop pushing Shared Drive as the only path. Switch the recommendation to **real-user OAuth** using his current account quota. The durable setup is: OAuth client credentials + refresh token stored in 1Password, script refreshes access tokens at runtime, and the batch still uses the same one-file smoke-test gate before the full run.

OAuth setup pitfall validated on Google personal Drive: a **TVs and Limited Input devices** client may reject the full Drive scope with `invalid_scope` for device flow:

```text
https://www.googleapis.com/auth/drive      → invalid_scope in device flow
https://www.googleapis.com/auth/drive.file → device flow may start, but access is narrower
```

Operational handling:
1. Try the already-created device-flow client once more if Rodolfo asks; do not force a new client before verifying.
2. If only `drive.file` works, warn that it may upload new/app-created files but may not fully access an existing `MGS-AGENTS/CRIATIVOS` tree; validate with a one-file smoke test before full batch.
3. For one-person/personal Drive use, keep OAuth app in **Testing** and add Rodolfo's Google account as a Test user; do not push Production/verification unless the app is public.
4. If full-folder access is required and device flow rejects full Drive scope, fall back to **Desktop app OAuth** and a one-time manual browser/code exchange.
5. If Google approval succeeds but 1Password cannot update the item, save `refresh_token` to a root-only gitignored local secret file and teach the runtime loader to combine `client_id`/`client_secret` from 1Password with that local token.
6. Keep token handling secret: never paste `client_secret`, `refresh_token`, access token, or authorization URLs containing returned codes into Discord unless the code is explicitly safe/short-lived and the user needs to provide it.

When a Google Drive/Sheets-backed cron uses a local OAuth client token file, reauth must validate the exact runtime path, not a nearby service-account path. MGS example: `meta-app-roles-watch` reads `/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json`; after exchanging the Desktop OAuth code, validate refresh-token exchange, run the cron script itself, and inspect its state (`_sheet_removed_sync`) for real sheet read/write success. If sheet sync fails, treat it as alertable infrastructure failure, not a silent state-only warning.

Never print Service Account JSON, OAuth refresh tokens, access tokens, client secrets, or 1Password field values. Report only item names and non-secret metadata such as `len=X`.

## Validation checklist

- `py_compile` or syntax check passes for modified scripts.
- Destination preflight shows whether storage is Shared Drive or My Drive.
- Smoke test with `--limit 1 --max-errors 1` succeeds before full queue.
- If blocked, no report CSV/file writes are produced for the attempted run.
- For OAuth watchdog changes: simulate `invalid_grant` with a temp credential file, confirm the alert contains a reauthorization URL/instruction, confirm no `client_secret`/`refresh_token`/`access_token` markers, then run the real healthy watchdog and confirm stdout is empty.
- Audit log records the decision and evidence.
- Report to Rodolfo in concise executive format with `Próximo passo pendente:`.

## OAuth watchdog self-service reauthorization

When a Google Drive OAuth watchdog receives `invalid_grant`, do not frame it as fully auto-fixable. Google requires new human consent. The correct durable automation is self-service recovery: generate the Desktop OAuth URL in the alert, ask Rodolfo to approve and paste the final localhost URL/code, exchange it, store the new refresh token in the approved secret location, then validate with the watchdog.

See `references/drive-oauth-invalid-grant-self-service-reauth.md` for the implementation and smoke-test pattern.

## Enabling Google Workspace APIs from an OAuth flow

If a Drive-backed workflow needs a Google API that is disabled in the OAuth project (example: Sheets API disabled while Drive API works), do not assume Drive scope is enough. Enabling project services through Service Usage requires an access token with `https://www.googleapis.com/auth/cloud-platform` and a user/account that has permission on the Google Cloud project.

Operational pattern:

1. Try the target API and capture the exact disabled-service project number from the 403 message.
2. Attempt `serviceusage.services.enable` only if the token has cloud-platform scope.
3. If the token only has Drive scope, generate a reauth URL with both existing needed scopes and `cloud-platform`:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/cloud-platform`
4. Ask Rodolfo to approve and paste the localhost URL/code.
5. Exchange the code for a new refresh token and store it in the approved secret file without printing token values.
6. Enable the service, then poll Service Usage until `state=ENABLED`.
7. Validate the target API with a real write/readback; for Sheets, create/update tabs and confirm row counts.

Pitfall: a 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` from Service Usage is a scope issue, not proof that the account cannot enable the API. Reauth with `cloud-platform` before giving up.

A different 403, `PERMISSION_DENIED` with missing `serviceusage.services.enable`, is an **IAM permission problem**, even when the access token already has `cloud-platform`. Do not expand or replace a personal refresh token merely because the Service Account lacks this IAM role. Try the Service Account once, then use one of these approved gates:

1. an already-authorized GCP admin identity;
2. Rodolfo enabling the API from the direct Cloud Console library page for the exact project;
3. a separately confirmed admin OAuth flow when no admin session/identity exists.

API activation is separate from file sharing. `permissions.create(role=writer)`, Drive HTTP 200, and `canEdit=true` prove the identity can reach the file through Drive; they do **not** prove Sheets cell reads/writes. Do not switch a production consumer until all of these pass with the Service Account: Sheets metadata HTTP 200, bounded write, readback of the exact sentinel, restoration/clear, and readback of the original value. Keep OAuth as rollback; revoking/deleting the refresh token is a later credential-gated action, not part of ordinary script cutover.

## References

- `references/service-account-my-drive-quota.md` — concrete MGS/Ares incident pattern and reusable Drive API probes.
- `references/personal-my-drive-oauth-device-flow.md` — personal Google Drive OAuth setup notes, device-flow `invalid_scope` pitfall, `drive.file` limitation, and Desktop app fallback.
- `references/drive-oauth-invalid-grant-self-service-reauth.md` — watchdog pattern for `invalid_grant`: auto-generate reauth URL, keep healthy checks silent, validate no secret exposure.
- `references/google-sheets-balanced-column-distribution.md` — Sheets API pattern for filling/formatting a column while preserving group integrity (e.g. one mailbox per bot/site) and balancing group loads.
- `references/cross-agent-google-sheets-shared-drive-inventory-and-cutover.md` — inventory only the Sheets actually used by named agents, classify personal/shared/historical/stale, and cut over safely to Service Account + enterprise Shared Drive.
- `references/shared-drive-google-sheets-cluster-cutover.md` — dependency-graph audit for interdependent Sheets, conservative share+Service Account route, and transactional same-ID move gates for formula-heavy clusters.
