# August AdOps reconciliation — partial application and security block

## Authority and scope

Rodolfo1551275920671776839, thread1545426987756298340; update1551279009415958700.

Confirmed decisions:
1. Rodolfo removed the duplicated SB2 tail; fresh readback is 794 data rows, USD87,151.00 (rounded to cents), no SB1 tail.
2. Gross revenue is the comparison basis, before revshare/clawback. AV consolidated governs the monthly gross, not net payout. Four malformed numeric strings were authorized for correction.
3. The affirmative response to the previous pg-19326 question retains Wantabrand Finance attribution. Main Wantabrand target is USD4,604.04; Finance target USD7.83.
4. Updated closing Sheet governs FB and Google amounts/dates despite earlier API snapshots; platforms can revise spend after the month closes. Rodolfo prefers checking approximately20days later. No new scheduled job was requested.
5. Infinitynexx belongs to Joe; Ícaro/G001 is a guest. Source MX G001 CAD923.5661480497590605 rounds923.57; a separate US G001 row group totalsCAD1.322205407245324684. Both were preserved as source-tagged Ícaro, not reassigned to Joe.
6. CPV05/16 spend, EggbevFinanzas16/08, NewsounFinanzas18–20/08 and all other approved FB differences follow the source day/account.
7. LyzmoFinanzas display-name suffix02 is correct; numeric ID1818460511984988 remains unchanged. Historical verified Meta name was not fabricated or rewritten.
8. Both Google reports are August01–31; the source's first12 locale-inverted date serials were interpreted under this explicit confirmation. No source Google cells were changed.
9. AV Eggbev monthly gross USD59,978.57 governs. Openzed monthly AV was split by Rodolfo into G00312,637.77 + G0015.00.
10. Cliquet and Cliquet Finanzas consolidated amounts279.12/182.35 were added; their detailed reports remain pending. TopFeed Finanzas consolidated6,937.50 remains authoritative.
11. Fincgriffin is SB Rede2/USD for August; the earlier discrepancy was the dashboard catalog, not an assertion that the source had Fincgriffin on Rede1.
12. Boostingecon, Cephyric, DicasFinancas, Escalatepower and Mavroa enter August assignedG002/MGS without participation in general-expense allocation.

## Applied and independently read back

Production workspace2026-08 revision391→392; master-ad-accounts6→7. PostgreSQL audit IDs1513/1514. Locked recovery scenarios `recovery-adops-1551275920671776839` and its `-accounts` counterpart.

- All48FB accounts and2Google accounts:1550account/day checks;199spend input corrections. FB USD286,368.15; Google BRL71,174.24. Consolidated spend USD300,349.7080935767661016147653 at unchanged period FX.
- Source-complete revenue for16existing SB-only sites plus5new residual sites:814source groups +20residual rows,811gross-input corrections and native facts when source country/manager/currency cannot be represented by an existing leaf.
- Five residuals totalCAD1.3642065391097813660, assignedG002; allocation units and company expenses unchanged.
- Fincgriffin network corrected to Rede2; source-complete Fincgriffin gross checked against sourceUSD.
- Other periods, immutable baseline/source, settlement FX/rate parameters, campaign/budget/payment execution remain unchanged. Dependent calculated net/payroll totals recalculate normally; they are not the comparison basis or a new payout decision.
- Source Sheet `rede AV - detalhado` G701/G914/G1893/G2150 corrected to numeric1419.47/1309.12/1144.90/1145.41. FORMULA/UNFORMATTED/FORMATTED readback passed; all other G cells preserved.
- Calculation has0errors; real services active; public loginHTTP200 and unauthenticated APIHTTP401.
- Browser reached login, but its vault has no dashboard item and 1Password interactive unlock is unavailable in the Discord/headless session. No password bypass or authenticated browser acceptance was performed; validation is the independent production SQL/result readback, not a claimed UI visual test.

## Latest TopFeed source addition

