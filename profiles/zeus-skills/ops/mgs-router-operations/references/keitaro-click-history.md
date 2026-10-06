# Keitaro historical aggregate clicks

Read `docs/mgs-router-keitaro-click-history.md`, source/validation receipts and checkpoint `mgs-router-keitaro-click-history-1556908028450836511` before resuming. Runtime and ledger supersede extraction-only checkpoints.

- Extract only authenticated aggregate day+campaign_id+clicks with explicit America/New_York timezone. Close the source interval before native Router collection; reconcile page counts, unique keys and summed clicks against the source summary programmatically.
- Match current route host+path to a unique source domain+alias; abort ambiguity or missing mapping. Exclude historical campaigns absent from the current catalog; do not recreate them implicitly.
- Preserve the native `since` and collected counts. Expose historical origin/date range independently in API/UI; do not claim native collection for imported dates or invent missing days.
- Use an online SQLite backup, never raw-copy a live WAL database. Prepare validated rows in connection-private TEMP memory before the live transaction; measure writer lock in a full-size copied database before publication.
- Bind the import to a stable ID, source hash and metadata ledger in the same transaction. Verify exact day+route totals and replay idempotency. Reconcile a possibly successful COMMIT before retrying any failed wrapper; never restore the whole DB over subsequent native counts.
- Daily overlap needs a source interval cut at native-start second and explicit reconciliation; the shipped single-use importer fails closed when source days overlap the native day. Do not weaken that check casually.
- QA both authorized accounts with all-history, first-day and monthly API/UI comparisons, sort and calendar; verify persistence after real Router restart. Use HEAD for public-route regression to avoid polluting live counters. Never restart gateways for this app.
- Keep credentials in approved protected flow; remove an ephemeral relay immediately after login. Never export visitor records or cookies.

Current receipt:2,575,829 imported clicks,27,433 daily records,444 campaigns with history out of445 exact current mappings,22 Jan–4 Oct2026. The source has no events for the remaining mapped campaign; zero is not a fabricated history. Scripts are single-use and authority/hash bound, not generic approval bypasses.
