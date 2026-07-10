# Post-update gateway restart validation — Zeus/Atena/Ares

Use after Rodolfo runs `hermes update` or asks to restart all MGS agents.

## Pattern

1. Validate update before restart:
   - `hermes --version`
   - `git -C /root/.hermes/hermes-agent rev-parse --short HEAD origin/main`
   - `git -C /root/.hermes/hermes-agent rev-list --count HEAD..origin/main`
   - `py_compile` critical patched files: `gateway/run.py`, `plugins/platforms/discord/adapter.py`, `gateway/platforms/base.py`, `tools/send_message_tool.py`
   - scan for MGS Discord patch markers: `_auto_create_thread`, `DISCORD_THREAD_AUTO_ADD_USERS`, `PATCH (MGS Digital Corp)`
   - provider/auth summary for `zeus`, `atena`, `ares` without printing tokens: provider, model, active_provider, access token length, refresh token present.

2. Restart gateways:
   - `systemctl restart zeus-gateway.service atena-gateway.service ares-gateway.service`
   - If invoked from Zeus itself, expect the terminal call to be interrupted or time out because the current conversation can keep the old Zeus gateway process alive while systemd is stopping it.

3. Handle Zeus self-restart safely:
   - Validate Atena/Ares first; they usually restart cleanly.
   - If Zeus is stuck in `deactivating (stop-sigterm)` and the old PID contains the active tool/session, schedule an external one-shot finalizer with `systemd-run --on-active=20s ...` to finish Zeus after the response is delivered.
   - The finalizer can `systemctl kill -s SIGKILL zeus-gateway.service || true`, wait, then `systemctl start zeus-gateway.service || true`, then validate all three services.
   - Do not rely on posting via Discord API from the finalizer unless you have confirmed the bot token is available to that process; Hermes v0.15+ may scrub/guard provider credentials in tool sandboxes. A local log file in `/tmp` is enough for the next Zeus session to inspect.

4. Final validation:
   - `systemctl is-active` and `systemctl show -p MainPID -p ActiveEnterTimestamp -p ActiveState -p SubState -p NRestarts -p Result` for all three gateways.
   - `journalctl -u <svc> --since <new ActiveEnterTimestamp>` and grep for real post-start failures only.
   - Treat `Failed with result` lines from the deliberate restart/kill of old PIDs as historical if the new PID is active and there is no post-start traceback/OOM/auth failure.

## Reporting rule

Report the distinction explicitly:

- `active` new PIDs = operational.
- restart-time `status=1/FAILURE` or `signal` on old PIDs = expected during controlled restart unless repeated after the new start.
- Zeus self-kill = expected when restarting Zeus from inside its own gateway session.

## Pitfall

Do not declare failure just because `systemctl restart ...` timed out inside Zeus. First check current service state and the new PIDs. A timeout often means the session interrupted itself, not that the gateway failed to come back.