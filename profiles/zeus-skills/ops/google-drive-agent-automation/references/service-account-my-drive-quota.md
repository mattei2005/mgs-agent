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

End reports with the concrete pending choice/action, e.g.:

```text
Próximo passo pendente: escolher Shared Drive ou OAuth; depois eu rodo smoke test de 1 arquivo e só então libero a fila completa.
```
