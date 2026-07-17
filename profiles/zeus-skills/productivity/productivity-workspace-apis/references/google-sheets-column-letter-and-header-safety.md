# Google Sheets column-letter and header safety

Use this when Rodolfo asks for comparisons or writes in a Google Sheet by tab name + column letters, especially after the sheet has been converted to a table or after columns were inserted/shifted.

## Durable lesson

Column letters in the user's wording may describe what he sees in the UI, but the exported/API sheet can have shifted columns, hidden/table-generated columns, or renamed headers. Do not trust a prior read or an earlier tab layout after a write or table conversion.

Before mutating:

1. Re-read the live tab metadata/values.
2. Print/inspect the current header row for the exact target tab.
3. Map the intended business fields by header names first (`User`, `LOGIN`, `email`, `Segurador`, `name`, `PG/PAGES`), then by column letter only if headers are absent.
4. If the user corrects the matching rule, recompute from scratch using the corrected pair key; do not reuse prior single-column matches.
5. For pair matching, compare normalized tuples, e.g. `(user/email, segurador/name)`, not only the email.
6. If a write must clear a marker column, make sure you are clearing the intended marker field after current header mapping, not a shifted data column.
7. Verify by readback and include the counts: rows compared, matches, only-left, only-right, and duplicate-count differences.

## Common mapping patterns observed

- A simplified comparison tab may expose headers as `email`, `name`, `pages` instead of `User`, `Segurador`, `PG`.
- A backup tab may retain full migration-style headers: `Removidos acumulado`, `User`, `TOKEN FB`, `Segurador`, `PG`, etc.
- Google Sheets table conversion can change exports/API ranges enough that a previous assumption like `A=LOGIN, B=SEGURADOR, D=marker` becomes stale.

## Reporting pattern

For tab-vs-tab comparison, report concise operational counts:

```text
Usei:
- Aba X: email/name
- Aba Y: User/Segurador

Resultado:
- Pares na X: N
- Pares na Y: N
- Tem na X e não tem na Y: N
- Tem na Y e não tem na X: N
- Quantidade duplicada diferente: N
```

If there are differences, list rows with `user | segurador | linha(s) | qtd`.
