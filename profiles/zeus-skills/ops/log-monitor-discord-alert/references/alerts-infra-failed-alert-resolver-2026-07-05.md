# Alerts-infra failed-alert resolver (2026-07-05)

## Trigger

Rodolfo may ask Zeus to "ficar de olho" on `#alerts-infra` (`1498132022634483894`) and resolve failed alerts in background, then report in the same channel/thread.

## Validated pattern

1. Create a deterministic polling script instead of an LLM cron:
   - Fetch only recent channel messages (`limit=50` is safe for a 5 min cadence).
   - Keep `data/*-state.json` with `last_seen_id` and `processed`.
   - On first `--init`, baseline to the newest message to avoid processing old history.
   - Each run processes only IDs `> last_seen_id`, in ascending order.
2. Candidate filter:
   - Act only on bot/webhook/embed messages that look like active failures (`falhando`, `failed`, `critical`, `down`, `stale`, `timeout`, `restart de serviço detectado`, etc.).
   - Skip normal human chat, `REPORT-INFRA`, `RESOLVIDO`/`restabelecido`, cost/heartbeat/info, and Zeus' own messages.
3. Background resolution:
   - Persist state as `processing` before calling any external action to avoid loops.
   - Run `hermes -p zeus -z '<self-contained prompt>'` with `HERMES_BACKGROUND_NOTIFICATIONS=off`.
   - The oneshot investigates/corrects with real checks and returns a concise PT-BR executive result.
   - Always post visible closure feedback as a reply to the original alert: green Discord Embed `✅ ALERTA CORRIGIDO` only when the result explicitly confirms `resolvido`, `restabelecido`, `corrigido`, `normalizado` or equivalent; otherwise yellow Embed `🔎 ALERTA INVESTIGADO`. Keep `content` empty, disable mentions, and never silently leave a red/failure alert without its closure state.
   - Keep anti-spam in the persisted `processed` map: one closure message per original alert ID.
4. Cron:
   - Use `flock -n` and redirect to a dedicated log.
   - Example schedule: `2-57/5 * * * * flock -n /var/lock/alerts_infra_failed_alert_resolver.lock /root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py >> /root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log 2>&1`.
5. Validation:
   - `py_compile` for Python.
   - `--init`, `--dry-run`, and one manual cron-style execution.
   - Inspect state/log and confirm `last_seen_id` advances only for new messages.
   - Update `docs/CRONS.md`, `infra-inventory.json`, audit log, and send REPORT-INFRA when script/cron/data changes.

## Historical-alert pitfall

Because `--init` baselines to the newest message, alerts posted before initialization are intentionally not auto-processed. If Rodolfo points to an older screenshot/message, investigate it manually instead of expecting the new watcher to catch it retroactively.

## Auto-push failed-alert resolution pattern

When the failed alert is auto-push `non-fast-forward`:

1. Inspect current state:
   - `data/auto-push-monitor.json`
   - `logs/auto-push.log`
   - `logs/monitor-auto-push.log`
   - `git status --short`, `git fetch origin main`, `git rev-list --left-right --count HEAD...origin/main`
2. If local and remote diverged, create a backup branch before merge.
3. Merge `origin/main` into local `main`; resolve conflicts minimally. In the validated case, conflict was only duplicate checklist numbering in `profiles/zeus-skills/ops/smartbidding-dashboard-map/SKILL.md`.
4. Push using the same credential path as the post-commit hook when non-interactive HTTPS push lacks credentials:
   - temporary `GIT_ASKPASS`
   - source `/root/mgs-agent/.env` with `set -a / set +a`
   - username `mattei2005`
   - token from 1Password item `GitHub PAT - mgs-agent`, field `github_token`
5. Verify:
   - `HEAD == origin/main`
   - ahead/behind `0 0`
   - run `monitor-auto-push.sh` manually
   - confirm `consecutive_failures=0` and resolution alert sent.

## Reporting style

For Rodolfo: short status table/block only. Include cause, correction, current HEAD/origin, monitor state, and whether the Discord resolution was sent.
