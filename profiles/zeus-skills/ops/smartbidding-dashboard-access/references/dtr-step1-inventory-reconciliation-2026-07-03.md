# DTR Step 1 inventory reconciliation — 2026-07-03

## Context

Rodolfo corrected the ordering for the DigitalTRChat/Smart Bidding page-health workflow. The first step is not page-error diagnosis; it is inventory cleanup so later cron/report logic does not pick the wrong duplicate account or report planned/removed users as failures.

## Correct Step 1 order

1. Read the live migration sheet first (`Migração 22/06`, gid `562940072`).
2. Build active scope from rows with:
   - valid `User` email;
   - `NO APP` present;
   - `Removidos acumulado != X`.
3. Keep rows with `Removidos acumulado = X` as explicit out-of-scope evidence; do not spend dashboard time opening them unless Rodolfo asks.
4. Discover matching 1Password DigitalTRChat items by username.
5. For each active bot user, log into DigitalTRChat and enumerate every top-bar segurador/account (`.account_switch`).
6. Before reading pages, detect duplicate segurador/account names within that bot user.
   - duplicate active segurador → report and skip page audit for that segurador;
   - do not choose one duplicate arbitrarily.
7. Cross-check DTR account names against the sheet using normalized names while preserving originals.
   - active match → may inspect pages;
   - `X` match → `IGNORED_X`, skip pages;
   - not in sheet / wrong user → `OUT_OF_SCOPE`, skip pages.
8. For valid active non-duplicate accounts, list `search_page_id` pages.
   - appears once and has zero pages → `NO_PAGES`, report and ignore as non-error;
   - has pages → valid for Step 2/page-health.
9. Only after this inventory gate should a future Step 2 inspect latest Completed reports, sends/leads, delivery, or DTR error codes.

## Classification labels

Use stable labels in code/reports:

```text
VALID_FOR_STEP2              active sheet match, non-duplicate, pages present
REPORT_DUPLICATE_SKIP_PAGES  duplicate segurador/account; no automatic choice
NO_PAGES_REPORT_IGNORE       appears once, no pages; reportable inventory note, not error
IGNORED_X_SKIP_PAGES         sheet says X; confirmed/out of scope
OUT_OF_SCOPE_SKIP_PAGES      not in sheet or belongs to another sheet user
AUTH_OR_CONNECTION_ERROR     real login/account/page-selector failure
```

## Execution result that validated the pattern

Manual read-only Step 1 run on 2026-07-03:

```text
Sheet rows: 351
Active rows: 183
X rows: 32
Active users: 69
1P matched users: 68
Users scanned in DTR: 68
DTR accounts: 217
VALID_FOR_STEP2: 176
IGNORED_X_SKIP_PAGES: 19
NO_PAGES_REPORT_IGNORE: 4
OUT_OF_SCOPE_SKIP_PAGES: 8
REPORT_DUPLICATE_SKIP_PAGES: 10 occurrences / 3 unique seguradores
Auth/login errors: 0
Active sheet rows not found in DTR: 0
```

Notable duplicate uniques:

```text
Reginaldo Novaes Santiago — disparoseggbev@gmail.com — 6 occurrences — active
Hùng Hợp Tiến — disparosfinancetopfeed@gmail.com — 2 occurrences — X
Isidoro Cristina Barbosa Martins — disparoszytivaes@gmail.com — 2 occurrences — active
```

Notable `NO_PAGES`:

```text
Dek Fiyan — disparoscliquet@gmail.com
Om Gendut — disparoscliquet@gmail.com
Jaqueline Dagostin — disparosfinanceadx@gmail.com
Debora Monteiro Lima — disparosvizioidmxcces@gmail.com
```

One active user lacked matching 1Password credentials in that run:

```text
disparosfincgriffinuscaren@gmail.com — Ricardo Gabriel Monteiro — sheet line 69 — NO APP B002
```

## Reporting style lesson

When Rodolfo asks “ta iai?” or “o que tem que fazer?”, answer with the next operational action and concise status. Do not append raw `[REPORT-INFRA]` blocks to normal responses. If infra reporting is required, send it through the proper infra flow/channel separately; the user-facing answer should remain operational.