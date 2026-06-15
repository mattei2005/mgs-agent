# Drive MD5 duplicate trash + OAuth recovery

Use when Rodolfo approves deleting duplicate creatives from `MGS-CRIATIVOS`.

## Scope

- Treat `UPLOAD_CANVAS` as RAW/original and do not delete from it unless Rodolfo explicitly names RAW deletion.
- For organized copies (`01_READY_CANDIDATE`, `00_REVIEW`, etc.), exact `md5Checksum` duplicates can be reduced to one keeper per MD5 group after approval.
- Keep one file per MD5 group. Prefer keeper order:
  1. `01_READY_CANDIDATE` over `00_REVIEW`
  2. canonical MGS filename over non-canonical filename
  3. oldest created file when otherwise tied

## Safe execution pattern

1. Generate a fresh Drive inventory with `trashed=false`.
2. Build `md5-duplicate-trash-plan.csv` with: `drive_id`, `path`, `md5Checksum`, `keep_drive_id`, `keep_path`, `reason`.
3. Simulate that every duplicate has exactly one keeper before write.
4. Trash duplicates using Drive API PATCH `{ "trashed": true }`, not hard delete.
5. Write `md5-duplicate-trash-report.csv` with: `status`, `verified_trashed`, `drive_id`, `path`, `keep_drive_id`, `error`.
6. Re-scan Drive and validate duplicate MD5 groups are gone from the organized scope.

## Permission/OAuth recovery

Google Drive can allow `canEdit=true` and `canModifyContent=true` while blocking delete/trash with:

```text
canTrash=false
canDelete=false
ownedByMe=false
HTTP 403: The user does not have sufficient permissions for this file.
```

When this happens:

1. Fetch file capabilities for a representative duplicate and report only sanitized fields (`canTrash`, `canDelete`, `ownedByMe`, owner display name if useful; never credentials).
2. Retry using real-user OAuth mode (`ARES_DRIVE_AUTH_MODE=oauth`) if a valid refresh token exists.
3. If OAuth refresh returns `invalid_grant` / token expired or revoked, try the non-interactive device flow only if the OAuth client type supports it.
4. If device flow returns `invalid_client` / invalid client type, use desktop OAuth URL generation. This requires the Drive owner to approve in Google and return only the short-lived `code` or final localhost redirect URL.
5. Do not claim deletion is complete until Drive API verifies `trashed=true` and a fresh scan confirms duplicates are gone.

## Communication pitfall

If Rodolfo pushes for autonomy, keep the operational line clear: the agent should do every automatable step (plan, attempt, capability check, OAuth path selection, report) but cannot bypass Google owner consent when the current credential has `canTrash=false` and OAuth is revoked. Phrase this as an authorization boundary, not a lack of willingness.
