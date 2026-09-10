# Finance dashboard — GAM revenue import, 01–09 September 2026

Authorization: Rodolfo `1547692440574627921`, thread `1545426987756298340`.
Status: `PASS`, production data written and read back.

## Source

- Approved corrected Excel: `work/finance-revenue-1547692440574627921/Receita-01-09set-2026-Zeus-Final-Corrigido.xlsx`.
- Final SHA256: `98efcd052b0ff3e5552dc67c62e5e5f30b12a083e1be9694f00ad99a403770e5`.
- 513 consolidated groups; original controls USD 59,828.65570781756822746681 and CAD 216,460.49855899488678972775.
- Canonical domain correction after first delivery: `helixenit.com` → `helixenit.net` in 27 rows, based on `context/sites.md`. No numeric, date, country, vertical, manager or currency value changed. Dashboard had already routed the brand to its existing canonical Helixenit entity. Audit bridge: event 458.
- Latest native Discord attachment: message `1547701048372756541`; downloaded bytes matched the final hash. Earlier attachment `1547700319469838336` is superseded, not deleted.

## Production operation

- Target: `dash.mgsdigitalcorp.com`, scenario `workspace-2026-09`.
- Revision 79 → 80, draft preserved.
- 42 Fincgriffin USD manager inputs updated through existing unique source fields.
- 471 deterministic currency-aware manager facts added. Original CAD was not pasted into legacy USD-base fields; it remains CAD at origin and converts through the September USD/CAD rate.
- Manager identity mapping: G001→Ícaro/internal george, G002→MGS/SEM_COMISSAO, G003→Isliago, G004→Joe, G005→Kelly, G006→Nicolas. The Excel retains `-s`/`-d`; the dashboard currently retains manager identity, not the traffic-strategy suffix.
- Yolokfx manager distribution matches the approved workbook. Countries in the emailed GAM were preserved even where the prior dashboard catalog showed another country.
- Cephyric, Escalatepower and Mavroa revenue is present as pending-site facts; they were not registered or activated because that would change monthly site status and company-expense allocation beyond this request.
- Spend, account bindings, site status and company expenses were preserved. Personnel recalculated as designed because manager results feed commission/payroll.
- PostgreSQL audit event 452 records the import. A second execution was a verified no-op.

## Backup and rollback

- Full pre-write dump: `/home/zeus/mgs-finance-backups/1547692440574627921/mgs_finance-before.dump`, SHA256 `b03361e504c80fa5aaf2b7c711dd7b196eb00944195dd1a989754ded94291a7d`; archive listing passed.
- Exact pre-write scenario JSON is beside the dump.
- Dump restored to isolated database `mgs_finance_gam_1547692440574627921`; 85,868 source cells and scenario revision 78 matched the snapshot.
- Exact latest transactional recovery scenario: `recovery-gam-1547692440574627921`, locked at revision 79, 165 prior additions and zero revenue for days 1–9. It preserves concurrent spend/quote changes that occurred after the earlier dump.
- No cleanup or deletion performed.

## Validation

- All 18 currency/day origin controls match the corrected Excel; maximum dashboard-versus-corrected-Excel difference `9.23962529E-12`.
- Dashboard USD gross after provisional CAD conversion: 216,333.0885623900206640037848 at USD/CAD 1.383095.
- PostgreSQL readback: 471 import entries, 42 target overrides, source hash/audit and recovery snapshot present.
- Authenticated public readback: September revision 80, 31 daily rows (30 + total), Gross CAD visible, representative active/inactive/pending sites discoverable by search, desktop/mobile PASS, zero JavaScript errors.
- Services: PostgreSQL, finance dashboard service and socket all active.
- No Google Sheet, billing, payment, credential, account, campaign or Hermes gateway write/restart.

## Recovered implementation failures

- First auth inspection saved the read-only workspace but failed to find an obsolete logout button; switched to the canonical CSRF logout API.
- Initial plan tried to bind BR revenue to dashboard countries that were historically US; changed to native country-preserving facts instead of remapping the CSV.
- Three staging attempts exposed private-directory ownership boundaries. Corrected to inspect/hash `0700` mgsfinance staging as `mgsfinance`, and to feed the private Zeus dump to `mgs_pg` through stdin. No production financial write occurred during these failures.
- Isolated DB connection under app role was blocked by the existing exact-database pg_hba policy; did not modify pg_hba. The dump restore was verified separately, and the calculator was rehearsed read-only against the current production scenario before the atomic write.
- Rehearsal initially asserted personnel must stay unchanged; corrected because revenue is required to propagate into commission/payroll. Spend and company expenses remained the unchanged controls.
- Three live UI readback assertions used zero currency keys/raw collapsed text. Corrected to compare only nonzero origins and discover sites through the search UI. These were read-only failures after the successful write.
- Artifact-correction audit insertion succeeded, but the client misparsed PostgreSQL `RETURNING` output; event 458 was reconciled by exact readback and not duplicated.
