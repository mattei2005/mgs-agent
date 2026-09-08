# API-first spend → site daily report — Rodolfo correction2026-09-08

## Active authority and explicit supersession
Thread1545426987756298340. Rodolfo1547012165150711858 rejected the imported-spend panel in Contas de Anúncio. During the same execution he explicitly required API-first discovery, automatic Dash registration and correct site linkage for new spending accounts, then daily spend insertion. He confirmed notifications in this SAME Discord channel/thread and explicitly requested persistence before context fills. This supersedes the previous `registered_accounts_only`, `no automatic registration`, and user-facing imported ledger in Accounts assumptions from1546991137171181578. Do not resurrect those as active policy.

## Required product behavior
- Contas de Anúncio is ONLY account identity/cadastro and site binding. No spending dashboard, imported-record list or API audit panel there.
- Spending appears in the existing Relatório Diário for the correct SITE and DATE, like filling that site's monthly Sheet manually.
- API discovery is the starting universe, NOT account IDs already in Dash. Find spending accounts from official Meta/Google APIs for the period, then compare to Dash. A new spending account must not be missed because it was absent from yesterday's cadastro.
- For a newly discovered spending account, register its verified official ID/name/currency/timezone in Dash, bind to the correct existing site, and import each day's spend automatically. This is Dash registration, NOT creation of an ad account in Meta/Google.
- Auto-binding must be unambiguous using canonical site/domain and established naming rules/country. Never invent a site, choose an ambiguous financial block, split an amount arbitrarily, or overwrite an explicit conflicting binding. Preserve other successes and report only the blocked account for human decision.
- The scheduled run remains around7am Eastern (current scheduled slot07:16+25s), covering the month through yesterday, excluding today/future. Exact-ID/date dedupe, live currencies, verified zero versus failed lookup, fixed FX protection and manual edit provenance remain required.
- Notify in Discord thread1545426987756298340 about new registrations and actionable exceptions. Rodolfo confirmed this destination. Do not add a notification/spend panel to Accounts. Routine success does not need a large daily inventory dump.

## Exact reconciliation of user's screenshot
Image `/root/.hermes/profiles/zeus/cache/images/img_9f15b7c05e0b.png`:34positive rows, all USD, displayed total114831.22; no date range visible. Rodolfo typed R$ and later11.206,16, but the screenshot currency is USD and the previous agent figure was111206.16USD. Preserve source distinctions; don't silently convert currencies or infer dates from image alone.
Transcription saved to `apps/finance-system/private/spend-placement-1547012165150711858/facebook-reference.csv`,34unique names, Decimal sum114831.22. Existing collection covered80registered Meta accounts,28positive,111206.16USD. Six omitted nonregistered spending accounts total3623.67USD: Vizioid-US-SHEIN-EN-01-G002 and Yolokfx-US-SHEIN-EN-02-G006 /03-G005 /04-G004 /05-G001 /06-G003. Seventeen matched accounts differ by a combined1.39USD between old collection and screenshot. Exact bridge111206.16+3623.67+1.39=114831.22. Do not attribute the1.39 to API correction timing until verified by a fresh source read. A310/350-account accessibility inventory is not a count of spending accounts.

## Execution state at this checkpoint — not completion
- Local `public/app.js` no longer mounts `media-spend.js` in Accounts; daily date rendering corrected to use actual month rather than hardcoded/08. Focused static tests watched fail then pass. Publication/browser verification remains required.
- Collector changes to inspect spend of accessible unregistered accounts are in progress; full API-first auto-registration and site/day acceptance still require implementation and staged/live validation.
- Existing data/cron are from the previous implementation until the next explicit validated cutover. Do not call the new behavior active merely because this rule is saved.
- Before closure: exact site/day API-versus-browser reconciliation, source coverage/counts, new-account canary+idempotency, no mistaken site allocation, notification proof, canonical contract/registry supersession, inventory and REPORT-INFRA. Preserve backups; no destructive cleanup or credentials change authorized.
