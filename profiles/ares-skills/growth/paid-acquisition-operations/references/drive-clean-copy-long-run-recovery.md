# Drive clean-copy long-run recovery — Service Account

Use when an Ares Shared Drive clean-copy queue runs for hundreds of Canva exports and needs resumable execution and post-run reconciliation.

## Canonical recovery behavior

1. Drive access tokens minted from the Service Account are short-lived. If a long queue receives HTTP 401, mint a fresh Service Account token through the shared helper and retry the same queue item once.
2. Never switch identity, create a local credential file or request browser consent.
3. Keep the queue resume-safe: persist source Drive ID, destination ID, checksum, final filename and terminal status.
4. Retry only bounded transient errors (`401` after remint, `429`, `5xx`) with backoff; classify permission/capability failures as terminal.
5. Re-read every successful destination and reconcile report rows before declaring completion.
6. The destination must have a `driveId` and write capabilities in `MGS-AGENTS`.

Use `ARES_DRIVE_AUTH_MODE=service_account` and the `Google Service Account - MGS Agent` 1Password item. Every other auth selector fails closed.
