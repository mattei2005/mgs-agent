# REPORT-INFRA — runtime permissions, OAuth auth stores, and secret-backed wrappers (2026-06-17)

Session pattern captured from agente legado infra reports.

## Cases handled

1. Discord runtime permission overwrite
- agente legado was granted access to `#alerts-infra` via Discord API permission overwrite.
- No repo file changed at the time of the runtime action.
- Zeus still needed to validate and inventory the runtime state.

Validation pattern:
- Use the target bot token internally and check `GET /channels/<channel_id>` returns HTTP 200.
- Use Zeus/admin bot token internally to read the channel object and confirm a permission overwrite exists for the target bot ID.
- Never print bot tokens or headers. Report only HTTP code, channel ID/name, overwrite allow/deny values.

Inventory pattern:
- Add a manual section such as `discord_permissions` to `data/infra-inventory.json`.
- Update `scripts/infra-discovery.sh` to preserve that manual section across future regeneration; otherwise nightly discovery will erase the inventory entry.

2. OAuth reauth / auth store updates
- agente legado reauthenticated `xai-oauth`; the auth store changed outside the repo.
- Validation included `hermes -p legacy-agent auth status xai-oauth => logged in` and a real wrapper generation artifact.

Validation pattern:
- Check auth status without printing tokens.
- Validate real downstream use when possible (e.g. generated image file exists, magic bytes/format, size, sha256).
- Record auth store path, size, mtime, provider, profile, validation summary — not token values.

Inventory pattern:
- Add a manual section such as `oauth_auth_states` to `data/infra-inventory.json`.
- Update `infra-discovery.sh` to preserve `oauth_auth_states` across regeneration.

3. Secret-backed operational wrapper
- agente legado created `scripts/legacy-agent-youtube-reference-download.sh`, which expects private cookies at `/root/.hermes/profiles/legacy-agent/secrets/youtube-cookies.txt`.
- Cookies are deliberately outside git and must not be pasted in chat.

Validation pattern:
- `bash -n` the script.
- Verify executable mode.
- Verify required commands exist when relevant.
- Run the fail-closed path with cookies absent: expected non-zero exit with a safe message naming the expected file path; stdout should not leak secrets.
- Register the script in `infra-inventory.json` with sha256, size, mtime, owner, purpose, and validation notes.

## Commit discipline

- Commit only relevant versioned artifacts: `data/infra-inventory.json`, preservation changes in `scripts/infra-discovery.sh`, and any new versioned script.
- Do not include unrelated state files, generated artifacts, auth stores, cookies, finalizers, or other agents' concurrent work.
- Add compact `report_infra_processed` event to `logs/events-audit.jsonl` with validations and `inventory_updated=true`; logs are local-only and typically not committed.

## Pitfall

Running the full infra discovery during processing can produce a large unrelated diff or erase manually registered runtime state. Prefer a targeted merge for the current report, and if a manual section is introduced, patch `infra-discovery.sh` to preserve it before future regeneration.