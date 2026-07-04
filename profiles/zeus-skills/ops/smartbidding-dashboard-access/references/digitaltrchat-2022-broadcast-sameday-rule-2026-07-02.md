# DigitalTRChat #2022 → Smart Bidding Broadcast same-day rule — 2026-07-02

## Trigger

Use when Rodolfo asks to remediate current/pure DigitalTRChat `#2022 temporarily restricted until DATE` errors in Smart Bidding Messenger Pages.

## Final rule from Rodolfo/Ciro

For temporary Messenger send restriction `#2022`:

- keep/set SB Messenger Page `STATUS = Broadcast`;
- set `RESTRICTED_UNTIL` to the **same calendar date** shown in the DigitalTRChat warning;
- do **not** add one day;
- do **not** set `Blocked` for temporary `#2022` by default;
- do **not** schedule manual clear/reactivation: Ciro/SB handles expiry automatically.

## Counting rule

Do not use Broadcast Template `PAGES` as the clean operational count after this change. Pages with `STATUS=Broadcast` and active `RESTRICTED_UNTIL` can inflate/alter template-level interpretation.

For operational page counts, use:

```text
Accounts > Messenger > Page
filter/status = Broadcast
```

Then explicitly account for rows with active `RESTRICTED_UNTIL` when judging immediate send availability.

## Safe execution pattern

1. Re-query live SB `/campaigns/Messenger` for full scope (`Digital trust` + `Digital trust 2`, all active publishers; expected ~3,237 rows at time of correction).
2. Identify only rows previously touched for temporary restriction or current/pure `#2022` candidates.
3. Backup full rows before write.
4. Group updates by target `RESTRICTED_UNTIL` date.
5. `PUT /campaigns/Messenger/update-many` with:

```json
{"STATUS":"Broadcast", "RESTRICTED_UNTIL":"YYYY-MM-DD", "ids":["..."]}
```

6. Re-read live `/campaigns/Messenger` and validate every target row:
   - `STATUS == Broadcast`;
   - `RESTRICTED_UNTIL == same DATE`;
   - no target remains `Blocked` with `RESTRICTED_UNTIL`.

## Validated session outcome

On 2026-07-02, after earlier D+1/Blocked behavior, 209 rows were corrected:

```text
Before: STATUS=Blocked + RESTRICTED_UNTIL=D+1
After:  STATUS=Broadcast + RESTRICTED_UNTIL=D
Rows updated: 209
Validation failures: 0
Final restricted rows: 209 Broadcast, 0 Blocked
```

Backup/validation artifacts were stored under:

```text
/root/mgs-agent/backups/sb-2022-rule-change/
```
