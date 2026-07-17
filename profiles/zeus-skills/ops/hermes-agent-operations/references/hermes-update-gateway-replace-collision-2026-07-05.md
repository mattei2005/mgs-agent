# Hermes update pitfall — gateway `--replace` collision after no-restart update (2026-07-05)

## Context

During a controlled Hermes update on MGS, the wrapper was invoked with `RESTART_GATEWAYS=0`, but the underlying `hermes update` still attempted to drain/restart manual gateways for Atena/Ares/agente legado. It launched replacement gateway processes like:

```text
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile ares gateway run --replace
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile atena gateway run --replace
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile legacy-agent gateway run --replace
```

Those replacement processes survived as PPID 1 and held the profile gateway locks/PIDs. Systemd then repeatedly tried to start the services, but each attempt exited with:

```text
Gateway already running (PID <orphan>)
Use 'hermes gateway restart' to replace it,
or 'hermes gateway stop' to kill it first.
Or use 'hermes gateway run --replace' to auto-replace.
```

Result: `atena-gateway.service`, `ares-gateway.service`, and `legacy-agent-gateway.service` were stuck in `activating (auto-restart)` even though the repo update itself succeeded.

## Durable lesson

After any Hermes update that touches gateways, validate for **two layers**:

1. `systemctl show <agent>-gateway.service -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus`
2. orphan replacement processes:

```bash
ps -ef | grep -E 'hermes_cli\.main --profile (atena|ares|legacy-agent|zeus) gateway run --replace' | grep -v grep
```

If systemd says `Gateway already running`, do not keep restarting the service in foreground. That loops and adds noise. Repair externally/detached.

## Safe repair pattern

For affected non-Zeus agents only:

1. Schedule a detached finalizer via `systemd-run --no-block` or use `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh` if it fits the case.
2. In the finalizer:
   - `systemctl stop <agent>-gateway.service` for affected services.
   - Identify only the orphan `hermes_cli.main --profile <agent> gateway run --replace` PIDs.
   - `kill -TERM` them, wait briefly, then `kill -KILL` only if still alive.
   - `systemctl reset-failed <agent>-gateway.service`.
   - Start affected services in normal order.
   - Validate `ActiveState=active`, `SubState=running`, `ExecMainStatus=0`.
3. Leave Zeus untouched unless explicitly planned; Zeus restart belongs last and should use the safe gateway restart contract.

Example minimal finalizer body:

```bash
for svc in atena-gateway.service ares-gateway.service legacy-agent-gateway.service; do
  systemctl stop "$svc" || true
done
sleep 3
for profile in atena ares legacy-agent; do
  pgrep -f "hermes_cli.main --profile ${profile} gateway run --replace" | xargs -r kill -TERM
 done
sleep 8
for profile in atena ares legacy-agent; do
  pgrep -f "hermes_cli.main --profile ${profile} gateway run --replace" | xargs -r kill -KILL
 done
systemctl reset-failed atena-gateway.service ares-gateway.service legacy-agent-gateway.service || true
systemctl start ares-gateway.service legacy-agent-gateway.service atena-gateway.service
sleep 10
systemctl show atena-gateway.service ares-gateway.service legacy-agent-gateway.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
```

## Reporting nuance

Do not call the update complete just because `hermes --version` says `Up to date` and patch guard passes. The final report must include gateway service state after collision repair. If Zeus was not restarted, say explicitly that Zeus is active but still on the previous PID and needs a separate safe restart to run the new code in-process.

## Related evidence shape

Good final evidence:

```text
Hermes repo/CLI: HEAD == origin/main, behind 0, Up to date
Patch guard: OK
py_compile: OK
Gateway tests: passed
Zeus: active/running, PID unchanged if not restarted
Atena/Ares/agente legado: active/running, new PIDs after repair
Backup: path + size
Disk: df -h /
Known pending: Zeus safe restart / Git push drift if any
```
