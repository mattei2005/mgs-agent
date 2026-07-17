# Hermes controlled update and auxiliary-memory repair lessons — 2026-06-21

Use this reference when Rodolfo asks to update Hermes/MGS, repair a Hermes-integrated subsystem, or confirm whether an integration is actually operational.

## User expectation signal

Rodolfo explicitly rejected vague completion language like “acabou operacionalmente”. For this class of task, final reports must be complete enough for CEO-level audit, not just status green.

Minimum final report sections:

1. Version/commit before and after, including ahead/behind.
2. Backups created, with paths and approximate sizes.
3. Crons reviewed: root crontab count, Hermes cron jobs, stale monitor status, key monitor logs.
4. Services/gateways: active state, PID/start time, restart order, finalizer log path.
5. Auth/provider sanity: model/provider for each agent, token presence/length only — never values.
6. Tests/validation: py_compile, targeted pytest/smoke checks, guard checks, health checks.
7. Infra reporting: REPORT-INFRA sent/acknowledged and inventory updated when scripts/config/data/skills changed.
8. Git hygiene: scoped commit/push status, remaining dirty state explicitly separated from the task.
9. Rollback assets and exact rollback feasibility.
10. Non-critical pendências clearly labeled.

## “Confirm in the system” means live validation

If Rodolfo asks to “confirmar no sistema”, do not infer from screenshots, emails, or stale context. Check runtime/canonical sources directly: config files, scripts, logs, service state, crons, wrapper health checks, Git, and audit/inventory files.

## Honcho repair pattern discovered

Observed failure:

- `mgs-memory-copilot` returned `BadRequestError`.
- Direct SDK probe showed: `Tenant is in cold storage due to inactivity. Resume it from https://app.honcho.dev.`
- After probing, the tenant resumed and health checks returned `status=ok`.

Durable fix applied:

- `experiments/honcho-spike/mgs_memory_copilot.py` classifies cold-storage errors as `status=cold_storage` with `action_required=manual_resume_app_honcho_dev`.
- agente legado was added to `AGENT_PROFILES` with `mgs-creative` target/session.
- Atena/agente legado SOUL coverage was completed so config, SOUL rule, and wrapper support align.

Coverage validation checklist:

```bash
python3 -m py_compile /root/mgs-agent/experiments/honcho-spike/mgs_memory_copilot.py
for agent in zeus atena ares legacy-agent; do
  /root/mgs-agent/scripts/mgs-memory-copilot \
    --agent "$agent" \
    --json \
    --question "health check" \
    --context "sanitized operational check, no secrets"
done
```

Acceptable final status:

```text
zeus  ok  none  mgs-memory-copilot-zeus
atena ok  none  mgs-memory-copilot-atena
ares  ok  none  mgs-memory-copilot-ares
legacy-agent  ok  none  mgs-memory-copilot-legacy-agent
```

## Honcho health monitor false-positive pattern

After adding a cron monitor for Honcho, a false alert appeared with all agents reporting `command_failed / investigate_wrapper / n/a` and wrapper exit `rc=127`. Honcho itself was healthy; the cron environment could not find `uv` because the wrapper depended on `/root/.local/bin`, which was present interactively but absent from cron's PATH.

Durable fix pattern:

1. Make the wrapper cron-safe, not only the monitor:

```bash
export PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
```

2. Validate wrapper and monitor in a cron-like empty environment:

```bash
env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  MGS_MEMORY_COPILOT_TIMEOUT_SECONDS=45 \
  /root/mgs-agent/scripts/mgs-memory-copilot --agent zeus --json --question 'health' --context 'sanitized'

env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  DRY_RUN=1 /root/mgs-agent/scripts/monitor-honcho-health.sh
```

3. If the monitor sends a false alert and then recovers, post a resolution with the real cause, reset alert state (`last_alert_sent=null`) on recovery, and validate a real run ends `status=ok failures=0`.

4. Bash monitor pitfall: do not pipe command output into `python3 - <<'PY'` while expecting Python to read stdin; the here-doc is stdin. Use a temp file or argv for the captured output.

See also `log-monitor-discord-alert` → `references/cron-wrapper-path-and-stdin-pitfalls.md`.

## REPORT-INFRA workaround

If the stored Alerts Infra webhook returns HTTP 403, send REPORT-INFRA through the Zeus bot token via Discord API and then post the canonical ack. Do not expose the bot token or webhook URL. Record inventory update and commit only scoped files.
