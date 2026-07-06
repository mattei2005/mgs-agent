# DTR restricted-pages authoritative cron correction (2026-07-06)

## Context

Rodolfo corrected the restricted-pages monitor design. The previous SB-only monitor treated SmartBidding `RESTRICTED_UNTIL` as if it proved a page was newly restricted. That is wrong.

## Authoritative source

A page may be reported as **newly restricted** only after reading DigitalTRChat/Bot live data:

1. Read the live migration sheet.
2. Include only active bot users/seguradores; skip rows with `Removidos acumulado = X`.
3. Log into DigitalTRChat for the active users.
4. Iterate valid top-bar seguradores/accounts and page selector entries.
5. Skip pages already restricted in SmartBidding (`STATUS=Broadcast` + active/future `RESTRICTED_UNTIL`) to save DTR time.
6. For remaining pages, read only the latest `Completed` campaign/report per page.
7. If no message/campaign was sent, ignore as neutral — not a restriction.
8. If the latest report contains `#2022`, pure or mixed with other errors, classify as a confirmed restricted page.
9. Extract restriction date/time from the DTR error description.
10. Apply `STATUS=Broadcast` + `RESTRICTED_UNTIL=<DTR date>` in SmartBidding and validate readback.
11. Alert the restricted-pages channel only after DTR confirmation and SB readback validation.

## Report requirements

Restricted-page alerts and Sheets must include:

- page name
- bot user
- segurador/account
- small `PAGE_ID`
- large `FB_PAGE_ID`
- DTR error code(s)
- DTR restriction date/time
- SB write/readback status when applicable

`FB_PAGE_ID` is required so Rodolfo can open `https://facebook.com/{FB_PAGE_ID}` directly and verify the page manually.

## Safety gates

- SB-only data is support state, not proof. Never call a row a “new restricted page” from SB-only evidence.
- `On-hold` rows must not be reactivated automatically.
- `Blocked` rows must not be set to Broadcast automatically; blocked pages require separate dual diagnosis: public page availability plus segurador/profile operational access.
- If DTR context is unsafe (repeated non-empty campaign signatures across accounts/seguradores), skip writes or dedupe only by unique SB row ID according to the existing validated workflow.
- Mixed `#2022 + other errors` still gets restricted handling, but persist/report the companion codes for post-expiry review.

## Cron shape

Correct cron class:

```text
DTR -> SB restricted-pages cron — active users from sheet (skip X), skip already restricted SB pages, latest Completed #2022 -> alert + SB update
30 7,15 * * * flock -n /var/lock/dtr_sb_page_health_sync.lock /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --quiet-noop >/dev/null 2>&1
```

SB-only monitor may exist as diagnostic/state support, but must not post operational “new restricted page” alerts unless explicitly labelled as SB-only diagnostic and not mixed with DTR-confirmed reports.
