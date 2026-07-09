# DTR↔SB Phase 1 — global ignore gate and pending reconciliation (2026-07-08)

## Context

During the Phase 1 DTR↔SmartBidding reconciliation, Zeus initially misread the active Sheet tabs as if all visible rows were still pending. Rodolfo corrected the interpretation:

- Some pages still appear in DTR because they were inherited with old seguradores/profiles.
- They are outside the current MGS niche/scope and must not be used operationally.
- Even if they “match 100%” in DTR/SB or still appear in a restored backup tab, they must be ignored globally.

This correction applies to future Phase 1 refreshes, SB registration checks, lead scans, restricted-page scans, and pending reports.

## Canonical rule

`/root/mgs-agent/data/mgs-global-page-ignore-list.json` is a pre-audit exclusion gate.

Load it before any of these operations:

- DTR→SB coverage comparison (`DTR sem SB`)
- SB→DTR inverse comparison (`SB sem DTR`)
- DTR lead/subscriber scan for pages missing in SB
- SB Messenger Page registration from Sheet payloads
- restricted-page / page-health scans
- schedule/backfill/template operational checks

Global ignore wins over all matching logic:

```text
If FB_PAGE_ID matches ignore-list → exclude.
Else if bot_user + PAGE_ID/PG matches ignore-list → exclude.
```

Do not report ignored rows as pending, missing, actionable, or “needs checking”. Do not scan them in DTR. Do not create them in SB. Do not schedule/backfill them.

## Sheet interpretation

For Sheet `1VNz7l1soafiju0v89H0IfaKJHcgioVjUw6nXyORl9oI`:

- `gid=130786795` / `Fase 1 - DTR sem SB`: after applying ignore-list, actionable pending can be zero even if restored/custom backup tabs still list rows.
- `gid=1798040517` / `Fase 1 - DTR sem SB Custom BKP`: backup detail of the 36 ignored rows.
- `gid=1627881114` / `Fase 1 - DTR sem SB Custom FULL BKP`: historical/custom full view; useful for audit history, not necessarily current action.
- `gid=907050576` / `CADASTRO NA DASH`: payload tab. Rows present here are not automatically pending; verify live SB and apply global ignore before calling them missing.

## 2026-07-08 live resolution example

Rodolfo corrected that `Clara Bailey` was removed from DTR and was not an MGS page:

```text
login       disparosxyvlov@gmail.com
page        Clara Bailey
PAGE_ID     13794
FB_PAGE_ID  838404979365746
status      GLOBAL_IGNORE / not MGS
```

Action taken:

- Added to `/root/mgs-agent/data/mgs-global-page-ignore-list.json`.
- Marked in `CADASTRO NA DASH` as `IGNORAR / GLOBAL_IGNORE_DO_NOT_SCAN`.
- Patched the SB registration script to skip ignore-list rows before planning creates.
- Dry-run then returned:

```text
Sheet actionable rows   113
Already existing in SB   113
Planned creates            0
Skipped/errors             0
```

## Pending report rule

When Rodolfo asks “what is pending?” for Phase 1 after prior work:

1. Do **not** answer from the visible Sheet alone.
2. Re-check live SB for the relevant buckets.
3. Apply global ignore before computing pending.
4. Treat stale tabs as historical until refreshed.
5. Separate:
   - truly missing SB registration;
   - global-ignore rows;
   - stale login-divergence rows already fixed live;
   - `SB sem DTR não Blocked` rows that still exist live.

The final concise shape should be:

```text
DTR sem SB actionable        N
Global ignore                N
Cadastro na Dash pending     N
Login divergente live        N
SB sem DTR não Blocked live  N
```

## Pitfall

Do not say “114 pending cadastro” just because `CADASTRO NA DASH` has 114 rows. In the July 8 case, 113 were already live in SB and the remaining 1 was a global-ignore page. The correct pending registration count was zero.
