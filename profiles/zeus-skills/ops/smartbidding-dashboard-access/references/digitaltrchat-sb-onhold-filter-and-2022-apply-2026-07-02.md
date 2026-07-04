# DigitalTRChat + Smart Bidding: On-hold filter before bot error reports — 2026-07-02

## Trigger

Use when Rodolfo asks for a DigitalTRChat bot/page health audit, `#2022` cleanup, or error categorization from Subscriber Broadcast reports.

## Correction learned

A DigitalTRChat latest `Completed` campaign report is not enough to decide current operational action. Smart Bidding Page status must be checked first.

If the matching SB Messenger Page row is already:

- `On-hold`
- `Blocked`

then the page is not entering broadcast scheduling and should be excluded from the current operational error report/action list, even if its latest DigitalTRChat `Completed` report from yesterday has errors.

This came from Rodolfo/Ciro revenue review: pages under R$100/month were moved to `On-hold`; their old Completed reports can still show errors but they are no longer active senders.

## Required sequence

1. Run DigitalTRChat audit live.
2. For each bot user, iterate all top-bar seguradores/accounts (`.account_switch`, `POST /social_accounts/fb_rx_account_switch`).
3. For each page, inspect only the newest `Completed` campaign report.
4. Capture live SB Messenger Page rows (`/campaigns/Messenger`) for full MGS scope.
5. Join DTR page to SB row by `USER_LOGIN` + `PAGE_ID`; if multiple rows, prefer `PROFILE_NAME`/segurador + `PAGE_NAME` match.
6. Exclude rows with `STATUS in {On-hold, Blocked}` before reporting errors or applying `#2022` cleanup.
7. Report counts before and after SB filter: total DTR contexts, ignored `On-hold`, ignored `Blocked`, missing SB match, operational contexts, errors.
8. Apply `#2022` only to operational rows, preferably `#2022` pure first; keep mixed rows for review unless Rodolfo explicitly says otherwise.

## Validated result pattern

After applying the SB filter in the session:

- DTR contexts before filter: 2742
- Ignored On-hold: 1602
- Ignored Blocked: 27
- Operational contexts: 1113
- `#2022` pure after filter: 208
- Applied to 208 SB rows with `STATUS=Broadcast` and `RESTRICTED_UNTIL = same error date`
- Readback failures: 0

## Pitfalls

- Do not report errors from pages already `On-hold`; those errors are historical noise.
- Do not assume Openzed/Cliquet subdomain pages missing from some reports means they are absent from SB. They can appear in `Accounts > Messenger > Page` while reporting migration to TEC/backfilled reports is in progress.
- Do not apply bulk `#2022` from raw DTR counts before SB status filtering; it can overcount inactive pages massively.
- If SB match is missing, label separately instead of applying writes.


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
