# DTR ↔ SB Step 1 PAGE ID audit — Sheet tabs, LOGIN source, and 07 cleanup

Session: 2026-07-06  
Scope: Bot/DigitalTRChat page registry vs SmartBidding `Accounts > Messenger > Page` registry.

## Core matching rule

For PAGE ID registration audits, never pre-filter SmartBidding rows by bot user/login before matching. Use the full SB Messenger Page scope first:

1. Full SB scope: all child publishers under `digital-trust` + `digital-trust-2`.
2. Match DTR page to SB row by global `FB_PAGE_ID` first.
3. Fallback to global `PAGE_ID` only if no global `FB_PAGE_ID` match exists.
4. Treat `LOGIN` / `USER_LOGIN`, `PAGE_ID`, `FB_PAGE_ID`, and `UTM_CAMPAIGN=pg_<PAGE_ID>` as validation fields after a row is matched.
5. Do not use page name as a match key for this audit class.

## SmartBidding login field gotcha

In `/campaigns/Messenger`, many rows have:

- `LOGIN` filled with the bot email;
- `USER_LOGIN` blank.

For human-facing sheets, label the field as `SB LOGIN/USER_LOGIN`, not just `SB USER_LOGIN`. If the code normalizes `USER_LOGIN or LOGIN`, say that explicitly in reports.

Example observed:

```text
SB ID: 68ead2f3-ac28-a655-5920-eeaacf2a0d24
LOGIN: disparoscliquet@gmail.com
USER_LOGIN: empty
PAGE_NAME: Daniella Rosário
PAGE_ID: 8341
FB_PAGE_ID: 823864334141386
STATUS: On-hold
COMPANY: digital-trust-2
```

## Sheet tab pattern for Step 1

When Rodolfo asks to recreate the Google Sheet after deleting tabs, create/recreate class-level tabs, not a one-off flat dump:

```text
00 Resumo
01 OK LOGIN PAGE FB UTM
02 Login difere
03 PAGE_ID FB difere
04 UTM difere
05 Nao encontrado SB
06 Ambiguo SB
07 SB sem Bot DTR
08 Duplicidades
```

Always write via Google Sheets API when available, freeze headers, add filters, and validate readback row counts for every tab before reporting success.

Recommended detail headers include:

```text
Classificação | Match por | Diferenças | DTR Bot user | DTR Segurador | DTR Página | DTR PAGE_ID/PG | DTR FB_PAGE_ID | DTR Facebook URL | DTR Email página | DTR raw | UTM esperado | SB LOGIN/USER_LOGIN | SB Segurador | SB Página | SB PAGE_ID/PG | SB FB_PAGE_ID | SB UTM_CAMPAIGN | SB Status | SB Restricted Until | SB Company | SB Domain | SB ID | Candidate count
```

## Tab 07 semantics and cleanup

`07 SB sem Bot DTR` means:

> A row exists in SmartBidding with that SB `LOGIN`/page IDs, but no same page was found in Bot/DTR by `FB_PAGE_ID` or `PAGE_ID`.

It does **not** mean the login came from DTR; the email source is SB `LOGIN`/`USER_LOGIN`.

Rodolfo correction: in tab 07, rows where `SB Status = Blocked` can be ignored for this comparison. Reason: blocked pages may have been unlinked by the gestor, deleted by Facebook, or permanently unavailable. Remove/filter `Blocked` rows from the active 07 review before asking Rodolfo to inspect the remainder.

In the 2026-07-06 run, 07 had 475 rows; after excluding `Blocked`, 89 remained for review.

## Public Facebook URL check for 07

For the remaining non-Blocked rows in tab 07, column I contains `https://facebook.com/{FB_PAGE_ID}`. Rodolfo may ask to open all and check for Facebook's unavailable warning:

```text
This content isn't available right now
When this happens, it's usually because the owner only shared it with a small group of people, changed who can see it or it's been deleted.
```

Use a real browser/Playwright pass over the column-I URLs, not just HTTP status. Classify rows as:

- `UNAVAILABLE_WARNING_EXACT` — exact warning text appears.
- `UNAVAILABLE_WARNING_OTHER` — similar unavailable/page unavailable warning appears.
- `NO_UNAVAILABLE_WARNING_SEEN` — page opens without that warning.
- `ERROR` — navigation/timeout/tool error.

In the 2026-07-06 post-Blocked pass, all 89 remaining column-I links returned `NO_UNAVAILABLE_WARNING_SEEN`.

## Reporting shape

For Rodolfo, keep the Step 1 closeout short:

```text
Escopo: users/logins/seguradores/páginas/publishers/SB rows
Resultado DTR → SB: OK, login diff, not found, ID diff, UTM diff, ambiguous, duplicates
Resultado SB → DTR: active 07 after Blocked exclusion
Sheet URL + readback counts
```

Avoid long narratives unless a row needs manual decision.