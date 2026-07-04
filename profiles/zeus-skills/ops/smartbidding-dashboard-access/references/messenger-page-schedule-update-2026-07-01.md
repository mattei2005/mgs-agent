# SB Messenger Page schedule reduction — 2026-07-01

## Context

Rodolfo taught the operational flow for reducing Messenger Page broadcast schedules in Smart Bidding. The schedule is stored on the Page record (`BROADCAST_TIME`), not only on the Broadcast Template inventory.

Correct UI path:

```text
Accounts → Messenger → Page
→ select all Digital trust + Digital trust 2 child sites
→ click the blue refresh/update button
→ filter by TEMPLATE NAME and/or BROADCAST_TIME
→ select rows or edit selecteds
→ Broadcast tab
→ Scheduled Times
→ Save
```

## Critical selection lesson

The first extraction was wrong because only `Digital trust` child sites were effectively applied. It returned:

```text
45 sites / 2,443 pages / 46 templates / 7 schedule patterns
```

Correct runtime scope requires selecting all children under both groups and clicking refresh:

```text
Digital trust:   45 child sites
Digital trust 2: 11 child sites
Total:           56 sites
Pages:           3,237
Templates:       53
Schedule grids:  9
```

Do not trust stale table/API data after changing site selection. Verify the UI says `56 sites` and the paginator says `Showing 1 to 50 of 3237` before summarizing or updating.

## API route observed

The Page table uses:

```text
GET /campaigns/Messenger?companies[]=...&source=Messenger
PUT /campaigns/Messenger/update-many
GET /campaigns/Messenger/{id}
```

The SPA JS showed the bulk route:

```js
PUT /campaigns/${source}/update-many { ...payload, ids }
```

For schedule updates, the payload that worked was:

```json
{
  "BROADCAST_TIME": ["07:00", "09:00", "11:00", "13:00", "15:00", "18:00", "20:00", "23:00"],
  "ids": ["<page-row-id-1>", "<page-row-id-2>"]
}
```

The response can return `BROADCAST_TIME` as a newline-delimited string; validation GET returns it as an array. Do not treat this response shape difference as failure if the follow-up GET/Table confirms the array.

## Safe update pattern

1. Load SB with headed Playwright/Xvfb and valid storage state.
2. Navigate to `Accounts → Messenger → Page`.
3. Select all Digital trust and Digital trust 2 child sites, then click refresh.
4. Capture/confirm current `/campaigns/Messenger` response has 3,237 rows.
5. Filter target rows by exact `BROADCAST_TEMPLATE_NAME`.
6. Backup full target row JSON before any write.
7. Assert target row count and current schedule pattern match expectation.
8. Use captured SPA headers/auth internally; never print secrets.
9. `PUT /campaigns/Messenger/update-many` with only intended `ids` and `BROADCAST_TIME`.
10. Validate with `GET /campaigns/Messenger/{id}` for each id.
11. Re-read the full 56-site table and assert:
    - target rows have the new times;
    - only the intended template/rows have the new pattern;
    - row count remains 3,237.

## Session test performed

Template updated:

```text
Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas
```

Before:

```text
09:00, 11:00, 14:00, 18:00, 20:00
```

After:

```text
07:00, 09:00, 11:00, 13:00, 15:00, 18:00, 20:00, 23:00
```

Rows changed:

```text
PAGE_ID 19337 — Teresa Camacho
PAGE_ID 5439  — Leticia Anzaldo
```

Validation result:

```text
target_rows:            2
all_target_times_ok:    true
rows_with_new_pattern:  2
other templates:        0
```

## Operational preference

For future reductions to 8 sends/day, prefer testing one exact template/pfew pages first, then rolling out by schedule/country group only after Rodolfo approves the pattern.