# Approved GAM workbook → live finance dashboard

## Scope and authority

Use only after the emailed GAM source has been reconciled and Rodolfo has approved all classification divergences. Consolidation remains owned by `revenue-spend-reporting-pipeline/references/gam-daily-excel-consolidation.md`; this reference begins at an approved final workbook and governs the live `dash.mgsdigitalcorp.com` import.

Validated production case: Rodolfo `1547692440574627921`, September 1–9 2026. Final workbook SHA256 `f7047d7ab39a1412a969bc3528bc9b5c6fd763306ad2145ee98a545c81c55477`; evidence `/root/mgs-agent/work/finance-revenue-1547692440574627921/`. This is a case fixture, not permission to replay it for another file or period.

## Recurring daily GAM e-mail import

Rodolfo `1547983130038767755` authorized the corporate mailbox pipeline. Load `/root/mgs-agent/docs/finance-gam-email-automation.md` for current state and exact artifacts. Each day is a new deterministic native-fact import: preserve original USD/CAD, require both reports and all classifications, rehearse against the current production revision with zero writes, create a validated `pg_dump` plus same-hash local copy, freeze a locked recovery scenario inside the write transaction, advance cutoff by exactly one day, and verify PostgreSQL/result readback. A revised source for an already imported day, date gap, missing source, unresolved country/vertical, unknown manager or duplicate identity blocks rather than overwrites.

**Classification closure and first live run — Rodolfo `1548001704119762945`:** TopFeed Finanzas source ES is an explicit destination override to US/`us-cc-es`; GameZoneAd source MX is an explicit destination override to BR/`br-game-br`; from source date 10/09/2026, a truly absent `utm_medium` (`-`/blank) on any site maps to `g002-s`. Preserve any valid `g00X-s/-d`; do not treat nonempty malformed values as absent or rewrite earlier imported history. The 10/09 pair completed as 3,058 rows → 74 native groups, production revision 122→123, audit 593, cutoff 10/09, locked recovery and idempotent second apply with revision unchanged.

## Financial mapping

1. Preserve the approved workbook's date, country, vertical, manager identity, currency and exact gross revenue. Never remap a new country to the site's usual country.
2. Map G001→`george` (public label Ícaro), G002→`SEM_COMISSAO`/MGS, G003→`isliago`, G004→`joe`, G005→`kelly`, G006→`nicolas`. The workbook retains `-s`/`-d`; the current dashboard stores manager identity, not that traffic-strategy suffix.
3. Existing legacy daily gross inputs are USD-base fields. Do not paste original CAD amounts into them even if stale model metadata says CAD: UI `inputCurrency()` and the domain projection treat a direct source gross cell as USD. Preserve emailed CAD through currency-aware native facts so `fx_convert` uses the period's USD/CAD rate and the UI shows the CAD origin.
4. Use existing USD per-manager inputs only when `(site,country,date,currency,manager)` resolves uniquely. Validated September case: 42 Fincgriffin USD inputs. Route missing site/country pairs and the shared Yolokfx manager split through deterministic native facts. Do not register unknown sites or change active-unit expense allocation merely to preserve small revenue; they appear as pending-site facts until separately classified in the catalog.
5. Native entries use the site's period network when registered; otherwise use the report's verified network and current period rates. Revenue imports must leave spend and company-expense allocation unchanged. Personnel is expected to recalculate because manager results feed commissions/payroll; treating unchanged personnel as a validation requirement is wrong.

## Transactional execution

- Preflight authenticated `/api/workspace?period=YYYY-MM`: owner identity, draft state, target fields blank, no existing import prefix, all source rows mapped once, 18 currency/day controls (or the exact period count) reconciled.
- Build a deterministic import prefix from period/date range/source hash. Aggregate only true key collisions; retain row lineage locally.
- Create a full `pg_dump` and exact scenario JSON before writes; validate archive listing and restore it into a fresh isolated database. A private `0700` directory owned by `mgsfinance` must be inspected/hashed as that user (`sudo -u mgsfinance`), not as `zeus`. A dump in a private Zeus directory must be fed to `mgs_pg` through shell stdin redirection; `mgs_pg` cannot open the private path directly.
- Rehearse the current production scenario through the same calculator with zero writes. Before the atomic update, lock the scenario row and create a locked recovery scenario containing the exact latest revision/overrides/additions/result, so concurrent spend/quote updates between the earlier dump and write remain recoverable.
- Apply one transaction with revision guard: target overrides + deterministic native additions + recalculated result + recovery audit + import audit. Never overwrite an existing nonempty gross value. Repeat execution must be a verified no-op with the same source hash and IDs; partial/mismatched state blocks.
- Preserve all unrelated additions, baseline/source rows, media spend, company expenses, site statuses, account bindings and closed history.

## Readback

- Verify stored overrides, native IDs/amounts, recovery scenario, audit action and source hash from PostgreSQL.
- Read authenticated live workspace and reconstruct origin totals exactly like UI: direct legacy gross inputs are USD; native facts use their declared currency. Ignore extra zero-only currency keys and reconcile every nonzero currency/day to the workbook.
- Test Relatório Diário on desktop/mobile, 31 rows for September (30 days + total), Gross CAD visibility, JS errors zero and search-based discoverability for representative active/inactive/pending sites. Do not assert that every site is present in raw `innerText`: collapsed inactive/pending groups may omit their text; filter/search and assert the target `data-site` element.
- Download/read back the final Excel attachment and match its hash. Before the first upload, finish canonical domain/site checks and send exactly one final file. Never send an interim file merely to prove local completion while a later canonical check can still change it. If a correction is discovered after upload, explain the reason immediately and identify the single superseding filename; do not leave two unexplained attachments. Deleting the superseded Discord message remains a separate destructive confirmation gate.

## September 1–9 verified result

- 513 approved Excel groups → 42 existing Fincgriffin USD inputs + 471 currency-aware native manager facts.
- Original totals: USD 59,828.65570781756822746681 and CAD 216,460.49855899488678972775; all 18 currency/day controls passed.
- Production workspace revision 79→80; audit 452; locked recovery `recovery-gam-1547692440574627921`; idempotent repeat no-op.
- Live origin readback, desktop/mobile and audit passed; spend/company expenses unchanged, personnel recalculated as designed. No Sheet, billing, payment, credential, account or campaign writes.
