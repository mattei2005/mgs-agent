# Cron stale-log false positives from divergent log paths

## Trigger

Use this when `monitor-cron-stale-logs.sh` reports a cron as STALE but the job appears healthy in another log file.

## Root pattern

A cron line may redirect stdout/stderr to one log while the script itself writes its heartbeat to a different internal `LOG=...` path:

```text
crontab redirect:  >> /root/mgs-agent/logs/script-name.log 2>&1
script internal:   LOG="/root/mgs-agent/logs/other-name.log"
```

The stale monitor parses the crontab redirect first. `CUSTOM_LOG` only helps when there is no redirect. If both exist and diverge, the monitor can watch the empty redirect file and alert even while the script is healthy.

## Correct fix

Prefer one canonical log path per cron:

1. Choose the crontab redirect path as canonical when it follows the script name.
2. Change the script's internal `LOG=...` to the same path.
3. Remove any now-unnecessary `CUSTOM_LOG` override.
4. Keep/ensure a heartbeat line on healthy no-op runs, otherwise healthy zero-work runs look stale.

## Validation sequence

```bash
bash -n /root/mgs-agent/scripts/<script>.sh
bash -n /root/mgs-agent/scripts/monitor-cron-stale-logs.sh
/root/mgs-agent/scripts/<script>.sh --dry-run   # if supported
/root/mgs-agent/scripts/monitor-cron-stale-logs.sh --dry-run | grep '<script>'
/root/mgs-agent/scripts/<script>.sh            # controlled real run if safe
stat -c '%y %s %n' /root/mgs-agent/logs/<canonical>.log
/root/mgs-agent/scripts/monitor-cron-stale-logs.sh --dry-run | grep '<script>'
```

Only after the dry-run shows `OK`, run the stale monitor for real to clear the old state and emit one green recovery embed if an alert was active.

## Reporting pattern

Report separately:

- code change applied;
- validation evidence;
- whether a recovery embed was sent due to existing stale state;
- final `data/cron-stale-logs-state.json` alert status.

## Concrete example

`cleanup-zombie-sessions.sh` had cron redirect `cleanup-zombie-sessions.log` but internal log `cleanup-zombies.log`. Standardizing on `cleanup-zombie-sessions.log` removed a false STALE alert while preserving heartbeat semantics.