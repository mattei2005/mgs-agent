# Service Account + My Drive quota pitfall

## Incident pattern

A Google Service Account shared into a normal **My Drive** folder can successfully:

- read files,
- download files,
- inspect folder metadata,
- create child folders,
- show Drive capabilities like `canAddChildren=true`, `canEdit=true`, and `canModifyContent=true`,

but still fail on file upload with:

```text
Google Drive 403 storageQuotaExceeded
Service Accounts do not have storage quota.
Leverage shared drives, or use OAuth delegation instead.
```

Operational translation: the Service Account has permissions on the folder, but no usable storage quota for file ownership in that My Drive context.

## Metadata probe

Use `files.get` for the root destination folder. The durable discriminator is `driveId`:

```text
Field       Meaning
----------|--------------------------------------------------
driveId    present = Shared Drive; absent = My Drive
owners     useful to identify the My Drive owner for the report
capabilities useful but not sufficient to prove upload viability
```

Recommended fields:

```text
id,name,driveId,ownedByMe,owners(emailAddress,displayName),capabilities(canAddChildren,canEdit,canModifyContent)
```

Always include:

```text
supportsAllDrives=true
```

## Shared Drive visibility probe

Use Drive API `drives.list` with the same credential. If it returns zero drives, the Service Account has not been added to any Shared Drive visible to that credential.

## Fail-fast script pattern

Do this before any heavy or side-effectful work:

```python
def preflight_destination(drive, root_folder_id):
    meta = drive.files_get(
        root_folder_id,
        fields="id,name,driveId,ownedByMe,owners(emailAddress,displayName),capabilities(canAddChildren,canEdit,canModifyContent)",
        supports_all_drives=True,
    )
    if using_service_account and not meta.get("driveId"):
        owner = ", ".join(o.get("emailAddress", "") for o in meta.get("owners", [])) or "unknown owner"
        raise RuntimeError(
            "DESTINATION_BLOCKED_MY_DRIVE_SERVICE_ACCOUNT: "
            f"root '{meta.get('name', root_folder_id)}' is a My Drive folder owned by {owner}. "
            "Google Service Accounts do not have storage quota for file uploads in My Drive. "
            "Move/use the folder in a Shared Drive or switch to real-user OAuth."
        )
    return meta
```

## Ares/MGS creative flow notes

Validated in the Ares creative cleanup/copy pipeline:

```text
Script                                      Purpose
------------------------------------------|---------------------------------------------
/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py
                                            queue runner: download → sanitize → verify → upload
/root/mgs-agent/scripts/clean-creative-metadata.sh
                                            central sanitizer/verify wrapper
```

The safe pattern is:

```text
UPLOAD_CANVAS/raw assets      keep intact; do not overwrite/move/delete
Clean/final creative copy     upload to final folder only after preflight passes
Report CSV                   append source/dest IDs, hashes, status, error
```

If the current destination is My Drive, do not keep retrying uploads. Create/move to Shared Drive or configure OAuth, then run a one-file smoke test before the full queue.

## Personal Google Drive OAuth pattern

When Rodolfo confirms there is no Workspace/Shared Drive option and the files must remain in a personal Drive, the correct fix is **real-user OAuth**, not more Service Account permission changes.

Runtime pattern:

```text
ARES_DRIVE_AUTH_MODE=oauth
ARES_DRIVE_OAUTH_OP_ITEM=<1Password item containing OAuth fields>
```

1Password item fields expected:

```text
client_id
client_secret
refresh_token
```

Recommended authorization flow for a headless VPS:

1. Create a Google OAuth client suitable for limited-input/device authorization if available.
2. Store `client_id` and `client_secret` in 1Password; never paste them in Discord.
3. Run a helper that prints only the Google verification URL/code.
4. Rodolfo approves Drive access in his browser with the personal account that owns the folder.
5. Helper saves `refresh_token` back into 1Password without printing it.
6. Batch script refreshes access tokens at runtime and proceeds against the same My Drive folder.

If Google Cloud does not offer device-flow client type in the project, fallback is Desktop OAuth plus one-time manual/loopback auth-code exchange. The durable rule is the same: tokens go to 1Password, not chat/logs; report only item title and `len=X`.

After OAuth is configured, validate in this order:

```text
Step                         Expected result
---------------------------|-----------------------------------------------
py_compile/script syntax     OK
OAuth token refresh          access token obtained, token not printed
Drive files.get root         storage=my_drive, auth_mode=oauth
--limit 1 smoke test         1 cleaned file uploaded, destination ID recorded
Full queue                   run only after smoke test passes
```

## User-facing recommendation

For Rodolfo, summarize as:

```text
Opção                         Veredito
-----------------------------|-----------------------------------------------
Shared Drive                  melhor para automação estável com Service Account
OAuth de usuário real          melhor se precisa ficar no Drive pessoal
Service Account em My Drive    não resolve upload
Manual                         evitar em lote grande
```

End reports with the concrete pending action. If Shared Drive is still an option:

```text
Próximo passo pendente: escolher Shared Drive ou OAuth; depois eu rodo smoke test de 1 arquivo e só então libero a fila completa.
```

If Rodolfo already confirmed it must stay in personal Google Drive:

```text
Próximo passo pendente: criar/configurar o OAuth client, salvar client_id/client_secret no 1Password, aprovar o device/consent flow, validar refresh token e rodar smoke test de 1 arquivo.
```
