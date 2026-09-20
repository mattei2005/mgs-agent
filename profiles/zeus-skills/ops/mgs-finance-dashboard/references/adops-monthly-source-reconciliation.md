# Monthly AdOps source reconciliation

## Authority and source precedence

Rodolfo `1551042463060197386`, thread `1545426987756298340`, supplied August/2026 workbook `1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g` for an all-account/all-network reconciliation. For this closing, **ActiveView consolidated is the payment-governing report**; detailed AV remains an attribution/reconciliation aid and must not replace the consolidated total merely because it is granular. SB Rede1 is CAD; SB Rede2 is USD; M2 consolidated and campaign detail are both required. This source priority is bounded to this supplied closing, not permission to change other periods, settlement rates or payment execution.

Use canonical Google SA only. Read every named tab completely and preserve original values/types/row numbers plus hashes. Re-read all source tabs before finalizing, not merely Drive modifiedTime. Compare with a consistent live production workspace and master account registry, recording their revisions.

## Required reconciliation gates

1. Detect cross-tab copied tails by exact row-position equality and currency-format transitions before summing networks. Equal grid row counts are not independent evidence of complete reports. Quarantine suspicious rows in analysis, retain literal data, and obtain source confirmation before an import.
2. Dates imported into a pt_BR Sheet from US exports may have days 1–12 converted to month/day-reversed serials while later dates remain strings. Inspect UNFORMATTED_VALUE and FORMATTED_VALUE. Record literal and proposed intended dates separately; do not silently reinterpret source cells or write malformed dates into another month.
3. Do not coerce ambiguous money text silently. A string such as `$1,419,47` is not a numeric cell. Keep the literal, flag the explicit numerical interpretation, recompute all rows, and compare with the stated footer. Never trust the footer alone or let SUM omission of text become the official total.
4. Reconcile Facebook by exact account identity, then day, then month. Account suffixes such as `-01`/`-02` and manager suffixes are not interchangeable. Same amounts/days support a mapping investigation but do not establish identity; request/resolve numeric account ID before remapping an unmatched name.
5. Trace legacy source_links across primary and complementary site blocks. A guest-manager account may have been incorrectly linked to the main account, with one-day offsets. Correct attribution separately from the net site-total difference and never append the guest amount on top of an already included complementary block.
6. A monthly zero delta can hide wrong daily placement. Retain all daily differences even for accounts whose monthly totals match. Source omission is not automatically zero for a registered account; enumerate positive dashboard-only amounts separately.
7. Use billing currency for spend (Google BRL, Facebook currency from the source). Prove that all reconciled legacy/native spend adds to the dashboard's existing consolidated spend, with its actual FX, before proposing replacement.
8. Keep revenue in native currencies. For a provisional USD bridge use the exact live dashboard USD/CAD rate, adding AV and M2 USD only after their basis is established. Dashboard site totals may blend pre-migration AV and post-migration SB; the site's current partner label does not prove all historical revenue belongs to that partner.
9. Preserve every source placement/site, including subcent residuals and absent August catalog sites. Do not let registering a residual site silently activate expense allocation. Country/manager attribution and site totals are separate acceptance checks.
10. M2 keeps the approved `b01*` Direct / everything-else BOT rule. Cross-check each campaign's dates/amounts against each consolidated domain: a detail report can label every row with the main domain while including a subdomain campaign. Matching the combined total does not prove domain attribution. Prior browser Profit Attribution data must not override a new reconciled AdOps export without an explicit source reason.
11. If a consolidated report will govern payment, clarify gross-versus-net basis before deducting invalids/revshare again. A receipt amount is not automatically gross revenue.
12. Report all source blockers and numeric deltas together when Rodolfo requests a numbered batch. Clearly separate confirmed discrepancies, conditional amount bridges and proposed corrections. Do not declare a corrected dashboard or close PEND-092 while financial writes/readback or source decisions remain outstanding.

## Current evidence pointer

The initial all-tab read-only reconciliation is recorded at `/root/mgs-agent/reports/finance-adops-reconciliation-1551042463060197386.md`, with original snapshots and daily/account/site artifacts in `/root/mgs-agent/work/finance-adops-reconciliation-1551042463060197386/`. The source issues found there are observations, not universal hardcoded import rules. Resume from checkpoint `ZEUS-FINANCE-ADOPS-1551042463060197386`.
