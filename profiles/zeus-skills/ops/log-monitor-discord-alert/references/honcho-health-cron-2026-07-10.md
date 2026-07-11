# Honcho Health Cron — 2026-07-10

## Canonical schedule

Rodolfo reduced `/root/mgs-agent/scripts/monitor-honcho-health.sh` from every 15 minutes to four checks per day after the shared 1Password Service Account consumption audit.

```text
Cron: 54 8,13,18,22 * * *
Timezone: America/New_York
Runs: 08:54, 13:54, 18:54, 22:54 ET
Lock: /var/lock/monitor_honcho_health.lock
```

The `:54` offset avoids start-time collisions with the current root/Hermes cron inventory and leaves 30 minutes after B011 starts at `:24`. Meta starts at `:04`; this creates the operational stagger `:04 → :24 → :54`.

Each healthy execution checks four agents through `mgs-memory-copilot`; nominal 1Password cost is four `op item get` calls, conservatively 12 reads per execution. At four runs/day: 48 reads/day and 1,440 reads/30 days.

Do not restore the old `*/15` cadence without explicit Rodolfo authorization and a new shared 1Password request-budget check.

## Verification

After changing the schedule:

1. `crontab -l` must contain exactly one `monitor-honcho-health.sh` entry.
2. Confirm the expression is `54 8,13,18,22 * * *`.
3. Regenerate `docs/CRONS.md` and `data/infra-inventory.json`.
4. Record the change in `logs/events-audit.jsonl` and send REPORT-INFRA.
