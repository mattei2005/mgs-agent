# DTR → SB full-scope restricted-page sync — page-by-page correction (2026-07-03)

## Trigger

Use this when building or operating the automation that detects DigitalTRChat `#2022` temporary Messenger restrictions and writes `RESTRICTED_UNTIL` in SmartBidding.

## User corrections that changed the workflow

Rodolfo corrected several false assumptions:

1. **Scope source is the live migration Sheet, not 1Password inventory.**
   - Sheet: `https://docs.google.com/spreadsheets/d/1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY/edit?gid=562940072#gid=562940072`
   - `gid=562940072` is stable across tab rename. Renaming the tab is OK; deleting/duplicating/recreating the tab changes the gid and breaks gid-based targeting.
   - Use active bot users from the sheet; exclude rows/users marked `Removidos acumulado = X`.
   - Match 1Password DTR items by username/email only after deriving the user list from the Sheet.

2. **`#2022` mixed with other codes still enters the automatic restriction rule.**
   - If latest current report contains `#2022`, apply the SB restriction even if the same report also contains `#10`, `#551`, `#100`, etc.
   - Mixed-code pages must be persisted to local state/database for post-expiry investigation because the companion code may explain why the page got restricted.
   - Suggested summary label: `Broadcast (Restricted + Erros)` = subset of restricted pages where DTR showed `#2022 + other code`.

3. **Account switch must be proven, not assumed.**
   - A test with `disparosopenzed@gmail.com` showed `.account_switch` POSTs returned HTTP 200, but the Subscriber Broadcast campaign dataset stayed identical across many top-bar accounts/seguradores.
   - Same campaign IDs repeated under different labels, proving the run was invalid for per-segurador reporting:
     - `Palmer Larkin` / campaign `4958473`
     - `Skylar Lane` / campaign `4957513`
     - `Georgia Smith` / campaign `4954729`
   - Therefore, do **not** label repeated global campaign results as if they belonged to each segurador.

4. **Report unique pages separately from occurrences/contexts.**
   - A generated Excel had 54 rows but only 3 unique pages. Rodolfo flagged this immediately.
   - Future reports must show unique page counts and, only if useful, a separate `Ocorrências por contexto` tab.
   - Do not present occurrence rows as page count.

## Correct DTR scan design

Use page-level scoping, not unvalidated account-label scoping:

1. Read live Sheet `gid=562940072`.
2. Extract active bot user emails.
3. Match those emails to 1Password DTR credentials.
4. Log into each active DTR bot user.
5. Enumerate the page selector/options for that user.
6. For each page option, use the DTR-supported page filter (`search_page_id=<page option value>`) to fetch that page’s latest `Completed` campaign/report.
7. Classify only the latest Completed report for the page.
8. Cross-check live SmartBidding `Accounts > Messenger > Page` by FB page ID / page name / user login.
9. Skip SB rows with `On-hold`, `Blocked`, or active future `RESTRICTED_UNTIL`.
10. If latest DTR classification includes `#2022`, apply `STATUS=Broadcast` + `RESTRICTED_UNTIL=<same date shown by DTR>` and validate live readback.
11. If latest DTR classification includes `#2022 + other codes`, also persist a mixed-code record with:
    - `page_id`
    - `fb_page_id`
    - `page_name`
    - `bot_user`
    - `segurador` from reliable SB/source only
    - `restricted_until`
    - `dtr_codes`
    - `raw_error`
    - `first_seen`
    - `last_seen`
    - `needs_post_expiry_review: true`

## Validation gates before apply/cron

- Run a small-scale dry-run first (one bot user or one page subset).
- Confirm page counts are **unique pages**, not duplicated context rows.
- Confirm no identical campaign-ID set is repeated under many account labels unless that is explicitly a global view and labeled as such.
- Confirm the canary write uses the same endpoint as production. A single-page legacy helper returned HTTP 400 in this session; the working path was the SB SPA `PUT /campaigns/Messenger/update-many` with readback.
- Apply one canary page and require:
  - before: target row has no active `RESTRICTED_UNTIL`;
  - write HTTP 200;
  - after: `STATUS=Broadcast` and `RESTRICTED_UNTIL=<target date>` from live `/campaigns/Messenger` readback.

## Channel routing

- Templates/broadcast/Utility/Run Approval alerts: Discord channel `1522487422510694450`.
- Restricted pages / `#2022` / `RESTRICTED_UNTIL` alerts: Discord channel `1522442220903337984`.

## Reporting format lesson

For an Excel/Sheet report requested by Rodolfo, use:

### `Páginas únicas`

Columns:

```text
link da pagina
nome da pagina
segurador
data
codigo dos erros
```

One row per unique FB page ID / SB page ID.

### `Ocorrências por contexto` (optional)

Only include if there is a reliable context dimension. If the DTR endpoint is global and account switch is not proven, do not create context rows with fake segurador labels.

## Pitfalls

- HTTP 200 from `/social_accounts/fb_rx_account_switch` is not proof that the campaign dataset changed.
- A top-bar account name is not safe to use as `segurador` unless the subsequent dataset is proven account-scoped.
- Repeated campaign IDs across account labels mean the run is invalid for per-segurador reporting.
- Never report “54 pages” when it is 54 rows but 3 unique pages.
- Do not use all 1Password `Digitaltrchat - Disparos*` items as production scope; use the Sheet.
