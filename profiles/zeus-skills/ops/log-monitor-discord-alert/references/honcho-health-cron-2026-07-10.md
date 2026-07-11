# Honcho Health Cron — 2026-07-10

## Canonical schedule

Rodolfo reduced `/root/mgs-agent/scripts/monitor-honcho-health.sh` from every 15 minutes to four checks per day after the shared 1Password Service Account consumption audit.

```text
Cron: 30 8,13,18,22 * * *
Timezone: America/New_York
Runs: 08:30, 13:30, 18:30, 22:30 ET
Lock: /var/lock/monitor_honcho_health.lock
```

The 30-minute offset avoids colliding with Meta app roles at `:00` and B011 DTR link at `:15` in the same operational windows.

Each healthy execution checks four agents through `mgs-memory-copilot`; nominal 1Password cost is four `op item get` calls, conservatively 12 reads per execution. At four runs/day: 48 reads/day and 1,440 reads/30 days.

Do not restore the old `*/15` cadence without explicit Rodolfo authorization and a new shared 1Password request-budget check.

## Verification

After changing the schedule:

1. `crontab -l` must contain exactly one `monitor-honcho-health.sh` entry.
2. Confirm the expression is `30 8,13,18,22 * * *`.
3. Regenerate `docs/CRONS.md` and `data/infra-inventory.json`.
4. Record the change in `logs/events-audit.jsonl` and send REPORT-INFRA.
