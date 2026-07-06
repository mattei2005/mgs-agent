# DTR/SB Step 1–2 segurador audit corrections — 2026-07-03

## Why this exists

During a live Step 1/Step 2 DTR/SB audit, Rodolfo corrected the workflow several times. These corrections are durable for any future daily cron or manual audit of DigitalTRChat seguradores/pages against the migration sheet and Smart Bidding.

## Step 1 is inventory hygiene, not page-error audit

Correct order:

1. Read the migration/control sheet first.
2. Apply sheet filters before opening DTR page/report details.
3. If `Removidos acumulado = X`, skip the segurador entirely. The `X` wins even if the segurador is duplicated in DTR.
4. If the `X` is later removed, the next Step 1 run should inspect that segurador normally and report duplicates/no-pages/auth issues then.
5. Detect duplicate segurador/account entries in DTR before page health checks. Do not choose a random duplicate.
6. If a segurador appears exactly once and has no pages inside, classify as `NO_PAGES`: report/ignore as inventory signal, not an operational error.
7. If pages are reconnected but have no sends/leads, do not classify that alone as an error; it may be normal without baseline expectation.
8. Rodolfo Mattei and Geizian Pereira accounts seen in DTR lists are noise for this workflow; ignore and do not report.

## Sheet exceptions/overrides from this session

These seguradores were not in the sheet yet because Geizian had not added them, but Rodolfo confirmed they are current active replacements for blocked old seguradores. Treat as active overrides until the sheet is updated:

```text
Segurador           User DTR                                  App
------------------  ----------------------------------------  ----
Andi Setiawan       disparoseggbev@gmail.com                  B003
Karoline Chaves     disparosfincgriffinuscaren003@gmail.com   B002
Akew Rider          disparosinfinitynexx@gmail.com            B009
Anggiat Hutajulu    disparosinfinitynexx@gmail.com            B009
```

## 1Password discovery pitfall

Do not discover DigitalTRChat credentials by brittle title prefix. Valid items may have spacing/title variants such as:

```text
Digitaltrchat -  Disparos Fincgriffin US-CAR-EN
```

Discover candidate `Digitaltrchat` items broadly, then match by the `username` field against the active bot user email from the sheet.

## Step 2 dry-run before apply

Run Step 2 read-only/dry-run first. Do not apply SB writes until:

- Step 1 corrections are integrated into the Step 2 script;
- context switching is safe for multi-account DTR users;
- `X` rows, Rodolfo/Geizian noise, and sheet overrides are filtered before write planning;
- every planned write has SB readback validation logic.

If the script reports `account_context_signatures_not_unique`, skip writes for that user. This means DTR account switching may be returning repeated/ambiguous context and errors could be attributed to the wrong segurador.

## Report interpretation

For Step 2 reports:

- `Blocked`/`On-hold` pages are not active scheduling errors.
- `Broadcast`/`Campaign` are operational and actionable.
- `#2022` can suggest `RESTRICTED_UNTIL` action, but only after the Step 1 filters and context-safety checks above.
- `#10`, `#551`, `#100`, `PERMISSION`, `APP_DELETED`, `TOKEN`, `OTHER` should generally be surfaced as diagnosis/NOTES candidates, not blindly auto-fixed.
- Page with no campaign/message sent inside the segurador at the time of inspection is **not an error** and must not be treated as unsafe context. It only means that, on that day/moment, no gestor had used that page in a sent campaign yet. If a gestor later creates/runs a campaign for that page, future runs will have data to inspect. Classification should be neutral/report-only (e.g. `NO_CAMPAIGN_DATA_YET` / `SEM_CAMPANHA_ENVIADA`), not a blocker.
