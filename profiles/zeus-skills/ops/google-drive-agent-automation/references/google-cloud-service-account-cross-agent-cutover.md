# Google Cloud Service Account Cross-Agent Cutover

Use when MGS replaces a Google Cloud project, Service Account, OAuth identity, or human Google account used across multiple agents, Drive, Sheets, Gemini, monitors, and backups.

## Identity facts to establish first

```text
Project display name   editable label
Project ID             globally unique, permanent, embedded in resource names
Project number         numeric API/billing identifier
Service Account email  <account-id>@<project-id>.iam.gserviceaccount.com
```

Before creating credentials, verify the Project ID is acceptable. A clean display name does not prevent a random permanent Project ID from appearing in every Service Account email.

A Service Account is a machine identity, not a Workspace mailbox. Human administration remains with the approved Workspace account.

## Safe cutover order

1. Record the new project ID/number, Service Account email, owning organization, canonical Drive ID, and intended APIs.
2. Enable required APIs in the new project.
3. Create the Service Account. Leave project IAM roles blank initially unless an API consumer proves a project-level permission is required.
4. Grant file/Shared Drive access separately. Project IAM does not grant Drive-file access.
5. Store the JSON in 1Password and validate only non-secret metadata: item title, project ID, client email, private-key presence, and key-ID presence.
6. Mint a token and perform read-only Drive/Sheets metadata checks with the new identity before changing runtime defaults.
7. Inventory every active consumer by item name, OAuth path, environment override, cron/job, script, live-profile mirror, and backup config. A credential named after one agent may be consumed by Finance, Sheets, monitors, backups, or other agents.
8. Migrate consumers and run bounded canaries before removing old credentials or memberships.
9. Remove old operational secrets/jobs/access only after exact-consumer readback passes. Preserve append-only audit logs, imported threads, migration manifests, and non-secret historical evidence.
10. Regenerate inventory, append audit, update the initiative checkpoint, and send REPORT-INFRA.

## 1Password storage pitfall

Many MGS loaders inspect `item.fields[*].value` for JSON containing both `private_key` and `client_email`. A JSON file attached to an item can exist and still be invisible to those loaders.

Preflight the item structure without printing values:

- item exists in the runtime-accessible vault;
- expected concealed/text field has a value;
- field length is plausible;
- parsed JSON has the exact `client_email` and `project_id`;
- private key and private-key ID are present;
- attachment-only storage is reported as incompatible unless the loader explicitly downloads attachments.

Prefer a concealed field for the JSON. An attachment may remain as backup, but do not assume it is runtime-readable.

## Shared Drive role parity

When replacing a production identity, first read the old participant role and required capabilities. Match role parity during cutover when deletion, movement, or member administration is part of the workflow. For Google Drive API values, `organizer` corresponds to Shared Drive Manager.

Do not infer role from a prior recommendation. Validate live membership and capabilities such as `canAddChildren`, `canEdit`, and `canModifyContent`.

## Service Usage Consumer gate

Drive/Sheets metadata may succeed without a quota-project header while production consumers fail when they send:

```text
x-goog-user-project: <project-id>
```

A 403 stating that the caller lacks permission to use the project means the Service Account needs the least-privilege role:

```text
roles/serviceusage.serviceUsageConsumer
```

Test both layers separately:

1. without quota header — proves API enablement and file-level access;
2. with quota header — proves `serviceusage.services.use` for the exact production path.

Do not grant Owner, Editor, or Service Usage Admin merely to solve this consumer gate.

## OAuth-to-Service-Account conversion

Before deleting a personal OAuth item or local refresh-token file:

- find consumers that are Service Account primary with OAuth fallback;
- find consumers that are OAuth-only;
- convert OAuth-only Sheets writers to the canonical Service Account helper;
- validate each exact spreadsheet by Drive metadata and Sheets API;
- run bounded dry-run/apply/readback for the original cron or script;
- remove disabled OAuth watchdog jobs and local token backups only under the deletion confirmation gate.

If the OAuth client project is already deleted, treat OAuth as unavailable, not as rollback.

## Direct cutover versus rollback

Rollback is preferred while both identities work. If the owner explicitly chooses a clean direct cutover and the old path is already broken, do not insist on reactivating it. Instead:

1. keep destructive deletion paused;
2. validate the new credential read-only;
3. run the smallest write/readback canary;
4. switch exact consumers;
5. remove old artifacts only after the new path passes.

Never call a missing or inaccessible old credential a working rollback.

## Gemini/API-key boundary

Drive/Sheets Service Account migration does not migrate a Gemini/Generative Language API key. Treat API keys as a separate consumer class:

1. create a key in the new project;
2. restrict it to the intended API when supported;
3. store it in a distinct 1Password item;
4. run a real minimal generation canary;
5. update consumers;
6. revoke the old key only after the canary and billing/quota checks pass.

Changing billing remains a separate critical gate.

## Destructive-scope confirmation

A request to “move the Service Account” does not automatically authorize deleting every old project, key, OAuth token, membership, local secret file, or historical record. If scope expands, inventory exact targets and obtain a new critical confirmation naming:

- projects and service accounts;
- 1Password items;
- local secret paths and backups;
- Drive memberships;
- disabled jobs/crons;
- API keys;
- artifacts preserved as audit/history;
- billing explicitly excluded or separately confirmed.
