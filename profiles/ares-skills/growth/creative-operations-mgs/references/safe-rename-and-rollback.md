# Safe Rename and Rollback — Creative Assets

## Scope

Use this procedure when renaming existing creative assets across Google Drive, local working copies, and the canonical Ares inventory. It governs transport and rollback only. Naming codes and inventory fields remain owned by `creative-taxonomy-mgs`; campaign eligibility remains governed by Creative Ops → Campaign Ops reconciliation.

## Preconditions

- Confirm Rodolfo authorized the exact asset set and rename scope.
- Load `creative-taxonomy-mgs` and derive the target names from its current taxonomy.
- Inspect each real media file; do not infer placement or person classification from the old name alone.
- Resolve the canonical inventory record and Drive object ID for every asset.
- Record independent mappings for local and Drive state; names may already differ.
- Keep `reservation_status` and `ares_eligible` unchanged unless separately authorized.

## Read-only preflight

For every asset, capture:

- asset ID and lineage IDs;
- local path/name, size, dimensions and SHA-256;
- Drive object ID, current name, parent and rename capability;
- canonical inventory filename and current status;
- proposed local and Drive names;
- collision checks in both namespaces.

Abort before writes if an object is missing, ambiguous, not renameable, collides with another target, or cannot be tied to one canonical inventory record.

## Backup and plan

1. Save the deterministic rename plan and preflight evidence outside mutable asset directories.
2. Back up every mutable local inventory/config file.
3. Preserve historical audit records unchanged; the new event records `old_name → new_name`.
4. Define the reverse mapping before the first write.
5. Do not include deletions, moves, eligibility changes, taxonomy changes or campaign writes in a rename authorization.

## Transactional execution

1. Rename Drive objects one at a time with PATCH.
2. Immediately GET each object and verify ID, name and parent.
3. Track every confirmed remote rename in execution order.
4. Rename local files with no-clobber collision checks.
5. Verify each local SHA-256 is unchanged after rename.
6. Update only the canonical operational inventory using an atomic validated write.
7. Append a reconciliation/audit event containing both old and new names and readback evidence.
8. Re-read Drive, local paths and inventory before declaring success.

## Rollback

If any remote, local, inventory or readback step fails:

1. Stop the forward operation.
2. Restore the inventory/config backup atomically if it was changed.
3. Reverse local renames in reverse execution order and verify hashes.
4. Reverse confirmed Drive renames in reverse execution order, with GET after every rollback PATCH.
5. Preserve the failed execution record; never rewrite historical evidence to look successful.
6. Report partial rollback or ambiguous state explicitly and block campaign use until reconciled.

## Verification

- [ ] Every target has one local source, one Drive ID and one canonical inventory record.
- [ ] Target names come from `creative-taxonomy-mgs`.
- [ ] No local or remote collision exists.
- [ ] Drive PATCH has matching GET readback per asset.
- [ ] Local hashes are unchanged.
- [ ] Canonical inventory parses and contains each active asset exactly once.
- [ ] Historical records are unchanged; a new audit event was appended.
- [ ] Reservation and `ares_eligible` values are unchanged unless separately authorized.
- [ ] Rollback path was defined before writes and any rollback was validated by readback.
