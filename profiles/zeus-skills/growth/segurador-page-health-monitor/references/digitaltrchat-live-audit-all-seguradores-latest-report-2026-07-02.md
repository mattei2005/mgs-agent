# DigitalTRChat live audit methodology corrections — 2026-07-02

## User corrections

Rodolfo corrected two major audit mistakes:

1. Logging into a bot user only opens the first/default segurador/account. The audit must use the top selector and visit **every segurador/account** under each bot user before claiming coverage.
2. Current status is determined by the **latest completed/sent campaign report per page**, not historical completed campaigns. Old errors may reflect a restriction or app issue that has already been fixed.

## Required live-mode workflow

For each bot user:

1. Log into DigitalTRChat/ChatPion live dashboard.
2. Open the top segurador/account selector.
3. Iterate every segurador/account, not just the default.
4. Within each segurador, enumerate pages/campaign contexts.
5. For each page, inspect only the latest `Completed`/sent campaign with a usable report.
6. Open campaign report and read exact `Sent response`.
7. Report exceptions only; stay silent on OK pages.

## Smart Bidding filter before reporting

Before treating an error as actionable, cross-check Smart Bidding/Dash page status:

- `On-hold` and `Blocked` are not in broadcast scheduling and should be ignored for current error reporting.
- `Broadcast` and `Campaign` are operational and count in template `PAGES`.
- Template `PAGES = Broadcast + Campaign`, not just Broadcast.

Rodolfo specifically noted that many low-revenue pages were intentionally set `On-hold` after revenue review; a historical `Completed` error from yesterday should not be reported today if the page is now `On-hold`.

## Error handling rules

- `#2022` current and pure: eligible for Smart Bidding action `Status=Blocked` + `Restricted Until = error date + 1 day`.
- `#2022` mixed with another error: report/review separately before bulk action.
- `#10_WINDOW`: copy exact error text; inspect the last five completed messages for that page to see if all five repeat the same error.
- `#551_UNAVAILABLE`: copy exact error text; inspect the last five completed messages; this is often subscriber-level/unstable, not structural page failure.
- `#100_TEMPLATE`: copy exact error text and provide recent example pages + segurador for manual inspection.
- Permission/App deleted errors: compare with migration sheet / app-role X state before treating as unexpected.

## Reporting shape

For large audits, use compact executive totals plus exception samples:

```text
Usuários
Seguradores/accounts visitados
Páginas/contexts auditados
Ignoradas por On-hold/Blocked
Sem último Completed/report
Com erro no último report
#2022 puro / misturado
```

Do not report an audit as complete unless every user × every top-selector segurador/account was visited or the coverage gap is explicitly labeled.
