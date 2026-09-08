# Explicit account-source identity reconciliation

Authority: Rodolfo1546752274989191230. Actual dashboard master-ad-accounts is the operational source; do not rerun successful one-shot migrations.

Resolved mappings (exact literals):
- `Creditoparaveiculo · BR-CAR-BR-015-G001` → `Creditoparaveiculo-BR-CAR-BR-15-G001`, ID `1063939172741186`, USD, America/Sao_Paulo. Source slot `principal|Agosto 2026|AJO|46`.
- `Yolokfx · US-SHEIN-EN-01` → `Yolokfx-US-SHEIN-EN-01-G002`, ID `7840111366055613`, USD, America/New_York. Source slot `principal|Agosto 2026|AGK|46`.

Both exact names/IDs confirmed live via the authenticated Meta lookup worker in Digital Trust155263197283282. Neither was already registered. Added two verified accounts and associated31 original daily source keys each in ONE optimistic-revision catalog write. Masterrevision3→4, accounts80→82. Original sheet labels, source keys, currencies, sites, countries and financial amounts preserved. In particular source CPV `countries:[US]` was not reclassified from the BR account name. The explicit owner mapping is not a general 015→15 normalization rule and not permission to omit/add G002 on other identities.

Procedure:
1. Check exact numeric IDs; authenticated on-demand lookup, live name/currency/timezone/BM validation, preserve literal user names.
2. Read catalog/slots/workspace; fail on existing ID, conflicting key owner, currency mismatch or existing native account_spend that could duplicate source spending.
3. Fresh dual PG/code backup with SHA256 verification and isolated restore.
4. Stage canonical `writeAccountDocument`, preserving all unrelated accounts/slots/candidates. Set only the two exact slots matched with owner-confirmation provenance; retain source_labels; attach original source_links instead of new monetary leaves.
5. Apply with same masterrevision guard and lookup freshness; read exact target back. Fingerprint all non-master financial scenarios before/after.
6. Real authenticated public API/browser: each ID/name searchable once on390/1440; original input values and entire financial domain unchanged; zero visible pending slots with nonzero amounts in August. This does NOT say every historical zero-money unresolved slot was reconciled.
7. Audit/registry/inventory/report and retained recovery paths. No Meta/Sheet/credential/service changes.

Tools: deploy/account-links-operation.py, deploy/reconcile-account-links.mjs, tests/account-links-preflight.mjs, tests/account-links-browser.mjs. One-shot AUTH1546752274989191230 already completed. Evidence private/account-links-1546752274989191230. Browser uses installed Chromium1234 with explicit executablePath; do not install missing default headless1243 or disturb protected1228. Resolve table DOM from current app (`[data-account-table]`), not historical `[data-account-catalog]`.
