---
name: google-workspace
description: "MGS Google Drive and Sheets operations through the canonical mgs-core-prod Service Account."
---

# Google Workspace — MGS Canonical Route

For MGS Drive and Sheets, use only:

- project: `mgs-core-prod`;
- Service Account: `mgsagent@mgs-core-prod.iam.gserviceaccount.com`;
- 1Password item: `Google Service Account - MGS Agent`;
- helper: `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`;
- watchdog: `/root/mgs-agent/scripts/monitor-drive-auth-unified.py`.

Personal Google credential files, browser consent, local token caches and alternate identities are permanently retired and are not fallback paths. The bundled compatibility scripts fail closed. Gmail, Calendar, Contacts and other user-scoped operations remain blocked until Rodolfo approves a separate corporate identity architecture.

Before any Drive/Sheets write, validate exact file metadata, permission, API availability and perform readback. Existing My Drive Sheets may remain in place when shared with the canonical Service Account; new automated file uploads belong in `MGS-AGENTS`.
