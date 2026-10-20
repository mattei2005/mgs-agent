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

## Storage-capacity and migration assessment

1. Establish the current storage type through the canonical helper, using a read-only Drive scope for diagnosis. Read `drives.get(driveId, fields=id,name,restrictions)` and `files.get(fileId, supportsAllDrives=true, fields=id,name,driveId,capabilities)`. A root named `Drive` is not evidence of My Drive; use the actual `driveId` and `drives.get` identity.
2. Separate permission, ownership and capacity. Sharing a Shared Drive with a personal account or adding a shortcut does not move its storage consumption to that account. For My Drive, new files ordinarily belong to the creating identity, not the parent folder's owner; granting the Service Account Editor access does not let its new uploads consume the folder owner's personal subscription. Distinguish reading/downloading and permitted edits of existing files from creating new binaries or copies. Never broaden this upload limitation into a claim that the Service Account cannot access My Drive at all.
3. Treat a move, copy, ownership transfer and shortcut as different operations. Check the exact source/destination and Google organization restrictions before claiming a move is supported. Copies create new IDs; moving or transferring a folder alone does not prove child ownership, storage attribution or consumer compatibility. Do not present manual archiving as a complete automatic solution until future archive writes and retrieval through recorded lineage are designed and tested.
4. Check capacity before redesigning authentication. In Admin Console, inspect **Billing > Subscriptions** for the actual edition, license count and commitment, and **Storage** for pooled capacity, usage and user/Shared Drive limits. A displayed limit alone does not identify the edition or total organizational capacity. If the account-specific console was not inspected, state that gap rather than claiming a purchase is available to this tenant.
5. Compare an edition upgrade with the **Google Workspace Additional Storage** add-on using current official sources. Include pooled storage per licensed user, total recurring cost for the affected subscription, region/currency, promotional versus ongoing pricing and contractual commitment. Monthly payment does not necessarily mean a cancellable monthly contract. Do not hard-code prices into this reference or assume storage from a personal Google subscription can be pooled into Workspace.
6. Prefer expansion of the existing Workspace when it meets the need, because it avoids moving files and changing IDs or authentication. Present the technical conclusion first, the concrete affected operation second, and the least-disruptive recommendation third. For a follow-up asking why sharing is insufficient, explain the creator-versus-folder-owner distinction directly rather than repeating a broad migration warning.
7. Keep assessment read-only. Billing, ownership, permissions and authentication changes need their applicable approval gates. If an isolated architecture is later approved, inventory consumers and lineage, define rollback, run one bounded write/readback/recovery canary, and validate the exact consumers before claiming equivalent operation.

### Official sources to refresh

- Shared Drive ownership and pooled storage: https://developers.google.com/workspace/drive/api/guides/about-shareddrives
- Service Account storage limitations and quota errors: https://developers.google.com/workspace/drive/api/guides/handle-errors#storageQuotaExceeded
- Ownership-transfer constraints: https://support.google.com/drive/answer/2494892 and https://developers.google.com/workspace/drive/api/guides/transfer-file
- Extra Workspace storage eligibility, purchasing and commitment: https://support.google.com/a/answer/12284220
- Current edition capacity and public prices: https://workspace.google.com/pricing.html

## Operational error

```text
DESTINATION_BLOCKED_MY_DRIVE_SERVICE_ACCOUNT:
The selected folder is outside a Shared Drive and cannot receive automated file uploads with the canonical Service Account. Use MGS-AGENTS. Existing Sheets may be shared directly with the canonical Service Account.
```
