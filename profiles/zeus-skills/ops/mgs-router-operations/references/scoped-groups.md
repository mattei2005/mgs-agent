# Scoped groups: Campanhas / Landing Pages

Read `docs/mgs-router-scoped-groups.md` and `data/mgs-router-scoped-groups-validation.json` for current UI/schema. This supersedes global shared-group semantics in the catalog/DNS/group-edit history only; preserve traffic, session, indexing and DNS decisions.

- Current bulk/state/pagination behavior: `references/bulk-actions-pagination.md` / `docs/mgs-router-bulk-actions-pagination.md`. Preserve `action_schema:1` and disabled flags as well as scoped metadata.
- Use `group_schema:2`, mandatory `route_groups` and `destination_groups` arrays (including empty arrays), `catalog`, `routes` and current `revision` in every config write. Reject legacy payloads/downgrades after migration; never merge the registries again to make an old importer work.
- Scope group create/rename/delete, uniqueness checks, filters, editor pickers and counts to the active area. Equal names across areas are valid. Rename/delete modifies only that area's memberships atomically; deleting a group clears membership and never deletes routes, URLs, IDs, snapshots or weights.
- Preserve existing memberships/names when migrating. Copy legacy names to both scopes once; retain intentionally empty groups. Do not reset names from an old source snapshot or claim exact Keitaro group attribution without source evidence.
- Keep Grupos in each area's toolbar and use a scoped dialog; no global Grupos tab. Verify counts against real area records, clickable count filters, Create, rename/cancel, delete/cancel, Escape, reload and mobile document width.
- In fixtures, await the real group name instead of one `<tr>`: the empty placeholder also counts as one. Treat an omitted empty catalog as an empty array in group operations; never assume `omitempty` emitted it.
- Exercise same-name cross-scope independence and stale revisions locally. Production browser QA opens/cancels editors/deletion and must assert zero route/group POSTs; never mutate an operator group just to test.
- Use the schema-aware canonical verifier; `tests/public_scoped_groups_smoke.py` is the current public UI test. Previous one-shot retirement receipts/scripts remain historical, not replayable after schema migration.
- Preserve and check a private rollback binary/state pair. Old binary alone cannot read schema2 memberships; rollback requires reconciled state too. Never overwrite intervening operator edits. Executor is one-approval/one-receipt fail-closed, not a reusable generic deploy.
- Keep the canonical public verifier read-only: resolve credentials through `mgs-op-with-service-account.sh`, consume saved `/api/domains` checks, and label them saved observations rather than fresh online probes. Only the operator Verificar action POSTs and updates timestamps. Do not fix missing CLI environment by rotating credentials or refresh checks incidentally during UI validation. A green saved observation still is not continuous monitoring.

## Independent domain scope

Current source: `docs/mgs-router-domain-layout-top-pagination.md` and `data/mgs-router-domain-layout-validation.json`.

- Persist domain-only groups in `domains.json` under its own revision, `group_schema:1`, `domain_groups`, and host-keyed `metadata:{id,group}`. Route schema2 and domain schema1 belong to separate stores; never conflate them.
- Preserve the additive domain registry, existing host IDs and all memberships on writes. Server assigns new IDs; reject ID edits, duplicate IDs, unknown groups, corrupt persisted metadata, stale revisions and schema downgrades. Startup of legacy data must not write/migrate silently.
- On an explicitly authorized all-current-domain association, reconcile the union of registered names and current campaign hosts first; some live hosts may only exist through routes. Persist the exact union without adding screenshot domains. The approved migration associated 19 current hosts with `MGS`.
- Use a separate Domínios group modal, real member counts, domain group filter/search, selected-visible assignment and 30-item synchronized top/bottom paging. Create/rename/remove group must not modify routes, DNS, SSL or check timestamps; group removal only clears membership. Domain deletion stays blocked.
- Treat Keitaro screenshots as visual references only. Show real saved status/timestamp, real campaign counts and the Router's actual origin instruction; never copy screenshot IPs, invent fresh checks or add disable/DNS semantics to group controls.
- Verify group mutations against isolated real backend/browser fixtures; public QA reads exact metadata and cancels/avoids writes. Preserve the complete private binary/domain/route/check state rollback pair and refuse overwriting concurrent edits.
