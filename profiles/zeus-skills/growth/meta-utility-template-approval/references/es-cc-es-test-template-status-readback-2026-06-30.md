# ES-CC-ES test-template status readback pattern — 2026-06-30

Use when Rodolfo says a dashboard approval test is ready and asks to update the country/language Sheet tab with `STATUS`.

## Trigger example

`baixa o template na dash "teste-5-es-cc-es-all-201-zero-width-2chars-approval" atualize a aba no sheet es-cc-es com a coluna status`

## Workflow

1. Treat the named SB/Dash template as the source of truth. Do not infer results from a prior CSV or another template.
2. Use headed Playwright under Xvfb with the existing SB storage state; navigate to `Accounts` → Messenger → `Broadcast Template` so the app emits the authenticated `/broadcast/Messenger` response.
3. Capture the full `/broadcast/Messenger` JSON from the browser response, then find the template by exact `NAME`.
4. Parse the template `MESSAGES` JSON and sort by `MESSAGE_ID`.
5. Derive `STATUS` per row from counters:
   - `INVALID_FORMAT > 0` → `INVALID_FORMAT`
   - `REJECTED > 0` → `REJECTED`
   - `ERROR > 0` → `ERROR`
   - `APPROVED > 0` → `APPROVED`
   - all counters zero/missing → blank/pending
6. Update the exact Sheet tab (`ES-CC-ES`, `US-CC-ES`, etc.) by adding/updating a `STATUS` column while preserving message rows and all operational columns.
7. Create/update a small summary tab for the exact approval template and counts.
8. Read the Sheet back and verify row count and status counts before reporting.

## Pitfalls

- Blank status is not failure by itself; it means the row has no approval/rejection/invalid/error counter yet in the Dash payload.
- Do not consolidate by text/CTA across templates. Rodolfo asked for the exact named template’s raw results.
- Do not use stale local `sb-broadcast-messenger-raw-latest.json` unless it already contains the exact template; if missing, refresh by capturing the live browser response.
- Keep zero-width stripping only for human-readable audit/CSV previews. Do not rewrite Sheet text unless Rodolfo asked for content changes.

## Useful artifacts from the validated run

- Work dir pattern: `/root/mgs-agent/work/meta-utility/<combo>-translation-YYYYMMDD/`
- Audit file pattern: `<combo>-testN-status-sheet-update-audit.json`
- Raw capture pattern: `<combo>-testN-broadcast-raw.json`
- Status CSV pattern: `<combo>-testN-status-from-dash.csv`

Validated example: `teste-5-es-cc-es-all-201-zero-width-2chars-approval` updated `ES-CC-ES` with 201 rows and `STATUS` readback counts from Dash.