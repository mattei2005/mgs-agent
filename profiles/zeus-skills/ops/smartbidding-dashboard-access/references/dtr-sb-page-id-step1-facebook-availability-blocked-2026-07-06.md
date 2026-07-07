# DTR/SB PAGE ID Step 1 — Facebook availability cleanup and `Blocked` rule (2026-07-06)

## Context

During the Bot/DigitalTRChat ↔ SmartBidding PAGE ID Step 1 audit, Rodolfo reviewed the `07 SB sem Bot DTR` tab manually. That tab contains SB rows whose `LOGIN` is in the audited DTR user scope but whose page was not found in Bot/DTR by `FB_PAGE_ID` or `PAGE_ID`.

After removing rows already `STATUS=Blocked`, the tab had 89 rows. Rodolfo opened the Facebook links in column I and found that only 11 page URLs opened; the rest showed Facebook's unavailable-content warning.

## Critical correction

Do not validate Facebook page availability from an unauthenticated Facebook browser session. In this session, an unauthenticated browser redirected every `https://facebook.com/{FB_PAGE_ID}` to the Facebook login wall (`/login/?next=...`). That was falsely classified as “no unavailable warning”. The result was invalid.

When the task is “does Facebook show the unavailable-content warning?”, either:

1. use a Facebook-authenticated browser/session that actually resolves the page content, or
2. treat Rodolfo's manual logged-in browser result as the source of truth if he provides it.

Never classify login-wall pages as available.

## Rodolfo-approved operational rule

If a page URL does not open and shows Facebook unavailable content, set the corresponding SmartBidding Messenger Page row to:

```text
STATUS = Blocked
```

Reason: if the page no longer opens publicly, it may have been unlinked by the gestor, removed from Facebook, or deleted permanently. It should be ignored from comparison/operations.

This is different from temporary Messenger restriction handling (`#2022`), which uses `STATUS=Broadcast` + `RESTRICTED_UNTIL`. For permanently/unavailable Facebook page URLs in the PAGE ID reconciliation workflow, use `Blocked`.

## Workflow for future Step 1 cleanup

1. In the Sheet tab equivalent to `07 SB sem Bot DTR`, filter out rows already `STATUS=Blocked` first.
2. Ask/verify which remaining Facebook URLs in column I truly open in a logged-in Facebook browser.
3. Keep only the opened/available pages in the manual review tab.
4. For the unavailable pages, update SB live `Accounts > Messenger > Page` / `/campaigns/Messenger` to `STATUS=Blocked`.
5. Always backup the exact SB rows before writing.
6. Apply via SB API route `PUT /campaigns/Messenger/update-many` with payload:

```json
{"STATUS":"Blocked","ids":["<SB row ID>"]}
```

7. Re-read full SB `/campaigns/Messenger` scope and validate every target row has `STATUS == Blocked` before reporting success.

## Specific pitfalls from this session

- `07 SB sem Bot DTR` does **not** mean “DTR user missing”. It means the row exists in SB under a scoped `LOGIN`, but no matching Bot/DTR page was found by `FB_PAGE_ID` or `PAGE_ID`.
- The SB e-mail in that tab came from SB field `LOGIN` when `USER_LOGIN` was blank. Header should be `SB LOGIN/USER_LOGIN`, not only `SB USER_LOGIN`.
- Column I should hold the Facebook page URL. If helper scripts insert an extra status column near I/J, preserve or repair headers so Rodolfo can still inspect page links reliably.
- Do not use page name as identity. User-provided open handles may map to SB rows by page name only as a manual convenience; the canonical identity remains `FB_PAGE_ID` first, `PAGE_ID` fallback.

## Validated outcome pattern

In the July 6 run:

- 89 non-Blocked rows remained in `07`.
- Rodolfo identified 10 mapped rows that opened in the current Sheet tab; one provided profile URL did not map safely to an existing row and was not forced into the audit.
- 79 unavailable rows were backed up, updated to `STATUS=Blocked`, and read back from live SB as `Blocked` with 0 failures.

Future reports should say explicitly whether SB/Dash was modified or only the Sheet was filtered. Rodolfo expects unavailable pages to be blocked in SB, not merely removed from the comparison tab.
