# DTR restricted-pages cron — authoritative flow correction (2026-07-06)

## Context

Rodolfo corrected the restricted-pages monitor/report flow. The prior SB-only monitor treated `SmartBidding Accounts > Messenger > Page` rows with active `RESTRICTED_UNTIL` as if they proved a page was restricted. That is wrong.

SmartBidding proves only operational state (`STATUS`, `RESTRICTED_UNTIL`). The Bot/DigitalTRChat latest Completed report is the authority for whether the page is actually restricted and what error/date/time caused it.

## Correct production flow

1. Read the live migration sheet (`Migração 22/06`).
2. Include only active bot users/seguradores; skip rows with `Removidos acumulado = X`.
3. Read live SmartBidding Messenger Page rows first only to build a skip-list of pages already restricted:
   - `STATUS=Broadcast`
   - active/future `RESTRICTED_UNTIL`
4. When scanning DTR for an active bot user/segurador, skip pages already in the SB restricted skip-list. They are already out of sending and do not need repeated DTR checks each run.
5. For remaining pages, read only the newest/last `Completed` report per page.
6. If no sent message/latest Completed exists: ignore as neutral (`NO_CAMPAIGN_DATA_YET` / `Sem campanha enviada`), not an error.
7. If newest Completed contains `#2022`, pure or mixed with other errors, classify as a newly confirmed restricted page.
8. Extract restriction date/time from the DTR error text.
9. Apply in SB:
   - `STATUS=Broadcast`
   - `RESTRICTED_UNTIL=<DTR date>`
10. Validate readback on the exact SB row.
11. Only after successful readback, alert channel `1522442220903337984`.

## Report requirements

Restricted-page alerts/reports must include:

- page name
- bot user
- segurador/account
- small `PAGE_ID`
- large `FB_PAGE_ID`
- DTR error codes
- DTR restriction date/time
- SB readback/log artifact when relevant

The large `FB_PAGE_ID` is mandatory because Rodolfo uses `https://facebook.com/{FB_PAGE_ID}` directly to open/verify the page.

## Hard pitfalls

- Never call a page “restrita” from SB-only evidence.
- Never let the SB-only cron post operational restricted-page alerts. It may be diagnostic only and must be explicitly labelled as SB-only.
- `RESTRICTED_UNTIL` in SB is support state, not proof of current Facebook/Messenger restriction.
- Do not re-check already restricted pages in DTR on every run; use the SB skip-list to reduce runtime.
- `On-hold` rows are not reactivated automatically.
- `Blocked` rows require separate dual diagnosis: public page availability plus MGS/segurador/profile operational access.
- Mixed `#2022 + other codes` still counts as restricted and should be applied/reported, while companion codes remain useful for later diagnosis.

## Validated runtime evidence from correction session

A post-fix production run completed successfully:

```text
Status                     OK
Start                      2026-07-06 17:30 ET
Finish                     2026-07-06 17:47 ET
Users active in sheet       76
1Password users matched     76
DTR accounts scanned        216
DTR pages in scope          2,590
Already restricted skipped  353
#2022 found                 20
SB writes                   13
New restrictions alerted    0
Errors                      0
```

The absence of alert was correct because no new restriction met the full gate: DTR-confirmed `#2022` + SB write/readback validated as a new alert row.
