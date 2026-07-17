# Service Account Sheets API enablement and consumer IAM

Use when Drive access succeeds for a Service Account but Google Sheets API calls still return HTTP 403.

## Two independent authorization layers

1. **API enabled in the consumer project**
   - Enable `sheets.googleapis.com` in the exact project number named by the 403.
   - A Service Account commonly cannot enable its own project service unless it has `serviceusage.services.enable`; use an authorized administrator or the direct Cloud Console API-library page.
2. **Caller allowed to consume enabled services**
   - The Service Account needs `serviceusage.services.use` on the consumer project.
   - Grant least privilege: `roles/serviceusage.serviceUsageConsumer`.
   - Do not grant Service Usage Admin merely to run Sheets API calls.

File-level sharing is a third, separate layer: the Service Account also needs `writer` (or the minimum required role) on the spreadsheet or membership in its Shared Drive.

## Diagnostic sequence

1. Confirm Drive API `files.get` returns HTTP 200 plus `canEdit=true` and `canModifyContent=true`.
2. Call Sheets `spreadsheets.get` with a Service Account token.
3. If the response says the API is disabled/recently enabled, confirm the API is enabled in Cloud Console and allow a short propagation window.
4. If ambiguity remains, repeat once with `x-goog-user-project=<consumer-project-number>`:
   - missing `serviceusage.services.use` / “Caller does not have required permission to use project” means the API can be enabled while caller-consumer IAM is still absent;
   - grant **Service Usage Consumer** to the Service Account, then wait for IAM propagation.
5. Require Sheets metadata HTTP 200 before modifying runtime auth.

Do not loop indefinitely on the generic disabled-service 403. The explicit quota-project probe is the discriminator between activation state and consumer IAM.

## Safe cutover after HTTP 200

1. Pick a blank, unprotected cell outside the used range on a low-risk canary spreadsheet.
2. Capture the original formula/value and relevant grid/protection metadata.
3. Write a unique sentinel with the Service Account.
4. Read back the exact sentinel.
5. Restore the exact original state (clear only if the original cell was blank).
6. Read back again and require exact restoration.
7. Add a selectable `oauth`/`service_account` auth mode to consumers while keeping OAuth as the default during staging.
8. Switch one consumer at a time, run its exact dry-run/apply path, and validate external Sheet/state readback.
9. Keep OAuth as rollback. Revocation or deletion of its refresh token is a separate credential-critical confirmation.

## Reporting

Report each layer independently:

- file permission: pass/fail;
- Drive API capability: pass/fail;
- Sheets API enabled: pass/fail;
- Service Usage Consumer IAM: pass/fail;
- canary write/readback/restore: pass/fail;
- active consumers switched: count;
- OAuth retained as rollback: yes/no.
