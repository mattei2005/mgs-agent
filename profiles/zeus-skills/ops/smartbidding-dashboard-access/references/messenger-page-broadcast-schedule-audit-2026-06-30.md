# Messenger Page Broadcast Schedule Audit — 2026-06-30

Use this note when auditing or planning bulk edits to Messenger Page broadcast times in Smart Bidding.

## Context

Rodolfo explained that broadcast send times are edited from:

```text
Accounts → Messenger → Page → row pencil/Edit selecteds → Broadcast tab → Scheduled Times → Save
```

Although the UI labels the selected item as `Message Template`, the `Scheduled Times` are stored on the Messenger Page record, tied to its current broadcast template, not in the Broadcast Template message bank itself.

## Validated read-only extraction path

1. Open SB through the headed/Xvfb route from the main skill.
2. Navigate to `/accounts`.
3. Select top source dropdown `Messenger`.
4. Click `Page` tab.
5. Ensure `Digital trust` and `Digital trust 2` companies/sites are selected, then refresh.
6. Capture the real SPA response:

```text
GET /campaigns/Messenger?companies[]=...&source=Messenger
```

7. Parse each row fields:

```text
COMPANY
PAGE_ID
FB_PAGE_ID
PAGE_NAME
STATUS
SOURCE
VERTICAL
COUNTRY
BROADCAST_TEMPLATE_ID
BROADCAST_TEMPLATE_NAME
BROADCAST_TEMPLATE_LANGUAGE
BROADCAST_TIME
BROADCAST_CURRENT_MESSAGE_ID
BROADCAST_MESSAGE_ID
BROADCAST_LAST_SCHEDULE
RESTRICTED_UNTIL
```

`BROADCAST_TIME` is the current schedule list shown in the Edit Messenger Page → Broadcast tab.

## Operational findings from this session

Current Zeus scope returned 2,443 page rows across `digital-trust` and `digital-trust-2`, 46 distinct `BROADCAST_TEMPLATE_NAME` values, and 7 distinct broadcast-time patterns.

Example schedule grouping pattern:

```text
Páginas  Templates  País/Vertical principal  Horários
1888     34         US / CC-JOB-CAR          03,08,09,11,12,14,16,17,19,20,21,23
363      2          US / CC                  09,11,14,18,20,23
132      5          DE / CC                  01,04,05,07,08,10,12,13,15,16,17,18
24       5          CA/ZA/AR/US / CC         09,11,14,18,20
21       4          MX / CC                  07,09,11,12,13,15,16,18,20,21,22,23
13       4          GB / CC                  02,05,06,08,09,11,13,14,16,17,18,19
2        1          US / CC                  03,05,08,12,14,17
```

When asked for templates in the 5-time CA/ZA/AR/US group, the exact templates were:

```text
4p   CA  Eggbev - US-CC-EN/EN-SR - g006-d Nicolas
2p   AR  Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas
12p  CA  Financeadx - CA-CC-EN/EN-SR - g006-d Nicolas
2p   US  Financeadx - MX-CC-ES/ES-ZW-SR - g006-d Nicolas
4p   ZA  Financeadx - ZA-CC-EN/EN-SR - g006-d Nicolas
```

Note the mismatch: `Financeadx - MX-CC-ES...` appeared on 2 pages whose `COUNTRY` was `US`. Flag mismatches like this before any write.

## Bulk edit safety contract

For schedule changes, do not edit broad production scope first.

Recommended controlled rollout:

1. Backup affected page rows before edit.
2. Choose one exact `BROADCAST_TEMPLATE_NAME`.
3. Edit only a tiny canary subset or one low-risk template.
4. Save via UI/API only after explicit approval of target times.
5. Re-read `/campaigns/Messenger` and validate:
   - affected rows have target `BROADCAST_TIME` count and values;
   - unrelated templates/pages are unchanged;
   - mismatched country/template rows were either intentionally included or excluded.

## Timezone caveat

Rodolfo said SB times are configured in Brazil timezone. Do not automatically convert or infer target times. Treat the values entered in SB as the operational source of truth, and ask/confirm the exact target hour list per country/template before changing schedules.
