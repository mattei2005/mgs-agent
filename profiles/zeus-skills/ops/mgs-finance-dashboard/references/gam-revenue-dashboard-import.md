# Approved GAM workbook → live finance dashboard

## Scope and authority

Use only after the emailed GAM source has been reconciled and Rodolfo has approved all classification divergences. Consolidation remains owned by `revenue-spend-reporting-pipeline/references/gam-daily-excel-consolidation.md`; this reference begins at an approved final workbook and governs the live `dash.mgsdigitalcorp.com` import.

Validated production case: Rodolfo `1547692440574627921`, September 1–9 2026. Final workbook SHA256 `f7047d7ab39a1412a969bc3528bc9b5c6fd763306ad2145ee98a545c81c55477`; evidence `/root/mgs-agent/work/finance-revenue-1547692440574627921/`. This is a case fixture, not permission to replay it for another file or period.

## Recurring daily GAM e-mail import

Rodolfo `1547983130038767755` authorized the corporate mailbox pipeline; Rodolfo `1549047147465281658` superseded whole-day mapping blockage with confirmed/pending partitioning. Load `/root/mgs-agent/docs/finance-gam-email-automation.md` for current state and exact artifacts. Each day is a deterministic native-fact import after spend covers the same date: require both reports, partition every source row exactly into mapped or pending, require `mapped + pending = source` per currency, rehearse against the current production revision with zero writes, create a validated `pg_dump` plus same-hash local copy, and freeze a locked recovery scenario inside the write transaction. Apply mapped rows immediately and expose their later date in Relatório Diário with an explicit `parcial` banner/row. Pending rows are omitted but never treated as zero; the Realizado cutoff and its totals remain on the prior day. After Rodolfo confirms the exception, complete only the missing partition under the same source identity and advance the cutoff by exactly one day. A revised source, date gap, conflicting existing partial fact, incomplete spend or unresolved partition mismatch blocks rather than overwrites. Routine success is silent; the thread receives only the exact classification question or a persistent technical blocker after retry.

**Classification closure and first live run — Rodolfo `1548001704119762945`; Mavroa supersession `1549069898674606352`:** TopFeed Finanzas source ES is an explicit destination override to US/`us-cc-es`; GameZoneAd source MX is an explicit destination override to BR/`br-game-br`; `pl_digital-trust_mavroa_us` is permanently `mavroa.com`/US/`us-shein-es`, with absent manager falling back to `g002-s` while canonical manager media still wins. From source date 10/09/2026, a truly absent `utm_medium` (`-`/blank) on any site maps to `g002-s`. Preserve any valid `g00X-s/-d`; do not treat nonempty malformed values as absent or rewrite earlier imported history. The 10/09 pair completed as 3,058 rows → 74 native groups, production revision 122→123, audit 593, cutoff 10/09, locked recovery and idempotent second apply. Full audit `1548008533608636527` restored the pre-import dump into isolated database `mgs_finance_full_audit_1548008533608636527`, added the spend-ledger gate and delayed finalizer, and proved that an 08:00 revenue arrival cannot expose an incomplete realized day.

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

## Principal Sheet versus dashboard monthly-total audit

For Rodolfo's total-based cross-check (request `1551598834092740688`, execution `1551599521887289517`), compare the exact linked tab's competence by domain and original Gross CAD, original Gross USD, Facebook USD and Google BRL. Do not require daily equality: the Sheet may place same-day CAD/USD on different rows because one USD cell also serves as CAD conversion. Resolve `gid` through live metadata, never infer the current month from conversation date. This is a read-only reconciliation, not authorization to repair either system.

- Read all three Sheet render modes. Discover and validate live header/block boundaries, including complementary Openzed and Infinitynexx blocks, but avoid counting Fincgriffin/CPV lower manager detail again when the top aggregate already includes it.
- Exclude USD cells whose formulas convert CAD via `$H$1` from **original USD** totals; retain direct USD and verified SUM aggregates. CAD-converted totals are not additional USD revenue. Compare original-currency amounts, not exchange-dependent global cash.
- Reproduce live UI `originGross` precedence: `gross_origins`, then model `gross_pair`, then true original inputs. Include monthly closing adjustments, even though their date is YYYY-MM rather than a day.
- Deduplicate spend source keys per domain. Google legacy inputs can carry stale `currency=USD` metadata while their exact source/label `Google Ads -R$` and source values are BRL; validate against raw source/override and normalized fact conversion before comparing, never report a false zero or currency gap from that metadata alone.
- Distinguish domains absent from the Sheet from literal zero entries. Report cent-visible differences separately from subcent residuals and retain full Decimal evidence. Reconcile source headers against live data: WavesBee's live CAD header supersedes the legacy frozen GBP header.
- A quote refresh may advance dashboard revision during the audit. Verify audit attribution, exact rate-only override delta, unchanged additions and unchanged original currency amounts; do not classify this expected FX movement as a financial-input change.

### Authorized pooled residual entry — August principal Sheet

Rodolfo `1551620693446234142` authorized pooling only the seven named August residuals (AutoCreditAdx, Portal Relevante, Cephyric, Escalatepower, Mavroa, DicasFinancas, Boostingecon) in principal `Agosto 2026` column AKU instead of creating blocks. Live AKU is **USD**, while these source amounts are **CAD**. The verified entry is AKU35, original CAD sum `1.4039951303068125534` divided by live `$H$1`, with the seven-domain breakdown in the cell note. This is a bounded Sheet accommodation, not a reassignment of every domain to AutoCreditAdx, not a dated revenue fact, and not authorization to change Dashboard entries. Reconciliation must remove the converted cell from original USD totals and allocate its documented original CAD components exactly once. Do not enter the rounded per-site display amounts and do not replay this entry as new revenue.

For this same review, AV consolidated workbook `1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g`, gid `1839542079`, column C remains the payment-governing August gross source. Zuout Finanzas is C20 = USD564.70, not the detail column D. This corroborates the existing consolidated-source rule; it does not authorize editing the report or applying net deductions twice. Evidence: `reports/finance-sheet-recheck-1551620693446234142.md`.

- Google Sheets normalizes long decimal literals in formula strings to its numeric precision. After a write/readback string mismatch, inspect the actual formula and validate its exact operator/reference structure plus a tight numeric tolerance before retrying; preserve full source precision in the note/manifest. Never replay a completed write merely because the literal was normalized.
- The workspace API deliberately omits `kind=rate` rows from `additions`; use that exact documented projection for API/database parity, while checking every financial fact and cash total strictly. Do not interpret a different raw list length as a concurrent financial mutation. Join large diffs by stable IDs and summarize counts, rather than printing index-shifted lists.

## Alias/catalog and execution safeguards

- When a GAM placement is unknown, query the real catalog case-insensitively before creating a site. Resolve the placement alias to the existing exact label/ID and update only authorized missing metadata; unknown importer alias and absent dashboard registration are different states.
- A confirmed inactive site stays outside general-expense allocation. Residual revenue does not authorize activation, campaign changes, invented spend, or a claim that its traffic was organic.
- Execute expensive rehearsal, backup, apply and verification as separately bounded tool calls. A client timeout can leave the remote transaction running; check its process, revision, recovery and audit before any retry. Never replay an ambiguous write solely because the local receipt is missing.
- When adding a mapping authority, update the parser's selected authority, the remote runner allowlist and focused test expectations together; preserve all older authority entries and financial assertions. Deploy/read back the UI rules copy as well as the runner, not only the local rules file.

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
