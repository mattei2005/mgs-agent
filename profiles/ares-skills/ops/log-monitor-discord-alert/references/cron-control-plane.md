# Cron Control Plane — MGS cron reliability pattern

Session pattern validated 2026-05-16 for MGS root crontab operations.

## When to use

Use this pattern when MGS has multiple Linux cron jobs and Rodolfo asks for inventory, cleanup, reliability hardening, or smoke testing.

## Core artifacts

- `/root/mgs-agent/scripts/cron-control-plane.py`
  - Read-only inventory/status generator for MGS root crontab jobs.
  - Parses `crontab -l`, extracts `/root/mgs-agent/scripts/*`, log paths, `flock`, owner/risk metadata, and last useful log signal.
  - `--write-doc` atomically regenerates `/root/mgs-agent/docs/CRONS.md`.
- `/root/mgs-agent/docs/CRONS.md`
  - Human-readable control plane: frequency, script, owner, risk, flock, last log, details per cron.
- `/root/mgs-agent/scripts/cron-smoke-test.sh`
  - Manual smoke test for safe/idempotent crons.
  - Runs destructive/risky jobs only with `--dry-run` when available.
  - Skips jobs that are production-timed or alert-oriented by design.
- `/root/mgs-agent/scripts/monitor-cron-stale-logs.sh`
  - Cron watchdog that alerts when a MGS cron log has not updated within tolerance.
  - Runs every 15 minutes via root crontab with `flock -n`.
  - State file: `/root/mgs-agent/data/cron-stale-logs-state.json`.

## Safe implementation sequence

1. Backup crontab before edits:
   ```bash
   crontab -l > /root/mgs-agent/data/crontab-backup-pre-<change>-$(date +%Y%m%d-%H%M%S).txt
   ```
2. Modify crontab via temp file, never with fragile heredoc-in-command-substitution.
3. Add `flock -n /var/lock/<job>.lock` to every MGS cron to prevent overlap.
4. For high-risk jobs, add `--dry-run` before including them in smoke tests.
5. Regenerate docs and inventory:
   ```bash
   /root/mgs-agent/scripts/cron-control-plane.py --write-doc
   /root/mgs-agent/scripts/infra-discovery.sh >> /root/mgs-agent/logs/infra-discovery.log 2>&1
   ```
6. Append structured audit event to `/root/mgs-agent/logs/events-audit.jsonl`.
7. Validate:
   ```bash
   crontab -l | grep -c '/root/mgs-agent/scripts/'
   crontab -l | grep -c 'flock -n .* /root/mgs-agent/scripts/'
   /root/mgs-agent/scripts/cron-smoke-test.sh
   /root/mgs-agent/scripts/monitor-cron-stale-logs.sh --dry-run
   grep -E 'Total MGS|Crons sem `flock`' /root/mgs-agent/docs/CRONS.md
   ```

## Operational judgement

Do not run every cron blindly. Classify:

- Run now: safe/idempotent local monitors, renderers, sync scripts with safety checks.
- Dry-run only: scripts that delete, close sessions, rotate state, or mutate auth/config.
- Skip by design: production reports tied to daily schedule, alert scripts that could spam Discord, or jobs whose correctness depends on real elapsed time.

## Thread cleanup lesson

Discord archived/stopped threads cost zero tokens and are valuable for audit/history. Prefer preserving threads. If a thread cleanup script exists, keep it deprecated/manual-only unless Rodolfo explicitly asks for deletion. Do not schedule automatic deletion just to save tokens.

## Pitfalls

- Empty log files right after creating a new cron can trigger stale-log false positives. Prime the log once or run the job manually before enabling stale monitoring.
- Some scripts log internally instead of using crontab redirection; map custom logs in the stale monitor (example: `cleanup-zombie-sessions.sh` → `logs/cleanup-zombies.log`).
- `infra-discovery.sh` rewrites `data/infra-inventory.json`; treat as medium risk but acceptable when user requested inventory regeneration.
- Auto-commit may push intermediate commits during multi-step changes; final validation still needs `git status --short` and recent log review.
