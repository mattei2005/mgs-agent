# Honcho usage and billing check — 2026-07-01

Use this note when Rodolfo asks how much Honcho/Roncho is spending per day or whether to preserve remaining managed Honcho credits.

## What was validated

- The MGS Honcho API key is stored in 1Password item `Honcho API - MGS` / field `api key`; do not print it.
- The active MGS wrapper is `/root/mgs-agent/scripts/mgs-memory-copilot`, which pulls the key from 1Password, sets `HONCHO_WORKSPACE=mgs-agents`, and runs `/root/mgs-agent/experiments/honcho-spike/mgs_memory_copilot.py`.
- The health monitor is `/root/mgs-agent/scripts/monitor-honcho-health.sh` and state is `/root/mgs-agent/data/honcho-health-state.json`.
- The root crontab ran the monitor every 15 minutes:
  `*/15 * * * * flock -n /var/lock/monitor_honcho_health.lock /root/mgs-agent/scripts/monitor-honcho-health.sh >> /root/mgs-agent/logs/monitor-honcho-health.log 2>&1`
- Each monitor run checks 4 agents: Zeus, Atena, Ares, agente legado.
- Therefore every 15-minute schedule means roughly 96 runs/day × 4 agents = ~384 Honcho copilot calls/day, before any manual/on-demand usage.
- The public Honcho OpenAPI at `https://api.honcho.dev/openapi.json` did not expose billing/usage/credits endpoints in this check. Tested obvious endpoints such as `/v3/usage`, `/v3/billing`, `/v3/credits`, `/v3/account`, `/v3/user`, `/v3/organization`; they returned 404. Do not claim exact daily dollar spend from the API unless a future endpoint/dashboard is available.

## How to answer Rodolfo

Give two layers:

1. **Confirmed operational usage** from local logs/crons: monitor frequency, calls/day, failures.
2. **Estimated dollar burn** only if Rodolfo provides current remaining credit or start/end balance. Label it as an estimate.

Useful calculation pattern:

- If credit went from $100 to $60 over N days, average burn = `$40 / N days`.
- If the monitor is still every 15 minutes, baseline call volume is ~384 calls/day.
- Manual Honcho briefing/second-opinion calls add on top of that but are usually smaller unless scheduled.

## Operational recommendation

For managed Honcho used only as “segunda opinião”, a 15-minute 4-agent health monitor is too aggressive. Prefer reducing to hourly or 2–4 checks/day while benchmarking value. Keep Honcho as hypothesis/context only; validate operational claims against canonical MGS sources before reporting or acting.

## Pitfalls

- Do not infer exact cost from local logs alone; local logs count calls, not billable units/tokens/dollars.
- Do not expose the Honcho key or workspace secrets in Discord.
- Do not treat lack of public billing endpoint as “cannot know forever”; check the Honcho dashboard or docs if available, and label API limitations as current-state evidence.
- If changing the monitor schedule, that is an infra/cron modification and needs normal MGS reporting/inventory handling.
