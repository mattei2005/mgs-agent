# Meta app roles sheet sync auth and alerting — 2026-07-02

## Context

The `meta-app-roles-watch` Hermes cron reconciles Meta app roles against the migration sheet and writes `X` into `Removidos acumulado`. Rodolfo challenged whether the cron was actually reading/writing the sheet and required reauthentication plus alerting if sheet sync breaks.

## Durable lesson

A cron can return `OK` for the Meta role checks while the sheet sync silently fails if the script catches the exception and only stores it in state. Sheet sync failure is operationally critical because the migration sheet is the intent/feedback layer for Ially and Rodolfo.

## Current production auth model

The cron uses only `mgsagent@mgs-core-prod.iam.gserviceaccount.com` through `Google Service Account - MGS Agent`. Personal OAuth fallback and its local token files were retired on 2026-07-17. The service account has Sheets API access and `roles/serviceusage.serviceUsageConsumer`, validated by quota-attributed readback.

## Historical OAuth path — superseded

The procedure below records the former incident response for audit only. Do not recreate the retired OAuth item, helper scripts or local token files.

## Reauth flow

Generate the Desktop OAuth URL:

```bash
python3 /root/mgs-agent/scripts/ares-google-drive-oauth-desktop-init.py
```

Rodolfo opens the link, approves access, and pastes either the final localhost URL or the `code` query param. Exchange it with:

```bash
python3 /root/mgs-agent/scripts/ares-google-drive-oauth-desktop-init.py --code '<localhost URL or code>'
```

The script updates the root-only client token file used by the cron. Never print refresh tokens, access tokens, client secrets, or the raw credential file.

## Validation after reauth

Validate both token refresh and the real target cron/script path:

```text
1. Refresh-token exchange returns an access token.
2. `bash /root/.hermes/profiles/zeus/scripts/meta-app-roles-watch.sh` exits 0.
3. `/root/mgs-agent/data/meta-app-role-monitor-state.json` shows:
   - `_last_run_summary.errors_count = 0`
   - `_sheet_removed_sync.enabled = true`
   - `_sheet_removed_sync.error` absent
   - rows/marked counts populated
```

Do not rely on a separate service-account test to judge this cron; test the same OAuth mode/file the cron uses.

## Alert requirement

If sheet read/write fails, the monitor must send a critical Discord alert with Rodolfo mention and include sanitized context:

```text
Meta App Roles — falha sync planilha
Estado: CRÍTICO
Planilha: <spreadsheet id>
Sheet/GID: <gid>
Auth mode: oauth/service_account
Erro: <sanitized error>
Ação: verificar OAuth/Service Account, Sheets API, sheet sharing/permissão
```

Current production rule after the 2026-07-09 timeout alert correction:

- Google/Sheets HTTP calls use retry/backoff before classifying failure.
- A single transient `<urlopen error timed out>` is not enough to page Rodolfo; alert only after 2 consecutive failed cycles, then cooldown applies.
- The consecutive counter is persisted in `/root/mgs-agent/data/meta-app-role-monitor-state.json` as `_sheet_removed_sync_consecutive_errors` and resets to `0` after a successful sync.
- Sheet sync failure is monitor infrastructure, not a B007/app-specific manager alert. Route it to `#alerts-infra`/infra channel via bot API, not to the app-rate-limit webhook fallback.

Use cooldown to avoid spam, but do not leave persistent failure only in state/logs.
