# Broadcast Template vertical inventory — linked pages only (2026-07-07)

Session context: Rodolfo asked Zeus to analyze the **current SB Broadcast Templates** and report only the verticals that have linked pages.

## Correct source

Use live Smart Bidding `Accounts > Messenger > Broadcast Template` data from `/broadcast/Messenger`, not cached exports and not Messenger Page row grouping.

Mandatory scope/filter:

- Messenger source/context selected.
- Broadcast Template tab.
- Company/filter scope for MGS (`digital-trust`, which brings current `digital-trust` + `digital-trust-2` behavior in this table).
- Include only templates where Broadcast Template `PAGES > 0`.

## Why this matters

Rodolfo’s wording “templates atuais com páginas linkadas” maps to the Broadcast Template `PAGES` field. Do **not** substitute a count of Page-tab rows grouped by `BROADCAST_TEMPLATE_NAME` unless explicitly labeled as a separate Page-row analysis.

## Extraction pattern

The existing helper from `scripts/sb-utility-rollout-manager.py` can capture live rows:

```python
p, b, c, page, rows, headers, url = await rollout.capture_rows_headers()
linked = [r for r in rows if int(float(r.get('PAGES') or 0)) > 0]
```

For each linked template, parse:

- `NAME`
- `LANGUAGE`
- `PAGES`
- `MESSAGES` count via `parse_messages(row)`
- optional `APPROVAL`

## Vertical derivation

Derive the vertical from the template `NAME` using the code pattern:

```text
COUNTRY-VERTICAL-LANGUAGE
```

Examples:

- `Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas` → `AR-CC-ES`
- `Newsoun - US-CC-EN/EN-SR - g005-d Kelly` → `US-CC-EN`
- `Fincgriffin - US-CAR-EN/EN - JBF - g001-d` → `US-CAR-EN`

Regex pattern used successfully:

```text
\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b
```

If the pattern is absent, report the row as `INDEFINIDO` with domain/language context instead of guessing.

## Recommended report shape

Summarize by vertical:

```text
Vertical     Templates   Páginas linkadas   Mensagens
US-CC-EN     11          543                10/20
US-CC-ES     11          244                10/20
DE-CC-DE     4           68                 20
```

Then add a short operational read:

- high priority by linked page volume;
- medium priority;
- low-volume/simple canaries.

Keep the final answer concise; do not dump every template unless Rodolfo asks for detail.

## Last observed live result from this session

Live capture returned 101 Broadcast Template rows, 45 with `PAGES > 0`, across 11 verticals:

```text
AR-CC-ES, CA-CC-EN, DE-CC-DE, ES-CC-ES, GB-CC-EN,
MX-CC-ES, US-CAR-EN, US-CC-EN, US-CC-ES, US-JOB-ES, ZA-CC-EN
```

Treat these counts as historical evidence only. Re-query live SB for future reports.
