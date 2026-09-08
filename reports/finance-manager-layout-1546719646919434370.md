# Finance manager layout and total contrast — published verified

Authority: Rodolfo1546719646919434370 and1546720000134483970; thread1545426987756298340. Login1546717157868703805 completed separately (REPORT1546718484283654158); sidebar logo remained proposal, unchanged.

## Result
Three frontend assets published: operations.js, operations.css, navigation.css. Nicolas cards/summary refreshed; every original daily column available by country/total group;31August and30September days, no vertical table cap. Values machine-decimal strings now formatted pt-BR2places without rewriting state. Read-only Nicolas pilot unchanged. Summary monthly total comes from existing engine; daily sums computed before display rounding; ROI totals unavailable rather than invented sum/average.
Subtotal child spans inherit parent foreground/transparent background, removing dark-blue-on-dark-blue and light boxes. Live company August/September and Eggbev/site totals verified. No schema/backend/auth/credential/financial mutation or restart.

## Reproduced defects and tests
Before live:428px viewport vs1132px scrollHeight,3189long-decimal strings in August manager payload, company subtotal contrast false in both months.
TDD RED3failed for missing helpers/full-month/contrast; then focused11pass and fullNode48pass,0fail. Initial test harness lacked URLSearchParams/location, corrected before valid RED. First browser canary rejected valid pt-BR thousands due broad regex; corrected anchor. Second selected current period redundantly and rerendered mid-test, causing hidden selector; removed redundant select. No production changes in either failed canary.
Canary and live:42month/block/group combinations,8blocks,390/1440px,31/30days,0JSerrors; independent screenshot QA passed. Browser records each combination in JSON; no auth sessions exported. Before/canary/live API snapshot hash identical, recorded in evidence (actual tool-generated hashes, not inferred).

## Arithmetic audit
Independent Python Decimal from live API facts and cash matched company gross/invalid/net/tax/spend/general/staff/profit within1e-6USD in both months. September personnel−6305.495751869284541554571885 /30 gives−210.1831917289761513851523962 daily. Display−6.305,50 and−210,18 is correct rounding, not evidence for forced day-end adjustment. Audit does not re-certify every business rule or Sheets parity.

## Backup/readback
One-shot deploy/manager-layout-release.py: fresh code archive+PGdump, remote/local copies with matching hashes, restored isolated DB and compared all scenario IDs/revisions/overrides/additions/results. Three compatible static assets staged;CSSfirst/JSlast atomic replacement; remote hashes, unchanged financial fingerprint and services active verified.
Backup:/home/zeus/mgs-finance-backups/1546719646919434370
Stage:/var/tmp/mgs-finance-manager-1546719646919434370
IsolatedDB:mgs_finance_manager_1546719646919434370
Evidence:apps/finance-system/private/manager-layout-1546719646919434370/{before,stage,live}-browser.json; *-snapshots.json; *-totals-2026-*.json; decimal-total-audit.json; prepared.json;published.json;deploy-readback.json;node-tests.log;screenshots.
Backup/stage retained and inventoried; no destructive cleanup. No daily spend importer or extra manager access enabled.

## Knowledge
Canonical direction updated; skill mgs-finance-dashboard0.1.28 with references/manager-layout-and-total-contrast.md and supersession of prior table cap. Inventory/audit/REPORTreadback in final-readback.json.
