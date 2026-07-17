# Service Account and My Drive quota — MGS canonical rule

Google Service Accounts do not have personal Drive storage quota. Folder visibility or `canAddChildren=true` in a shared My Drive folder does not prove binary upload viability.

## MGS production behavior

- Existing Google Sheets may remain in My Drive when directly shared with `mgsagent@mgs-core-prod.iam.gserviceaccount.com`; preserve IDs, Forms, formulas and `IMPORTRANGE`.
- New automated file uploads must target `MGS-AGENTS` and have a real `driveId`.
- Consumers use only `service_account` and fail closed on every other selector.
- Do not solve My Drive quota by changing identity.

## Preflight

1. Fetch root/file metadata with `supportsAllDrives=true`.
2. For uploads require `driveId`, `canAddChildren`, `canEdit` and `canModifyContent`.
3. For an existing Sheet require Drive HTTP 200, Sheets HTTP 200 and `canEdit=true`.
4. Run a one-item or one-cell write/readback/restore canary.
5. Stop before downloading or processing a queue if the destination is a My Drive folder.

## Operational error

```text
DESTINATION_BLOCKED_MY_DRIVE_SERVICE_ACCOUNT:
The selected folder is outside a Shared Drive and cannot receive automated file uploads with the canonical Service Account. Use MGS-AGENTS. Existing Sheets may be shared directly with the canonical Service Account.
```
