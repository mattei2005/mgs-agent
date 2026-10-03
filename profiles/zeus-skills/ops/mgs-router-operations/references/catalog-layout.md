# Router catalog and compact UI

Load `docs/mgs-router-catalog-layout.md` and its receipts before operating Rotas/Destinos/Grupos. This layout supersedes the former sidebar UI, not signed DNS verification or weights.

- Preserve the entire configuration (`revision`, `routes`, `catalog`, `groups`) on every API write. Old route-only payloads fail closed after catalog migration; do not remove metadata to force an old importer through.
- Keep imported Landing Page identities by source ID (`ktr-<id>`), not URL. Different names/IDs may share a URL; deduplication by URL changes the inventory even if redirects initially look equal.
- Require `destination_id` references to exist and match the concrete URL snapshot. Change a shared URL and all referenced route snapshots atomically, only after the panel identifies affected routes and obtains confirmation. Names/groups are metadata, not redirect rules.
- Derive initial local groups from confirmed source name prefixes when group metadata was not extracted. Label this derivation honestly; do not infer country or claim an exact Keitaro group copy.
- A catalog built from imported routes covers used pages only. Do not claim all Landing Pages shown in an external screenshot were imported.
- Scope UI assertions to the active table (`#routes .empty`, etc.); hidden tabs contain their own placeholder rows. Count real records, not placeholder `<tr>` nodes.
- Seed fresh test fixtures at their actual revision, not the revision copied from production. Test stale writes, reload persistence and shared edits/cancellation in Chromium; keep synthetic records out of production.
- Resolve 1Password through `/root/mgs-agent/scripts/mgs-op-with-service-account.sh` when terminal env lacks the Service Account. The authorized token lives in `/root/mgs-agent/.env`; do not use another identity or rotate credentials to repair an unloaded env.
- Preserve a private binary+state rollback pair before migration, verify checksums, and exercise the previous binary against the copied state. Any later rollback must reconcile edits made after the backup.
- Verify the public panel under both accounts, including catalog/search/group filter/pickers, all four views at mobile width, native login transport, logout and origin denial. A scrollable table may be wider internally; the document itself must not overflow.
