# Google Drive OAuth for personal My Drive — device-flow scope pitfall

Historical generic pattern for personal Drive OAuth only. MGS Creative Ops no longer uses this destination model: its canonical root is the Shared Drive `MGS-AGENTS` (`0AEwt4Ye690ocUk9PVA`), administered by `support@matteiservicesinc.com`.

## What worked / failed

```text
OAuth client type                         Scope                                      Result
----------------------------------------|--------------------------------------------|-----------------------------
TVs and Limited Input devices            https://www.googleapis.com/auth/drive       Google returned invalid_scope
TVs and Limited Input devices            https://www.googleapis.com/auth/drive.file  Device flow started successfully
Desktop app                              https://www.googleapis.com/auth/drive       Recommended fallback if full access needed
```

`drive.file` is narrower than full Drive. It may be enough for creating/uploading app-authorized files, but do not assume it can traverse or manage an existing large personal Drive folder tree. Treat it as a hypothesis and run a one-file smoke test before the full queue.

## Recommended agent behavior

1. If the user already created a device-flow OAuth client, retry it with the full Drive scope once; if Google returns `invalid_scope`, try `drive.file` only as a limited smoke-test path.
2. If the production requirement is broad access to an existing folder tree, prepare a Desktop OAuth fallback instead of repeatedly retrying device flow.
3. For a future explicitly approved exception, create a new scoped item such as `Google OAuth - Personal Drive Exception`; never reuse a retired operational credential or print values.
4. Validate OAuth mode safely: if the 1Password item is missing/incomplete, the script should fail before Drive writes or report CSV changes.
5. After approval, run the Drive batch with `--limit 1 --max-errors 1`; only then run the full queue.

## OAuth consent screen state

For one-person/internal MGS use, do **not** send the OAuth app through Google verification just to unblock Rodolfo. The reliable setup is:

```text
Publishing status       Testing
User type               External
Test users              explicitly approved Google account
Branding/verification   minimum required fields only; no verification center unless app is public
```

If Google shows `Access blocked: <app> has not completed the Google verification process` with `403 access_denied`, check Test users first. Moving to Production can make the UX worse for unverified sensitive/restricted scopes; for personal automation, Testing + explicit test user is enough.

## Token persistence pitfall

A 1Password service account may be able to **read** an OAuth credential item but fail to **edit** it after Google approval (`Couldn't update the item`). Do not discard the authorization success or expose the token in chat. Preferred handling:

1. Try to save `refresh_token` back into the configured 1Password item using a template/stdin path, not argv assignment.
2. If 1Password update is denied, stop and request a storage decision; do not recreate retired MGS local OAuth files as an automatic fallback.
3. Add `.secrets/`/`secrets/` to `.gitignore` before writing the fallback file.
4. Update runtime OAuth credential loading to read `client_id`/`client_secret` from 1Password and `refresh_token` from the local fallback file when present.
5. Report only storage location class (`1Password` or `local root-only secret file`) and token length, never the token value.

This is a durable fallback for headless VPS OAuth bootstrap where 1Password write permissions are narrower than read permissions.

## UX/detail

When running a long-polling device helper in the background, Hermes process output may not surface until process exit. If the user needs the code immediately, run the helper foreground with a short timeout to capture URL/code, or redirect to a temp log and read the log. Do not leave multiple polling helpers running; kill stale sessions before starting a fresh authorization code.

Background-process completion notices can arrive late for helpers that were intentionally killed. When multiple OAuth codes were generated, explicitly tell Rodolfo which **single current code** is active and which old codes/process IDs to ignore.
