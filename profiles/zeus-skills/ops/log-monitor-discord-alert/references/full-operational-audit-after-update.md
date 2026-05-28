# Full operational audit after Hermes update or agent restart

Use when Rodolfo asks “verifica se tudo está funcionando” or “verifica todos os crons”. This is broader than checking `systemctl is-active`.

## Checklist

1. Services and resources
   - `date -Is`, `uptime`, `free -h`, `df -h / /root /tmp`, `df -ih / /root /tmp`.
   - Check `zeus-gateway`, `atena-gateway`, `ares-gateway`, `mgs-autocommit`, `cron` with `systemctl is-active`, `is-enabled`, and `systemctl show` fields: `MainPID`, `ActiveEnterTimestamp`, `ActiveState`, `SubState`, `NRestarts`, `Result`.
   - Grep recent journals for `traceback|exception|oom|critical|failed with result|permission denied|segfault|address already|auth failed|token expired`.
   - For restart windows, compare log timestamps against the new `ActiveEnterTimestamp`; old restart failures may be historical/expected.

2. Crons
   - Dump root `crontab -l` and count jobs.
   - Run `/root/mgs-agent/scripts/cron-control-plane.py --json` when present; use it as the canonical inventory.
   - Run `/root/mgs-agent/scripts/monitor-cron-stale-logs.sh --dry-run` to catch stale logs and semantic errors.
   - Run `/root/mgs-agent/scripts/cron-smoke-test.sh --dry-run` if present. Treat explicit skips as design, not failure.
   - Check no long-running cron/script/flock process is stuck with `ps`.

3. Cron semantic error handling
   - If stale-log reports one bad cron, inspect that script and log.
   - Validate `bash -n` for shell scripts.
   - Confirm credentials without printing secrets: item found + field length only.
   - If safe/idempotent, run the cron manually once and then rerun stale-log dry-run. A resolved transient should be reported as resolved, not left as active failure.

4. Auto-commit / repo health
   - Check `/root/mgs-agent` git status and auto-commit logs, not just service state.
   - `mgs-autocommit.service active` does not mean commits are happening; guardrail can block every cycle.
   - Tail `/root/mgs-agent/logs/auto-commit-watcher.log` for `BLOQUEADO` and `/root/mgs-agent/logs/auto-push.log` for `auto-push FAIL`.
   - If blocked by a filename that contains `token|password|secret|webhook|credential`, scan the file for actual secret patterns without printing content. If no secret is present and the file is documentation, recommend renaming the file to remove the sensitive word rather than weakening the guardrail.

5. Hermes auth/provider
   - For profiles `zeus`, `atena`, `ares`, report provider/model/active provider and token presence by length/boolean only.
   - Confirm policy: `openai-codex` + `gpt-5.5`, no Anthropic/Claude fallback unless explicitly authorized.

## Reporting shape

Use compact status tables:

- Summary by area: Gateways, Crons, Hermes cron internal, Provider/model, VPS resources, Monitors, Auto-commit.
- Services table with active state + PID.
- Crons table with total jobs, flock coverage, stale-log result, smoke result.
- Pendências reais: distinguish active problem, resolved transient, and expected restart noise.

## Common interpretations

- `Hermes cron list` count 0 is OK when MGS uses Linux crontab for operational monitors.
- `monitor-yoast-health-eggbev` can fail transiently if 1Password lookup returns empty; if a manual rerun gets credentials, SSH, SQL and snapshot OK, classify the prior error as resolved.
- `mgs-autocommit.service` may be active while committing nothing because the security guardrail blocks a suspicious path. This is a real operational pending item because repo changes stop being pushed.
- Docs with names like `new-discord-agent-bot-token-1password.md` can trigger the guardrail even when they contain no secret. Prefer renaming to `new-discord-agent-1password-credential-flow.md` or similar after confirmation.