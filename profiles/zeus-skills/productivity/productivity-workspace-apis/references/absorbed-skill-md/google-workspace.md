# Google Workspace — MGS canonical route

The former generic personal-credential procedure is disabled for all MGS profiles.

## Drive and Sheets

Use only:

- project `mgs-core-prod`;
- Service Account `mgsagent@mgs-core-prod.iam.gserviceaccount.com`;
- 1Password item `Google Service Account - MGS Agent`;
- helper `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`;
- watchdog `/root/mgs-agent/scripts/monitor-drive-auth-unified.py`.

Validate the exact Drive file and Sheet, then use bounded write/readback/restore canaries. Existing operational Sheets may remain in My Drive when shared directly with the canonical Service Account; new automated uploads use `MGS-AGENTS`.

## User-scoped services

Gmail, Calendar, Contacts and other user-scoped operations are blocked in MGS profiles until Rodolfo approves a separate corporate identity architecture. Do not create local Google credentials or use browser consent as a workaround.

The compatibility scripts under `scripts/google-workspace/` intentionally fail closed or run only the canonical Service Account health check.
