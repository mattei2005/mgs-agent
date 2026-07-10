# US-CC-ES zero-width approval probe — 2026-06-30

Session lesson from Rodolfo correction during US-CC-ES Utility Template workflow.

## What happened

Rodolfo asked to create `US-CC-ES` from `US-CC-EN`, translate `TEXT` and `CTA 1`, inspect the existing SB template `Openzed - US-CC-ES/ES-ZW - AV - g003-d Isliago`, then apply zero-width characters to the messages.

Initial implementation used `U+200B` between every adjacent letter in `TEXT`. Rodolfo judged that too dense and requested a lighter pattern:

```text
2 visible letters + U+200B + 2 visible letters + U+200B + ...
```

He also corrected the approval sequence: do **not** select the best 70 before the approval probe. First export/send **all messages** for approval; only after approval results return should we filter approved messages and choose the best 70 for production template replacement.

## Durable rules

1. For `*-ZW` Spanish/zero-width approval probes, default to the lighter pattern when Rodolfo asks for reduced density:
   - strip existing zero-width first;
   - apply `U+200B` after every 2 visible alphabetic characters inside `TEXT` only;
   - preserve `{{first_name}}`, `{{last_name}}`, and bracket placeholders exactly;
   - do not insert zero-width in `CTA 1`, links, UTM params, or IDs.

2. Approval-probe CSV order of operations:
   - create/translate/update the Sheet tab first;
   - apply requested zero-width pattern;
   - export **all eligible rows** for approval, not the best 70;
   - use UTF-8 BOM + CRLF;
   - only after approval results are known: filter approved rows, rank by appeal, select 70, then replace production templates preserving their own links.

3. Reporting distinction:
   - “CSV for approval” = all rows from the test bank/sheet;
   - “production install” = selected best 70 approved rows after approval results.

## Verification checklist

- Sheet readback row count matches source row count.
- CSV row count equals all eligible Sheet rows when this is an approval probe.
- `TEXT` has zero-width; `CTA 1` has zero-width count 0.
- Placeholders remain literal, e.g. `{{first_name}}`.
- CSV starts with UTF-8 BOM and uses CRLF.
- Report clearly whether the file is for approval probe or production replacement.
