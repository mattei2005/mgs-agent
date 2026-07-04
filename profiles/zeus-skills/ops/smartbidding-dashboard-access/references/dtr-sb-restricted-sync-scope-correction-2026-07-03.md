# DTR → SB Restricted Until sync — scope correction (2026-07-03)

## Trigger

Use when implementing or reviewing automation that reads DigitalTRChat `#2022` errors and writes `RESTRICTED_UNTIL` in SmartBidding Messenger Page rows.

## User correction

Rodolfo corrected the proposed automation design: the source of which bot users to log into is **not all 1Password `Digitaltrchat - Disparos*` items**. 1Password contains credentials for users that may not currently be operational.

The source of active bot users is the Google Sheet `Migração 22/06` in spreadsheet:

```text
1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY
GID: 562940072
```

Relevant columns observed in CSV export:

```text
Removidos acumulado, User, Segurador, Conta dev, USUARIO, NO APP, OBS, ...
```

Operational count observed in this session:

```text
Rows with bot User email:                      220
Unique bot users in sheet:                      77
Unique operational users without X:             58
Rows with Removidos acumulado = X:              63 rows / 38 unique users
```

These counts are runtime observations, not constants. Re-read the live sheet every run.

## Correct automation contract

Every run must be live/from scratch:

1. Read the live Google Sheet.
2. Build the active bot-user scope from `User` rows that are operational for the current process.
   - Do not use all 1Password items as the primary scope.
   - Ignore or separately classify rows marked `Removidos acumulado = X` depending on the task.
3. For each active bot user, log into DigitalTRChat.
4. Inside that login, iterate **all top-bar seguradores/accounts**.
   - Do not trust the first/default segurador after login.
   - Use the account switcher route/mechanism discovered for DigitalTRChat.
5. For each segurador, enumerate all pages.
6. For each page, inspect only the latest `Completed` campaign/report with usable `Campaign report` data.
   - Do not aggregate historical Completed reports as current status.
7. Classify the latest error.
8. Before applying or reporting as active error, cross-check live SmartBidding Messenger Page rows.
9. Ignore from DTR error reporting/apply:
   - `STATUS=On-hold`
   - `STATUS=Blocked`
   - rows with active future/today `RESTRICTED_UNTIL`
10. For pure/current `#2022`, set in SB:
   - `STATUS=Broadcast`
   - `RESTRICTED_UNTIL=<same date shown by DTR>`
   - validate by live readback.
11. Pages automatically re-enter scope only after the restriction date clears/expires in SB/live state.

## Readiness gate

Do **not** say the cron is ready to enable until the implementation proves in dry-run that it performs the exact scope above:

```text
sheet users -> DTR login -> every top-bar segurador -> every page -> latest Completed only -> SB live filter -> candidate #2022 list
```

Required validation before `--apply`:

- sheet read count and active bot-user count reported;
- number of DTR users actually logged in;
- number of top-bar seguradores visited;
- number of page contexts audited;
- skipped counts for `On-hold`, `Blocked`, and active `RESTRICTED_UNTIL`;
- candidate pure `#2022` rows with SB row IDs and target dates;
- no ambiguous SB matches;
- dry-run output reviewed before writes.

## Pitfalls

- **Wrong scope:** all 1Password DTR items ≠ active bot users. Use the sheet.
- **Partial DTR audit:** logging in and reading the default account only is incomplete; every top-bar segurador/account must be visited.
- **Historical false positives:** older Completed reports can show errors for pages now recovered, on-hold, blocked, or migrated. Latest Completed only.
- **SB status filter:** pages on `On-hold` or `Blocked` should not create current operational error noise because they are not in scheduling.
- **Premature enablement:** if only a detector and single-page updater exist, the system is not ready for production cron.
