# Hermes restart loop + cron drift after direct multi-agent restart (2026-06-11)

## Trigger

Use this reference when updating/restarting Hermes gateways from a live Zeus Discord session, especially when Rodolfo asks to restart Zeus/Atena/Ares/Hera together after a Hermes update.

## What happened

After applying a small Hermes delta and attempting to restart all four gateways, the operation fell into a deep restart/resume loop. Zeus was the active agent executing the command while also being restarted. Multiple external/systemd-run attempts overlapped and repeatedly killed/restarted Zeus while Hermes tried to resume the same thread.

Evidence pattern in logs:

```text
DIRECT RESTART START repeated several times
Job for zeus-gateway.service canceled
Failed to kill unit zeus-gateway.service: Failed to send signal SIGKILL to auxiliary processes: Invalid argument
Zeus/Atena/Ares/Hera eventually active/running
```

The system ended operational, but the experience was bad: Rodolfo had to use another assistant/terminal to recover.

## Durable lesson

Do **not** drive repeated restart attempts from inside the Zeus conversation that is being restarted. For multi-agent restarts, use one external, idempotent, locked finalizer and then stop issuing restart commands until that finalizer has completed and its log can be inspected.

Good pattern:

1. Apply update and validate before restart: `HEAD`, `behind=0`, patch guard, `py_compile`, targeted tests.
2. Write a single restart/finalizer script with `flock` or another lock, so repeated user messages/resume events cannot schedule duplicates.
3. Launch it once outside the active Zeus process (for example `systemd-run --unit=<unique> --on-active=...`).
4. The script should restart Atena/Ares/Hera first, then Zeus last, log final statuses, and exit.
5. After Zeus resumes, inspect the finalizer log and `systemctl show` before doing anything else.
6. If Zeus is stuck in `deactivating`, use one explicit recovery/finalizer path; do not schedule a new full multi-agent restart every resume.

## Cron drift discovered

During recovery, root crontab had one operational monitor intentionally/destructively commented out:

```text
# DESARMADO 20260611 pos-update v0.16 -> 1-56/5 * * * * flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1
```

Result: root crons dropped from 20 to 19 active entries, while `monitor-cron-stale-logs` still reported `problems=0` because it accepted the new count. Future post-restart reviews must compare against `docs/CRONS.md`, not just the live crontab count.

## Required post-restart review checks

After any update/restart maintenance, verify all of these before reporting success:

```bash
# gateways live
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service
systemctl --failed --no-legend | grep -Ei 'zeus|atena|ares|hera|gateway|hermes|mgs' || true

# root cron parity, especially service restart monitor
crontab -l | grep -n 'monitor_service_restarts\|monitor-service-restarts'
grep -n 'monitor-service-restarts\|service_restarts' /root/mgs-agent/docs/CRONS.md

# Hermes cron watchdog
hermes -p zeus cron list

# update invariants
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
```

Expected root cron line:

```cron
1-56/5 * * * * flock -n /var/lock/monitor_service_restarts.lock /root/mgs-agent/scripts/monitor-service-restarts.sh >> /root/mgs-agent/logs/monitor-service-restarts.log 2>&1
```

## Reporting guidance

If a loop happened, say it plainly. Distinguish:

- **Incident:** repeated restart attempts / canceled jobs / manual recovery required.
- **Current state:** whether gateways are now active and failed units are clear.
- **Drift:** any config/cron/patch state changed by the recovery.
- **Action needed:** concrete restoration command or request for critical confirmation if tools block crontab writes.