Read all8tabs again after1551279009415958700. AV detailed now has16,096data rows including1,677TopFeed Finanzas rows. Those new rows sumUSD6,937.68 versus consolidatedUSD6,937.50: detail exceeds byUSD0.18.

The appended report has a separate locale-date issue: days1–12 are numeric serials interpreted as January08…December08, later dates are literalUS strings through08/19/2026. Monthly sum is unaffected; daily placement is not silently normalized.

After numeric-text repair, Eggbev detailedUSD59,978.59 differs from consolidatedUSD59,978.57 byUSD0.02, notUSD5,018.88. The earlier helper difference omitted numeric text. Full AV consolidated sumUSD106,920.78; complete current detail sumUSD106,459.59. Cliquet detail remains absent for the two domains; monthly consolidated values remain the approved targets.

## Financial work still open

AV/mixed-network and M2 gross adjustments have NOT been applied. Exported AV detail lacks a country column, monthly consolidated deltas lack a source day, and M2 lacks confirmed country attribution. Do not fabricate a day/country or silently spread monthly adjustments. Need Rodolfo's decision on a separately identified monthly closing adjustment versus explicit allocation. This is a blocked partition of the original scope, not cancellation or completion. PEND-092 remains open. Current partial dashboard grossUSD411,172.1132835894960372163176 is NOT the final reconciled gross.

## Security incident — self-caused, containment incomplete

Zeus incorrectly wrote the full pre-change PostgreSQL dump into `work/finance-adops-1551275920671776839/before.dump` before checking Git exclusion. The automatic watcher committed it in `a73a267d0` and auto-pushed to GitHub at2026-09-20T13:12:09-04:00. GitHub REST confirmed `mattei2005/mgs-agent` is PUBLIC. Remote main at containment:025531c4e36e35e4cc663c2ed483ceffd33be284. There is no evidence ruling out third-party download.

The restored exact dump contains financial data,6finance_users rows with password hashes/salts,7encrypted MFA records,308session records with token hashes and CSRF values, and9trusted-device records with token hashes. No plaintext password or raw session token is implied by these hashes. The MFA encryption key and owner password configuration are application files outside this database dump; this does not authorize assuming all Git history is free of other exposure.

Safe containment performed:
- moved the local dump to ignored/private `/root/mgs-agent/apps/finance-system/private/adops-1551275920671776839/before.dump`, mode0600/private parent0700, same SHA256;
- stopped `mgs-autocommit.service`; readback inactive/dead;
- preserved the remote/private backup and isolated restore database; financial service remains online;
- stopped further financial writes and did not rotate credentials, delete files/history, change repository permissions or force-push without Critical Subset confirmation.

Required confirmation: narrow removal of the dump from current Git and affected local/remote history with explicit force-with-lease; revoke dashboard sessions/trusted devices and rotate the6database-user passwords. Consider GitHub sensitive-data removal because a rewritten branch cannot prove cache/exact-SHA erasure. Do not reactivate auto-commit until containment and preventive exclusion are verified. This incident, not the financial calculation, is the immediate blocker.

## Backup and evidence

DumpSHA256 `fc6e7864f7f6871e0893f40da1143c697c40dd12614c88c57f02cfd56697b3c2`.
Remote private backup `/home/mgsfinance/backups/adops-1551275920671776839/before.dump`.
Isolated restored DB `mgs_finance_adops_1551275920671776839`:147scenarios,85,868source cells,August revision391. Preserved pending controlled cleanup.
Evidence directory `/root/mgs-agent/work/finance-adops-1551275920671776839/`, excluding the relocated dump. `final-summary.json`, `verify-out.json`, `backup-readback.json`, source snapshots and source-number readbacks are the bounded evidence.

Operational failures: absent barepython corrected to python3; continuity reference resolved to its owning skill; root-owned backup parent rejected app-user mkdir, corrected by creating only the new private child with explicit owner. A failed preparation initially allowed a subsequent rehearsal invocation, which failed without writes; chaining was corrected to fail closed. The more serious Git exposure above remains unresolved and must not be hidden under successful finance checks.
