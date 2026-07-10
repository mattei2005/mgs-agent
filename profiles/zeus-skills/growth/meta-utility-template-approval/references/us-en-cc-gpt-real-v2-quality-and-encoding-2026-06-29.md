# US EN CC GPT Real v2 — copy quality + emoji encoding lesson — 2026-06-29

## What happened

Rodolfo reviewed the `GPT Real 200` sheet and caught two issues:

1. Message IDs 1–50 had emoji and stronger concept, but IDs 51–200 did not.
2. IDs 51–200 had collapsed into one-line generic utility copy instead of the stronger headline + body style.

He also corrected the initial diagnosis that emojis should be avoided. The first canary CSV (`us-en-cc-canary-206-seed-plus-new.csv`) had imported/rendered emojis correctly, so emojis were not the root problem. The issue was encoding/import handling in the later CSV flow.

## Durable rules

For US EN CC Utility Template batches:

- Keep emoji in every message when the seed/batch style uses emoji.
- Preserve a clear message concept, not only generic `status/update/next step` wording.
- Use headline + blank line + body structure:

```text
🔔 CARD STATUS UPDATE

{{first_name}}, your card request has a new status ready.
Open the update to review the next step and keep the process active.
```

- CTA should also carry the same polished style when appropriate:

```text
📥 OPEN UPDATE
💳 REVIEW CARD
✅ CONFIRM NOW
```

- Avoid letting large generated ranges degrade after the first segment. QA must compare early/mid/late rows, not just row count.

## Encoding rule

If emojis are present and the CSV will be imported into the SB dashboard, export a UTF-8 BOM version:

```python
with open(path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLS, lineterminator="\r\n")
```

Use the BOM file for dashboard import. Keep regular UTF-8 files for local processing if useful.

Mojibake examples that indicate UTF-8 was read as Latin-1/Windows-1252:

```text
✅ -> âœ…
🚀 -> ðŸš€
📦 -> ðŸ“¦
It’s -> Itâ€™s
```

Do not respond by removing all emojis if an earlier known-good CSV proves emojis work in the same dashboard. First compare the known-good CSV encoding/import path and regenerate with UTF-8 BOM.

## QA checklist for future batches

Before delivering a CSV/Sheet batch:

- [ ] Row count matches target.
- [ ] Required columns are filled: `TEXT`, `CTA 1`, `LINK 1`.
- [ ] Exact duplicate text check passes.
- [ ] Representative rows from start, middle, and end are manually inspected.
- [ ] If emoji style is expected: 100% of generated rows have emoji in `TEXT` and/or `CTA 1`.
- [ ] If multi-line style is expected: 100% of generated rows have headline + blank line + body.
- [ ] CSV import version is UTF-8 with BOM and CRLF when emojis are present.
- [ ] Sheet readback verifies the relevant range, not only local files.

## Session artifact names

Final v2 artifacts created in this session:

```text
us-en-cc-gpt-real-v2-150-new.csv
us-en-cc-gpt-real-v2-200-total.csv
us-en-cc-gpt-real-v2-200-total-utf8-bom.csv
us-en-cc-gpt-real-v2-approval-tracker-200.csv
```

The durable learning is the QA/encoding pattern above, not the exact filenames.
