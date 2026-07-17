# Hermes restart loop + cron drift after direct multi-agent restart (2026-06-11)

## Trigger

Use this reference when updating/restarting Hermes gateways from a live Zeus Discord session, especially when Rodolfo asks to restart Zeus/Atena/Ares/agente legado together after a Hermes update.

## What happened

After applying a small Hermes delta and attempting to restart all four gateways, the operation fell into a deep restart/resume loop. Zeus was the active agent executing the command while also being restarted. Multiple external/systemd-run attempts overlapped and repeatedly killed/restarted Zeus while Hermes tried to resume the same thread.

Evidence pattern in logs:

```text
DIRECT RESTART START repeated several times
Job for zeus-gateway.service canceled
Failed to kill unit zeus-gateway.service: Failed to send signal SIGKILL to auxiliary processes: Invalid argument
Zeus/Atena/Ares/agente legado eventually active/running
```

The system ended operational, but the experience was bad: Rodolfo had to use another assistant/terminal to recover.

## Durable lesson

Do **not** drive repeated restart attempts from inside the Zeus conversation that is being restarted. For multi-agent restarts, use one external, idempotent, locked finalizer and then stop issuing restart commands until that finalizer has completed and its log can be inspected.

Good pattern:

1. Apply update and validate before restart: `HEAD`, `behind=0`, patch guard, `py_compile`, targeted tests.
2. Write a single restart/finalizer script with `flock` or another lock, so repeated user messages/resume events cannot schedule duplicates.
3. Launch it once outside the active Zeus process (for example `systemd-run --unit=<unique> --on-active=...`).
4. The script should restart Atena/Ares/agente legado first, then Zeus last, log final statuses, and exit.
5. After Zeus resumes, inspect the finalizer log and `systemctl show` before doing anything else.
6. If Zeus is stuck in `deactivating`, use one explicit recovery/finalizer path; do not schedule a new full multi-agent restart every resume.
7. Runtime guard now required: startup auto-resume must synthesize an `Internal restart recovery checkpoint` message that explicitly says `Do not re-run` prior side-effecting requests (`restart/update/deploy`). Empty auto-resume events are unsafe because they can make the agent continue/reexecute the previous command.

## Cron drift discovered

During recovery, root crontab had one operational monitor commented out:

```text
# DESARMADO 20260611 pos-update v0.16 -> 1-56/5 * * * * flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1
```

Result: root crons dropped from 20 to 19 active entries, while `monitor-cron-stale-logs` still reported `problems=0` because it accepted the new count. Future post-restart reviews must compare against `docs/CRONS.md`, not just the live crontab count.

**Governance correction from Rodolfo:** do not automatically "fix" a commented/disabled cron. It may be intentionally disabled as part of incident recovery. Treat cron drift as a decision point: report what differs, state whether the script only alerts or mutates state, then ask Rodolfo before re-enabling or disabling. The `monitor-service-restarts` script only alerts; it does not restart services, but restoring it is still Rodolfo's decision.

## Required post-restart review checks

After any update/restart maintenance, verify all of these before reporting success:

```bash
# gateways live
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service
systemctl --failed --no-legend | grep -Ei 'zeus|atena|ares|legacy-agent|gateway|hermes|mgs' || true

# root cron parity, especially service restart monitor
crontab -l | grep -n 'monitor_service_restarts\|monitor-service-restarts'
grep -n 'monitor-service-restarts\|service_restarts' /root/mgs-agent/docs/CRONS.md

# Hermes cron watchdog
hermes -p zeus cron list

# update invariants
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
```

If Rodolfo confirms the restart monitor should be enabled, the expected root cron line is:

```cron
1-56/5 * * * * flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1
```

If it is disabled/commented, do **not** restore automatically. First report the drift and ask whether to keep it disabled or re-enable it.

## Reporting guidance

If a loop happened, say it plainly. Distinguish:

- **Incident:** repeated restart attempts / canceled jobs / manual recovery required.
- **Current state:** whether gateways are now active and failed units are clear.
- **Drift:** any config/cron/patch state changed by the recovery.
- **Action needed:** concrete restoration command or request for critical confirmation if tools block crontab writes.
