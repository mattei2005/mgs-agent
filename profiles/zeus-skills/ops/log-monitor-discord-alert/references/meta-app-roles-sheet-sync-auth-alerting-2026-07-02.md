# Meta App Roles sheet sync auth + alerting — 2026-07-02

## Trigger

Use when maintaining the `meta-app-roles-watch` cron/Hermes job, the B001–B010 Meta App Roles alerts, or the migration sheet columns such as `Removidos acumulado`.

## Lesson

Do not silently swallow migration-sheet sync failures. If the monitor can read Meta app roles but cannot read/write the Google Sheet, Rodolfo must receive an alert; otherwise the cron appears healthy while the sheet and downstream identity mapping are stale.

## Historical auth reality — superseded 2026-07-17

This section records the former working path for audit only. The active architecture now uses `mgsagent@mgs-core-prod.iam.gserviceaccount.com` through item `Google Service Account - MGS Agent`; personal OAuth and its local token files are retired.

## Current validated state

The monitor uses only the canonical Service Account from `Google Service Account - MGS Agent`, with `MGS_META_APP_ROLES_GOOGLE_AUTH_MODE=service_account`. The project `mgs-core-prod` has Sheets API enabled and `roles/serviceusage.serviceUsageConsumer`; personal OAuth fallback is forbidden.

## Validation pattern

1. Source `/root/mgs-agent/.env` with `set -a`/`set +a`.
2. Resolve the canonical Service Account JSON through the shared Google auth helper without printing values.
3. Mint a Sheets-scoped token and attribute quota to `mgs-core-prod` with `x-goog-user-project`.
4. Call Sheets metadata:
   - `GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets(properties(sheetId,title))`
5. Validate write with a no-op idempotent range update when safe:
   - read current `Removidos acumulado` values from CSV export
   - PUT the same values back to the exact range
   - require HTTP 200 and `updatedCells` matching row count
6. Run `meta-app-roles-watch.sh` in dry-run and inspect `_sheet_removed_sync` in state.
7. Fail closed if any code path attempts personal OAuth fallback.

## Alerting requirement

If `sync_sheet_removed_accumulated(state)` raises, the script must:

- persist `_sheet_removed_sync.error` in state;
- send a critical Discord alert with Rodolfo mention;
- include spreadsheet ID, GID, auth mode, and a clipped error;
- mark a cooldown key such as `sheet_removed_sync` to prevent spam.

The failure should not remain state-only.

## Pitfalls

- `no_agent=true` cron status `ok` only means the script exited; it does not prove the sheet sync succeeded unless `_sheet_removed_sync` is inspected.
- CSV export can work while Sheets API write fails, depending on auth path and API enablement.
- Avoid printing OAuth refresh tokens, service account JSON, bot tokens, or webhook URLs while validating.
