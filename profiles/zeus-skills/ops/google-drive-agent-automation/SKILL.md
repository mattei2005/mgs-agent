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

## Executive rule

Do **not** treat Drive `canAddChildren=true`, `canEdit=true`, or successful folder creation as proof that uploads will work. For Google Service Accounts, upload viability depends on destination storage model:

```text
Destination type              Service Account upload outcome
----------------------------|----------------------------------------------
Shared Drive                 normally valid if SA has sufficient role
My Drive folder shared to SA  can read/create folders, but file upload may fail
Real-user OAuth in My Drive   valid if the user account has quota/permission
```

## Standard diagnostic sequence

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

Use env overrides rather than hardcoding replacement folder IDs when possible:

```text
ARES_DRIVE_ROOT_FOLDER_ID=<shared-drive-backed MGS-CRIATIVOS folder id>
ARES_DRIVE_OP_ITEM=<1Password item title if different>
```

Never print Service Account JSON, OAuth refresh tokens, access tokens, or 1Password field values. Report only item names and non-secret metadata.

## Validation checklist

- `py_compile` or syntax check passes for modified scripts.
- Destination preflight shows whether storage is Shared Drive or My Drive.
- Smoke test with `--limit 1 --max-errors 1` succeeds before full queue.
- If blocked, no report CSV/file writes are produced for the attempted run.
- Audit log records the decision and evidence.
- Report to Rodolfo in concise executive format with `Próximo passo pendente:`.

## References

- `references/service-account-my-drive-quota.md` — concrete MGS/Ares incident pattern and reusable Drive API probes.
