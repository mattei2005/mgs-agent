# Scoped groups: Campanhas / Landing Pages

Read `docs/mgs-router-scoped-groups.md` and `data/mgs-router-scoped-groups-validation.json` for current UI/schema. This supersedes global shared-group semantics in the catalog/DNS/group-edit history only; preserve traffic, session, indexing and DNS decisions.

- Use `group_schema:2`, mandatory `route_groups` and `destination_groups` arrays (including empty arrays), `catalog`, `routes` and current `revision` in every config write. Reject legacy payloads/downgrades after migration; never merge the registries again to make an old importer work.
- Scope group create/rename/delete, uniqueness checks, filters, editor pickers and counts to the active area. Equal names across areas are valid. Rename/delete modifies only that area's memberships atomically; deleting a group clears membership and never deletes routes, URLs, IDs, snapshots or weights.
- Preserve existing memberships/names when migrating. Copy legacy names to both scopes once; retain intentionally empty groups. Do not reset names from an old source snapshot or claim exact Keitaro group attribution without source evidence.
- Keep Grupos in each area's toolbar and use a scoped dialog; no global Grupos tab. Verify counts against real area records, clickable count filters, Create, rename/cancel, delete/cancel, Escape, reload and mobile document width.
- In fixtures, await the real group name instead of one `<tr>`: the empty placeholder also counts as one. Treat an omitted empty catalog as an empty array in group operations; never assume `omitempty` emitted it.
- Exercise same-name cross-scope independence and stale revisions locally. Production browser QA opens/cancels editors/deletion and must assert zero route/group POSTs; never mutate an operator group just to test.
- Use the schema-aware canonical verifier; `tests/public_scoped_groups_smoke.py` is the current public UI test. Previous one-shot retirement receipts/scripts remain historical, not replayable after schema migration.
- Preserve and check a private rollback binary/state pair. Old binary alone cannot read schema2 memberships; rollback requires reconciled state too. Never overwrite intervening operator edits. Executor is one-approval/one-receipt fail-closed, not a reusable generic deploy.
- Distinguish an unchanged verification cache at deployment from the later canonical verifier refreshing live checks/timestamps. A green saved observation still is not continuous monitoring.
