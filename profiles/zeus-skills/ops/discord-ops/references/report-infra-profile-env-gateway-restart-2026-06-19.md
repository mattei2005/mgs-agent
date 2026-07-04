# REPORT-INFRA — profile `.env` config + gateway restart (Ares logs-aquisicao threads)

Session pattern validated on 2026-06-19/20 while processing Ares config for conversation inside `#logs-aquisicao` threads.

## When this applies

Use this when a `[REPORT-INFRA]` reports a profile-local config change such as:

- `/root/.hermes/profiles/<agent>/.env`
- a `.env.backup-*` file
- a detached restart/finalizer unit, e.g. `mgs-gateway-restart-...`
- a gateway service restart needed to load Discord routing variables

Typical fields:

```text
Tipo: config / gateway-restart
Path: /root/.hermes/profiles/ares/.env; backup ...
Evidência: DISCORD_ALLOWED_CHANNELS includes <channel_id>; ...; restart unit/log ...
```

## Validation steps

1. Validate the current `.env` and backup exist, but never print secret values.
2. Parse and display/store only allowlisted non-secret keys relevant to the report. For the Ares logs-aquisicao case:
   - `DISCORD_ALLOWED_CHANNELS`
   - `DISCORD_FREE_RESPONSE_CHANNELS`
   - `DISCORD_THREAD_REQUIRE_MENTION`
3. Confirm the new channel/thread value exists in current `.env` and differs from the backup as reported.
4. Validate the restart finalizer log exists and contains clean start/done/service markers.
5. Validate the actual gateway service, not just the finalizer:
   - `systemctl is-active <agent>-gateway.service`
   - `systemctl show <agent>-gateway.service -p ActiveState -p SubState -p ExecMainPID`
   - minimal `journalctl -u <agent>-gateway.service -n 20` grep for stop/start/Connected markers when useful.

## Inventory pattern

Do **not** commit `.env`, backup `.env`, or restart logs.

Register only metadata in `data/infra-inventory.json`:

- `config_files[]` entry:
  - `path`, `backup_path`, `agent`, `profile`, `type`
  - `size_bytes`, `modified_at`, `sha256`, `backup_sha256`
  - `secret_values_stored: false`
  - `tracked_keys` and `previous_tracked_keys` limited to non-secret allowlisted keys
  - `purpose`, `last_report`
- `runtime_artifacts[]` entry for the restart finalizer:
  - `id`/`unit`
  - `log_path`, `log_sha256`, `log_size_bytes`, `completed_at`
  - `target_service`
  - `service_state` with `is_active`, `ActiveState`, `SubState`, `ExecMainPID`

Append a compact `report_infra_processed` event to `logs/events-audit.jsonl`; this is local-only and normally not staged.

## Commit scope

Stage only:

```bash
git add data/infra-inventory.json
```

Do not stage:

- `/root/.hermes/profiles/<agent>/.env`
- `.env.backup-*`
- restart finalizer logs
- systemd transient unit files

## Pitfalls

- `systemctl is-active hermes-ares.service` or `ares.service` may be inactive even when the real service is `ares-gateway.service`; validate the actual service name from the report/log.
- Hashing `.env` is okay; printing its full content is not. Store hashes and selected non-secret config keys only.
- If the inventory needs a new section such as `config_files[]`, add it surgically without reordering or regenerating the whole JSON file.