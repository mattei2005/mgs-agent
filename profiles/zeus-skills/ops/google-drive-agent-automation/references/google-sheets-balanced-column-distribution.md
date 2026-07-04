# Google Sheets balanced column distribution by group

Use when Rodolfo asks to fill a Google Sheets column with a fixed list of values distributed across many rows, especially when rows belong to operational groups such as site/bot email/gestor.

## Key lesson

Do **not** distribute values row-by-row as `1,2,3,4...` when the sheet has a grouping field. Rodolfo expects a manager/site to be able to open one mailbox and process all rows for that site together.

Correct pattern:

1. Identify the grouping column from the user's language.
   - In `Migracao 22/06`, column A `User` is the bot/site email group.
   - Rows with the same `User` must receive the same assigned mailbox in the target column.
2. Balance by whole groups, not rows.
   - Count rows per group.
   - Sort groups by descending size.
   - Greedily assign each group to the target value with the lowest current load.
   - This preserves group integrity while keeping totals roughly equal.
3. Before writing, save a backup of target cells and planned assignments to `/root/mgs-agent/reports/`.
4. Apply updates with Sheets API `values:batchUpdate` using `valueInputOption=RAW`.
5. Validate with `values:batchGet`:
   - every target row matches the planned value;
   - no group appears under more than one assigned value;
   - final counts are balanced.

## Example

If column A has:

```text
disparosamazing@gmail.com
disparosamazing@gmail.com
disparoscliquet@gmail.com
disparoscliquet@gmail.com
```

Then column N should be assigned by group, not alternating by row:

```text
disparosamazing@gmail.com  -> 1not1@matteiservicesinc.com for all amazing rows
disparoscliquet@gmail.com  -> 2not2@matteiservicesinc.com for all cliquet rows
```

## Formatting-only requests

If Rodolfo asks to set text color for one Sheets column, use `spreadsheets.batchUpdate` with `repeatCell` and only the specific format field, e.g. `fields=userEnteredFormat.textFormat.foregroundColor`, so the operation does not alter values or other formatting.

## Pitfalls

- A direct CSV export is good for row discovery, but validate writes through Sheets API readback, not by assuming the CSV refreshed immediately.
- Column letters are one-based for A1 notation but zero-based in `repeatCell` ranges; column N is `startColumnIndex=13`, `endColumnIndex=14`.
- If the user says “por segurador/site/gestor” after an initial row-wise distribution, treat it as a correction to grouping semantics and redo the distribution by the grouping column immediately.
