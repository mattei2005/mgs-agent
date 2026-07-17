# Google Sheets occurrence-level comparisons

Use this pattern when Rodolfo asks to compare registrations, submissions, sends, transactions, or other repeated events.

## Unit of analysis

- Treat each source occurrence as one row. A repeated name, phone, email, or lead ID is not a duplicate unless the user explicitly defines it that way.
- Preserve the original displayed name/number in output. Normalize only an internal matching key.
- Whether repeated recipients should be contacted is an MGS business decision; the analysis must not suppress rows based on presumed resend policy.

## One-to-one multiset comparison

1. Read every source event in deterministic chronological order.
2. Normalize the matching key conservatively (for Brazilian phones: punctuation removal; strip `55` only from 12/13-digit values).
3. Build a queue of destination events per normalized key.
4. For each source event, consume at most one destination event from that key's queue.
5. Every unconsumed source event becomes one difference row. Do not collapse repeated difference rows.
6. Report destination-only events separately. The count of source-only occurrences can exceed the simple net row gap when destination-only events exist.

Example accounting:

```text
source rows = matched + source-only
destination rows = matched + destination-only
net gap = source rows - destination rows
source-only may be greater than net gap
```

## Sheet writing safety

- Use `valueInputOption=RAW` or explicit `stringValue` so names beginning with formula characters are not executed.
- Store phone columns as text and keep the source representation in the visible cell.
- Create only the tabs and columns requested; keep diagnostics local or in audit metadata.
- Validate by full API readback: tab names, row counts, repeated-occurrence counts, frozen/filter properties, and deterministic hashes.
- Remove temporary files containing names/phones after readback.

### Safely enriching an existing occurrence Sheet

When adding a derived column such as entry time to a previously validated comparison:

1. Revalidate the **exact spreadsheet**, not only the Shared Drive root. After an identity cutover, a standalone file may still need to be shared directly with the canonical Service Account even when the account can access the Shared Drive.
2. Read every existing source tab and require exact header, row-count, and A:B (or original-column) equality with the reconstructed occurrence dataset. Abort if operators changed the sheet or ordering drifted.
3. Create a mode-0600 pre-write backup containing the original values and relevant sheet/filter/grid metadata.
4. Recreate the original deterministic occurrence order and multiset matching before deriving values for the new column. Difference rows must retain the timestamp of their original unmatched source occurrence.
5. Expand only the required grid dimension and write only the new column. Preserve the original columns byte-for-byte; update header formatting, column width, borders, and filter range to include the new column.
6. Keep source-event semantics explicit. “Lead entered” may differ from “message sent”; use the entry timestamp belonging to each source rather than one convenient timestamp for every tab.
7. Perform a second, independent full readback of all columns. Verify exact hashes, row cardinality, new-value format, frozen rows, filters, and column counts.
8. On failure after mutation, clear the new column and restore the previous grid/filter shape. Remove temporary PII after success; retain only the protected backup required for rollback/audit.

## Enterprise Service Account gate

When the enterprise Service Account already has Drive `canEdit/canModifyContent` but Sheets returns `SERVICE_DISABLED`:

1. Keep the enterprise Service Account architecture; do not redirect to a personal OAuth account as the default workaround.
2. Enable `sheets.googleapis.com` in the Service Account's consumer project.
3. If the Service Account lacks `serviceusage.services.enable`, give the administrator the exact Cloud Console activation URL.
4. Poll until Sheets metadata returns HTTP 200, then write and read back through the Service Account.
5. Treat Drive permission and Sheets API activation as separate gates.
