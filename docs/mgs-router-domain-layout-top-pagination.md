# MGS Router — Domain table, scoped domain groups and synchronized pagination

## Authority and active source

Rodolfo in Discord thread `1555381168894115912`:
- `1556486236846428211`: keep lower Campanhas/Landing Pages pagination and add the same controls above.
- `1556486947147350067`: domain workspace follows Keitaro table layout; independent domain groups; create `MGS` and associate all current domains.
- `1556493561938317322`: remove the imported Landing Page ID column when not operationally useful on screen.

This extends and supersedes the **UI details** of `docs/mgs-router-bulk-actions-pagination.md`. The original bulk/state/query/privacy/traffic/DNS contracts remain unchanged. `data/mgs-router-domain-layout-validation.json` is the exact deployment receipt; `data/mgs-router-public-validation.json` is the later read-only public validation.

## Published behavior

- Campanhas and Landing Pages: synchronized upper/lower Anterior, Página X de Y, Próxima; still 30 items/page, independent scope state, search/filter/sort reset and visible-only selection.
- Landing Pages: selection checkbox remains; `ktr-*` ID text/column label removed from the operator display. Identity is essential internally for `destination_id`, shared usage, weights, editor choices and bulk selection; never remove or regenerate IDs in the data. Browser QA uses checkbox `data-key`, not visible cell text.
- Domínios: compact table with selection, stable local ID, domain link, group, dated saved DNS/HTTPS status, HTTPS-Only indication, root campaign name if present, campaign count/navigation, and DNS-instructions/Verificar actions. Domain search, group filter, ID sorting, 30-item upper/lower pagination and scoped group dialog; responsive internal-table scrolling.
- IP badge uses the existing MGS origin instruction returned by the API; screenshot Keitaro IPs are not imported or applied. No extra provider settings, tracking or automatic DNS/certificate operations added.
- Registered all 19 already operational hosts in domain metadata and associated each with `MGS`. The old registry had only two explicitly registered hosts plus 17 hosts inferred from campaigns; this migration persists the existing union, not new external domains.
- Domain group create/rename/remove and assigning selected visible domains work through the real domain API. Removing a group only clears memberships. Domain removal remains prohibited; no domain enable/disable semantics were introduced.

## Domain persistence and safety

`/var/lib/mgs-router/domains.json` retains the `domains` string list for compatibility, with `group_schema:1`, `domain_groups`, and host-keyed `metadata:{id,group}`. It has its own revision independent of route configuration. Server allocates positive IDs, preserves existing IDs, rejects duplicates, unknown groups, stale revisions, legacy downgrade, omitted existing metadata and domain removal; atomic locked writes. Startup accepts legacy data without side effects and rejects corrupt schema1 data.

Route configuration stays `group_schema:2`, `action_schema:1`, with 445 campaigns, 943 Landing Pages, 29 groups in each area. Route JSON, user state, domain-check store, service config and credentials preserved; no DNS, SSL, WordPress, permissions or gateway changes. Only Router app restart for embedded assets/code. Private pre-change binary/state and candidate state at `/root/.local/share/mgs-router-rollbacks/1556486947147350067`; exact-pair rollback refuses concurrent state edits. Old executors are single-use and never replayed.

## Validation and operational repair

- 78 Go/browser cases passed, race, vet, JavaScript syntax and build passed.
- 1,856 real public route checks passed.
- Both `rodolfo` and `geizian` accounts: real Chromium upper/lower synchronization, all 445 campaigns and 943 LPs enumerated, exact MGS domain memberships/counts, group modal/filter/search/selection, mobile width, and LP ID display removal; zero production UI action writes.
- Real isolated Chromium/backend fixture covers create/rename/remove domain group, assignment, adding grouped domain, ID stability/reload, 30-page boundaries and cleared page selection. Go regression covers stale revision/schema downgrade/bad refs/ID mutation, persistence, corrupt startup and preserved redirects.
- Postdeploy independent public checker initially lacked a loaded 1Password environment (`command_failed:op`). Corrected it to the canonical `mgs-op-with-service-account.sh` wrapper; credentials were not rotated. Repeat returned `public_validation_passed` for both accounts.
- Made that public checker genuinely read-only: consume saved `/api/domains` observations instead of POSTing `/api/domains/check`, which updates verification timestamps. Receipt explicitly labels `saved_observations_no_online_probe`. The operator's Verificar button still performs a fresh online DNS/HTTPS probe and saves its timestamp. Saved green is not continuous monitoring.

No secrets in receipts, inventory, logs or docs. Preserve private rollback material; cleanup/deletion needs its own critical confirmation.
