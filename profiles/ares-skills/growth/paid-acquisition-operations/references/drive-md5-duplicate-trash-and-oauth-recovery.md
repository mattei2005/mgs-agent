# Drive MD5 duplicate cleanup — canonical authorization

Use when Ares must identify duplicate Drive files and trash only the copies explicitly authorized by scope.

## Procedure

1. Use the canonical `mgs-core-prod` Service Account only.
2. Query exact file metadata with `supportsAllDrives=true` and require Shared Drive membership plus `canTrash=true` for the target.
3. Group candidates by byte size and MD5 where available; retain the approved canonical file.
4. Produce a dry-run list with file IDs, paths, checksums and proposed action.
5. Require the applicable destructive confirmation before trashing.
6. Trash the smallest authorized batch and read back `trashed=true` for every file.
7. If capability is missing, stop and correct the Shared Drive role through the approved admin path. Do not change identity.

No local Google credential, browser consent or alternate auth selector is valid in MGS production.
