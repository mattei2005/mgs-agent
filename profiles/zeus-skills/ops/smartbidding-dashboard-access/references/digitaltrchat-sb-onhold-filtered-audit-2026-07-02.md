# DigitalTRChat + Smart Bidding on-hold filtered audit — 2026-07-02

## Trigger

Use this when Rodolfo asks to audit DigitalTRChat bot/page errors, especially after Smart Bidding page statuses have been updated by revenue/health rules.

## Key correction from Rodolfo

A page can have a recent `Completed` campaign report with an error, but if Ciro/Rodolfo already changed the page to `On-hold` in Smart Bidding, it is no longer sending broadcasts and must not be included in actionable error counts.

Correct current-state rule:

```text
DigitalTRChat current error = latest Completed report only
Operational current error = latest Completed report AND SB Page STATUS in Broadcast/Campaign
Ignore for actionable report/remediation = SB Page STATUS On-hold or Blocked
```

This matters because MGS reviewed 30-day page revenue and pages under the retention threshold may be put `On-hold` the day after the DTR send. The DTR error is real history, but not an active broadcast problem.

## Full audit sequence

1. For each bot user, log into DigitalTRChat.
2. Enumerate every top-bar segurador/account via `.account_switch`.
3. For each account, switch using:

```text
POST /social_accounts/fb_rx_account_switch
payload: id=<data-id>
```

4. Reload `/messenger_bot_enhancers/subscriber_broadcast_campaign`.
5. Parse `search_page_id` for pages in that segurador.
6. For each page, query latest `Completed` campaign only via `/subscriber_broadcast_campaign_data`, ordered newest first.
7. Open only that campaign's report via `/campaign_sent_status` + `/campaign_sent_status_data`.
8. Join the page to live SB `/campaigns/Messenger` using at minimum:

```text
USER_LOGIN / LOGIN
PAGE_ID
PAGE_NAME
PROFILE_NAME (segurador)
```

9. Exclude SB `STATUS=On-hold` and `STATUS=Broadcast` from actionable counts.
10. Keep SB `STATUS=Broadcast` and `STATUS=Campaign` as operational.
11. Report SB-unmatched rows as their own bucket.

## `#2022` remediation rule after SB filter

Split rows into:

```text
#2022 puro       latest report has #2022 and no other non-OK category
#2022 misturado  latest report has #2022 plus #10/#551/OTHER/etc.
```

Default action after Rodolfo approval:

```text
Only #2022 puro + SB operational status => update SB row
STATUS = Blocked
RESTRICTED_UNTIL = parsed restriction date + 1 calendar day
```

Do not apply automatically to mixed `#2022` unless Rodolfo explicitly includes it.

Bulk update pattern:

1. Capture live `/campaigns/Messenger` via headed/Xvfb SB session.
2. Build exact target rows and parse target dates.
3. Backup full SB rows before writing.
4. Group by `RESTRICTED_UNTIL` date.
5. PUT `/campaigns/Messenger/update-many` with:

```json
{"ids":["<SB row ID>"],"STATUS":"Broadcast","RESTRICTED_UNTIL":"YYYY-MM-DD"}
```

6. Re-read `/campaigns/Messenger` and validate every target row:

```text
STATUS == Blocked
RESTRICTED_UNTIL == target date
PAGE_ID / USER_LOGIN / PROFILE_NAME match intended page
```

## Error-category follow-up rules

For Rodolfo review, provide exact error strings and current examples by segurador/page.

For `#10_WINDOW` and `#551_UNAVAILABLE`, inspect the last five `Completed` campaign reports for each page after the SB status filter and summarize:

```text
total pages with category
with 5 Completed available
same5
diff5
less than 5 Completed
```

Observed interpretation:

- `#10_WINDOW` often repeats across the last five sends and may be structural/policy-window related.
- `#551_UNAVAILABLE` often varies and is more subscriber-level/noisy.

## Migration sheet cross-check

The migration sheet can be read via Drive export even if Google Sheets API is disabled for the service-account project.

Known file:

```text
Drive file: Migração app - Digitaltrust
Sheet ID: 1sTkBE6RQPQ3obq1j6m8RSu_22beEUbZjkQ-OttI01XY
Tab: Migracao 22/06
```

Drive export route:

```text
GET https://www.googleapis.com/drive/v3/files/<sheet_id>/export?mimeType=text/csv
```

The `gviz` CSV endpoint can target the tab:

```text
https://docs.google.com/spreadsheets/d/<sheet_id>/gviz/tq?tqx=out:csv&sheet=Migracao%2022/06
```

Relevant columns seen:

```text
Removidos acumulado  -> X marker for removed/fallen app/profile tracking
Segurador
USUARIO
NO APP
Migracao
OBS                  -> may contain "Perfil antigo: <nome>"
```

When cross-checking `PERMISSION` / `APP_DELETED`:

- Compare DTR `segurador` / SB `PROFILE_NAME` against `Segurador` values with `Removidos acumulado = X`.
- Also parse `OBS` for `Perfil antigo:` to suppress old-profile alerts after planned migrations.
- Separate counts into `segurador com X`, `perfil antigo em OBS`, and `normal/sem marcação`.
- Do not claim the sheet was updated if only Drive export was available. Sheets API may return `403 PERMISSION_DENIED` if the API is disabled, even while Drive export works.

## Reporting shape

Always state:

```text
DTR contexts before SB filter
Ignored by On-hold
Ignored by Blocked
SB-unmatched rows
Operational contexts after filter
No latest Completed/report after filter
Errors after filter
#2022 pure / mixed
```

Then provide:

- exact error strings;
- three manual-check pages per requested category with `USER`, `SEGURADOR`, `PAGE`, `PAGE_ID`;
- last-five consistency for `#10` and `#551`;
- migration sheet cross-check counts for `PERMISSION` and `APP_DELETED`.


## Update 2026-07-02 — #2022 rule correction

Rodolfo/Ciro corrected the temporary restriction workflow: for current/pure `#2022`, keep/set `STATUS=Broadcast` and set `RESTRICTED_UNTIL` to the same date shown in the DigitalTRChat warning, not D+1. Ciro/SB handles expiry automatically. For operational counts, do not trust Broadcast Template `PAGES`; use `Accounts > Messenger > Page` filtered to `STATUS=Broadcast`, and consider active `RESTRICTED_UNTIL` when judging send availability.
