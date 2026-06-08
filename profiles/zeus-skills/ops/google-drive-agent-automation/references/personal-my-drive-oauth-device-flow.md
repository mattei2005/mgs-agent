# Google Drive OAuth for personal My Drive — device-flow scope pitfall

Session pattern: Rodolfo needed Ares to upload cleaned creative files into `MGS-CRIATIVOS` that must remain in his personal Google Drive, not a Shared Drive.

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
3. Store `client_id`, `client_secret`, and `refresh_token` in 1Password item `Google OAuth - Ares Drive`; never print the values.
4. Validate OAuth mode safely: if the 1Password item is missing/incomplete, the script should fail before Drive writes or report CSV changes.
5. After approval, run the Drive batch with `--limit 1 --max-errors 1`; only then run the full queue.

## UX/detail

When running a long-polling device helper in the background, Hermes process output may not surface until process exit. If the user needs the code immediately, run the helper foreground with a short timeout to capture URL/code, or redirect to a temp log and read the log. Do not leave multiple polling helpers running; kill stale sessions before starting a fresh authorization code.
