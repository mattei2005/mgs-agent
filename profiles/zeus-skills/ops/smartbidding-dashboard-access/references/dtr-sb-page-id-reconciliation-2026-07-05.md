# DTR ↔ SmartBidding Page ID reconciliation — 2026-07-05

## Context

Rodolfo requested a read-only cross-audit between DigitalTRChat/Bot page registration and SmartBidding `Accounts > Messenger > Page` because he suspected wrong page identifiers in SmartBidding.

Fields compared:

- DTR/Bot page name
- DTR/Bot small PG/Page ID shown after the `|` on the page card
- DTR/Bot large Facebook Page ID
- DTR/Bot segurador/account name
- SmartBidding `PAGE NAME`
- SmartBidding `PAGE ID`
- SmartBidding `FB PAGE ID`
- SmartBidding `PROFILE NAME` / `USER_LOGIN`

## Correct live scope

1. Read active bot users from the migration/control sheet, not all 1Password DigitalTRChat items.
2. Active filter used in the validated run:
   - `User` contains an email
   - `NO APP` is non-empty
   - `Removidos acumulado != X`
3. Discover 1Password DTR items broadly by title containing `digitaltrchat`, then match the `username` field to the active sheet users.
4. For each active DTR user, log in live and iterate every top-bar `.account_switch` segurador/account.
5. For this page-ID inventory task, use `https://digitaltrchat.com/social_accounts/index` / page cards, not campaign reports.
6. Fetch SmartBidding live from `/campaigns/Messenger` under active `digital-trust + digital-trust-2` publishers; do not use snapshots.

## DTR extraction detail

On `social_accounts/index`, each page card has observed text shape:

```text
Analytics <PAGE_NAME> [optional email] <FB_PAGE_ID> | <PG_PAGE_ID>
```

Example:

```text
Analytics Karina Duarte karina@gmail.com 320023591203685 | 743
```

Parsing rule:

- Right side of `|` = DTR small PG/Page ID.
- Long number before `|` = Facebook Page ID.
- Text before optional email/long number = page name.
- The top-bar selected account/segurador name is operational context and should be compared to SB `PROFILE_NAME` when available.

Important DOM pitfall: query only `.page_list_ul` cards for page rows. Including `.card.author-box` can double-count each page because page cards may also have nested/ancestor card classes.

## Matching order

Use high-confidence matching in this order:

1. `(USER_LOGIN, PAGE_ID)`
2. `(USER_LOGIN, FB_PAGE_ID)`
3. global `FB_PAGE_ID`
4. `(USER_LOGIN, PAGE_NAME normalized)` only as probable fallback, clearly labeled

Classify separately:

- `OK` — name, small ID, FB Page ID, and segurador/profile match.
- `DIVERGENTE` — exists on both sides but one or more fields differ.
- `NO_SB_MATCH` — exists in DTR/Bot but not in SmartBidding.
- `NO_DTR_MATCH` — exists in SmartBidding but not in DTR/Bot.
- `DUPLICATE` — duplicate same `(bot user, FB Page ID)` or `(bot user, PAGE ID)` on either side.

Do not assume a name-only match is safe for writes. For correction planning, `FB_PAGE_ID` match is stronger than page name.

## Validated run shape from 2026-07-05

Read-only run completed with:

```text
Active sheet users:       76
Matched DTR credentials:  76/76
DTR logins OK:            76/76
DTR seguradores/accounts: 214
DTR pages:                2,902
SB live rows total:       3,218
SB rows for active users: 2,534
OK matches:               2,360
Issues:                   568
```

Issue breakdown:

```text
DTR page not in SB:       392
SB page not in DTR:       26
Divergent existing rows:  150
Duplicate detected:       1
```

Divergent breakdown:

```text
PAGE_ID mismatch:         125
PAGE_NAME mismatch:       25
FB_PAGE_ID mismatch:      0 in confirmed high-confidence matches
SEGURADOR/profile diff:   29 cases, overlapping mostly with PAGE_ID mismatches
```

Operational interpretation: in that run, the primary confirmed data-quality issue was the small `PAGE ID` in SmartBidding, not the large `FB PAGE ID`. `NO_SB_MATCH` rows need separate triage before correction because they may be old/out-of-scope DTR pages or genuinely missing SB registrations.

## Execution/reporting notes

- This is read-only unless Rodolfo explicitly asks to apply corrections.
- Report unique pages and issue classes, not just occurrences.
- Always output a CSV/JSON evidence file for large audits, but final Discord response should be a concise executive summary with counts and the file paths.
- If the run is long, detach via a supervised process/systemd-run and poll logs; avoid relying on gateway foreground lifespan.
