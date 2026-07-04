# DTR → SB full-scope restricted-page sync — 2026-07-03

## Trigger

Use when automating or auditing SmartBidding `RESTRICTED_UNTIL` writes based on DigitalTRChat/ChatPion `#2022` temporary Messenger restrictions.

## Rodolfo corrections captured

1. **Scope source is the Google Sheet, not 1Password.**
   - Sheet: `https://docs.google.com/spreadsheets/d/1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY/edit?gid=562940072#gid=562940072`
   - `gid=562940072` is stable across tab renames; renaming the tab is OK. Deleting/recreating/duplicating the tab changes the gid and can break scope.
   - Use active bot users from this sheet, excluding rows/users marked `Removidos acumulado = X`.
   - Do **not** use every `Digitaltrchat - Disparos*` item in 1Password as the execution scope; 1P contains extra/inactive access.

2. **Full DTR traversal is required.**
   - For each active bot user from the sheet, log into DigitalTRChat.
   - Iterate every top-bar segurador/account (`.account_switch` / `/social_accounts/fb_rx_account_switch`).
   - For each segurador, inspect all pages and only the latest `Completed` campaign/report per page.
   - Historical completed reports are not current truth.

3. **SmartBidding live filter before writes.**
   - Re-read live `Accounts > Messenger > Page` under `digital-trust + digital-trust-2`.
   - Ignore `On-hold` and `Blocked` rows.
   - Ignore rows already carrying active `RESTRICTED_UNTIL` until the release date; once expired, they return to scope.
   - Match carefully by `FB_PAGE_ID` / `PAGE_NAME` / `USER_LOGIN`; ambiguous matches must not be written.

4. **#2022 write rule.**
   - If latest DTR report contains current `#2022`, apply the restriction, whether pure or mixed with other codes.
   - Set/keep `STATUS=Broadcast`.
   - Set `RESTRICTED_UNTIL` to the same calendar date shown in DTR (not D+1).
   - Validate by live SB readback for every write.
   - Do not auto-write pages with only `PERMISSION`, `APP_DELETED`, `#10`, `#551`, `#100`, `TOKEN`, `OTHER`, or no latest Completed/report.

5. **Mixed-code persistence.**
   - If a page has `#2022 + other codes`, still apply the restriction, but save it to local state/database for post-expiry investigation.
   - Suggested fields: `page_id`, `fb_page_id`, `page_name`, `bot_user`, `segurador`, `restricted_until`, `dtr_codes`, `raw_error`, `first_seen`, `last_seen`, `needs_post_expiry_review=true`.

6. **Report labels.**
   - Keep `Broadcast (Restricted)` as the total active restricted Broadcast pages.
   - Add a subset line such as `Broadcast (Restricted + Erros)` for pages where DTR had `#2022` plus companion codes.
   - This count requires a DTR check of the currently restricted pages; do not estimate it from SB alone.

7. **Alert channels.**
   - Páginas restritas / `#2022` / `Restricted Until`: Discord channel `1522442220903337984`.
   - Templates, Broadcast Template, Utility rollout, Run Approval, template cron/errors: Discord channel `1522487422510694450`.

## Safe rollout sequence

1. Implement/modify script.
2. Run a small dry-run with one sheet user and all their seguradores.
3. Validate:
   - sheet active users count;
   - 1P username matches;
   - seguradores iterated;
   - latest Completed pages counted;
   - `#2022` pure/mixed split;
   - no script errors;
   - no ambiguous SB matches.
4. Apply one canary page via SB `update-many` endpoint and validate live readback.
5. Apply one full user only.
6. Only after that, enable cron at `07:30` and `15:30` ET with `flock`, quiet no-op output, and critical alerts on sheet/DTR/SB/write/readback failures.

## Implementation notes from validated canary

A small dry-run for `disparosopenzed@gmail.com` validated the full traversal shape:

```text
Planilha active users: 58
1P username matches: 58/58
User tested: disparosopenzed@gmail.com
Seguradores traversed: 18
Pages/latest Completed: 4,374
#2022 operational: 1,962
Already restricted active: 1,764
Candidate writes: 198
Mixed #2022 + codes: 54
Script errors: 0
```

One canary write was validated on SB via `PUT /campaigns/Messenger/update-many`:

```text
Page: Hope Warren
PAGE_ID: 13820
FB_PAGE_ID: 982994414889529
Before: STATUS=Broadcast, RESTRICTED_UNTIL empty
After: STATUS=Broadcast, RESTRICTED_UNTIL=2026-07-22
Readback: validated true
```

A legacy single-page utility path using `/accounts/Messenger` returned HTTP 400 in this session. The durable lesson is not “that tool is broken”; it is: for this class of page bulk/sync writes, prefer the validated `PUT /campaigns/Messenger/update-many` route and require readback.

## Pitfalls

- Do not run a full dry-run first if a smaller canary will validate the logic faster. Rodolfo explicitly prefers small-scale validation: if it works correctly on one user/page, then scale.
- Do not conflate SB-only restricted count with DTR mixed-code count. SB can say 209 restricted, but only DTR can say which of those are `#2022 + #10/#551/#100/etc.`.
- Do not leave a partial/old cron enabled while designing the corrected one. Disable partial automation before building the correct full-scope workflow.
- Do not route Utility template approval reports into the restricted-pages channel.
