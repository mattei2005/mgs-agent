# SB Messenger Page MESSAGE ID reset — 2026-07-02

## Context

Rodolfo changed most `MESSAGE ID` values in `Accounts > Messenger > Page` to `-1` and asked Zeus to count and then reset the remaining rows.

Live scope used:

```text
Endpoint: GET /campaigns/Messenger
Companies/publishers: all active publishers under Digital trust + Digital trust 2
Rows observed: 3,237
Field in API: BROADCAST_MESSAGE_ID
UI column: MESSAGE ID
Do not confuse with: BROADCAST_CURRENT_MESSAGE_ID / Current Message ID
```

Initial live count:

```text
BROADCAST_MESSAGE_ID = -1      3,009
BROADCAST_MESSAGE_ID != -1       228
```

After reset:

```text
BROADCAST_MESSAGE_ID = -1      3,237
BROADCAST_MESSAGE_ID != -1         0
```

## Safe reset workflow

1. Use the normal headed/Xvfb SB route from this skill.
2. Fetch `/company`, enumerate all active publishers under `digital-trust` and `digital-trust-2`.
3. Fetch `/campaigns/Messenger?companies[]=<publisher>...&source=Messenger`.
4. Backup all rows where `str(BROADCAST_MESSAGE_ID).strip() != '-1'` before writing.
5. Reset with:

```json
{
  "BROADCAST_MESSAGE_ID": "-1",
  "ids": ["<SB row ID>"]
}
```

or grouped/chunked payloads.

6. Re-fetch the full table and validate exact final count.

## Critical pitfall — restricted rows can 500 without companion fields

`PUT /campaigns/Messenger/update-many` can return HTTP 500 if restricted rows are updated with only:

```json
{"BROADCAST_MESSAGE_ID":"-1", "ids":[...]}
```

This was reproducible on rows with `RESTRICTED_UNTIL` set. The reliable pattern is to preserve stable fields in the same payload, especially:

```json
{
  "BROADCAST_MESSAGE_ID": "-1",
  "STATUS": "Broadcast",
  "RESTRICTED_UNTIL": "YYYY-MM-DD",
  "ids": ["..."]
}
```

Operational pattern:

- canary one row first;
- if bulk/chunk 500s, fall back to chunks grouped by `(STATUS, RESTRICTED_UNTIL)`;
- include `STATUS` and `RESTRICTED_UNTIL` for those groups;
- validate by readback, not by HTTP 200 alone.

## Observed final validation

```text
Rows read                      3,237
MESSAGE ID = -1                3,237
MESSAGE ID != -1                   0
Rows with Restricted Until       209
Restricted rows status          209 Broadcast
```

Backups were stored under:

```text
/root/mgs-agent/backups/sb-message-id-reset/
```

## Why this matters

For scheduling/rollout work, `MESSAGE ID` is the API field `BROADCAST_MESSAGE_ID`. `Current Message ID` is a different field (`BROADCAST_CURRENT_MESSAGE_ID`) and should not be reset when Rodolfo asks about the UI column named `MESSAGE ID`.
