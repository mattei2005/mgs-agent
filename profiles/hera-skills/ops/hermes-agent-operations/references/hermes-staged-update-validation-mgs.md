# Hermes staged update validation — MGS reference

Use this reference when updating or validating Hermes Agent on the MGS VPS for Zeus/Atena/Ares. It captures the durable workflow from the June 2026 Hermes update/restart validation.

## Operating principle

Separate **update**, **validation**, and **restart**. Restarting gateways can interrupt Discord threads/sessions, so it requires explicit Rodolfo authorization unless he already performed it and asks for validation.

## Recommended sequence

1. Read-only pre-check
   - `hermes --version`
   - `git -C /root/.hermes/hermes-agent status --short`
   - `git -C /root/.hermes/hermes-agent rev-parse --short HEAD`
   - `git -C /root/.hermes/hermes-agent fetch origin main`
   - compare local HEAD vs `origin/main`

2. Backup before update
   - archive `/root/.hermes/profiles/`
   - save local Hermes diff with `git diff > /root/mgs-local-hermes-$ts.patch`
   - if profiles are live, `tar: file changed as we read it` is expected; verify the archive exists and size is plausible.

3. Run update without restart
   - Execute `hermes update` only after backups.
   - Do not restart Zeus/Atena/Ares automatically after update unless Rodolfo explicitly authorizes restart.

4. Validate local MGS patches
   - Expected modified files may include:
     - `gateway/run.py`
     - `plugins/platforms/discord/adapter.py`
     - `gateway/platforms/base.py`
     - related gateway/Discord tests
   - Check markers for:
     - `PATCH (MGS Digital Corp)`
     - `[READ-ONLY RECENT CHANNEL CONTEXT — NON-ACTIONABLE]`
     - `[New message — ACTIONABLE USER REQUEST]`
     - `DISCORD_THREAD_AUTO_ADD_USERS`
     - deterministic thread rename/auto-add logic
   - Generate local diff and validate structural compatibility against `origin/main` in a temporary worktree with `git apply --check`.

5. Compile/import smoke
   - `py_compile` critical modules:
     - `gateway/run.py`
     - `plugins/platforms/discord/adapter.py`
     - `tools/discord_tool.py`
     - `gateway/platforms/base.py`
   - Import-smoke the same modules from the Hermes repo.

6. Restart only when authorized
   - Restart services as a separate step: `zeus-gateway.service`, `atena-gateway.service`, `ares-gateway.service`.
   - After restart, validate:
     - `systemctl show` active/running, MainPID, ExecMainStartTimestamp, NRestarts
     - logs show Discord connected and gateway running
     - journal warnings after restart window
   - Lines like `Failed with result 'exit-code'` at the exact restart timestamp are not an incident if followed by new active/running PIDs and `NRestarts=0`.

7. Validate crons
   - Root crontab jobs should use `flock`.
   - Check cron docs/log monitors, especially stale-log monitor.
   - Check Hermes cron per profile; disabled jobs should be reported as disabled, not failures.

8. Run targeted tests
   - Unset Discord production env vars when running tests to avoid production-env contamination.
   - Prefer targeted groups for Discord/gateway tests. If a broad combined pytest suite fails but the same tests pass isolated, report it as likely test state/env contamination and keep the caveat explicit.

## Reporting format

Use a short executive summary with aligned tables:

- update/HEAD/upstream lag
- local patch status and compatibility
- services and PIDs/start times
- crons root/Hermes
- test results
- honest caveats

Distinguish clearly between:

- operational blocker
- non-blocking upstream lag
- cleanup recommendation
- test-isolation caveat

Never expose credentials from `.env`, systemd env, cron scripts, or logs. Redact secrets and only report safe keys/IDs/status.