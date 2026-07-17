# Replacing a Shared Drive Service Account safely

Use this procedure when replacing an active MGS Google Drive/Sheets Service Account with a new identity or moving it to a new Google Cloud project.

## Identity model

Keep these separate:

- Human/Workspace administrator: manages the Cloud project and Shared Drive.
- Google Cloud project: supplies API enablement, quota/consumer context, and the Service Account namespace.
- Service Account: machine identity; its email is `<account-id>@<project-id>.iam.gserviceaccount.com`.
- Shared Drive membership: grants file/drive access independently of project IAM.

The visible project name does not determine the Service Account email. The immutable project ID does. Confirm the project ID before creating credentials.

## Safe sequence

1. Create the target project under the intended Workspace organization.
2. Enable Drive API and, when needed, Sheets API.
3. Create the new Service Account without broad project roles. Do not grant Owner or Editor.
4. Read the active Shared Drive membership and capabilities with the current credential.
5. Add the new Service Account to the Shared Drive. During replacement, match the old identity's real Drive role for parity; MGS full-operation flows that require member-equivalent `organizer` capabilities use the UI role `Manager`.
6. Keep the old Service Account until the new identity has passed credential, token, Shared Drive, and bounded write/readback checks. If Rodolfo explicitly chooses a direct cutover, state that there is no rollback and that the old runtime can remain unavailable until the new credential is installed.
7. Store the new JSON credential in the approved 1Password vault. Never send it through Discord or email.
8. Validate in this order before changing production config:
   - expected `client_email` and `project_id`;
   - private key fields present without printing values;
   - token mint succeeds;
   - Shared Drive root returns HTTP 200 and a `driveId`;
   - membership role/capabilities match the required operation;
   - one bounded write/readback canary succeeds.
9. Change the runtime credential reference only after the preflight. Keep the old credential as rollback until post-cutover monitoring passes; revocation/deletion is a separate credential-gated action.

## 1Password storage compatibility

Before assuming an item is usable, distinguish item visibility from payload compatibility:

- The runtime Service Account loader used by MGS scans item field values for JSON containing both `private_key` and `client_email`.
- A JSON file attached to a 1Password item can be present and valid while the loader still reports `service account JSON not found`.
- For the current field-scanning loader, place the complete JSON in a concealed field such as `credential`/`credencial` (or in a field the loader explicitly supports). An attachment may remain as backup.
- Validate only safe metadata: item title/vault, field labels/types, value presence/length, attachment name/size, expected `client_email`, and expected `project_id`. Never print the private key, token, or full JSON.
- If attachment-only storage is desired, update and test the loader to retrieve the attachment explicitly rather than assuming attachments appear in `fields`.

## Diagnostic pitfalls

- A Drive `404 File not found` or `Shared drive not found` from a credential often means that identity cannot see the Shared Drive; it does not prove the Drive was deleted.
- Before attributing the failure, print only the active credential's non-secret `client_email` and `project_id`. A nearby OAuth filename or item title is not proof of the runtime identity.
- Test file metadata, Shared Drive metadata, and permissions separately. If all return 404 for the same identity while another administrator can see the Drive, treat it as membership/access loss.
- A user OAuth fallback can fail independently because its OAuth consumer project was deleted or disabled. Do not infer that the Shared Drive or primary Service Account is unhealthy from that fallback alone.
- Project IAM roles and Shared Drive roles solve different problems. Leave broad IAM roles blank at Service Account creation; grant `Service Usage Consumer` only when the exact API probe proves `serviceusage.services.use` is missing.
