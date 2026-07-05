# Alerts-infra failed-alert background resolver

## When this applies

Use when Rodolfo asks Zeus to “ficar de olho” on `#alerts-infra` / channel `1498132022634483894` and automatically handle faulty/failing alerts that appear there, reporting the resolution in the same channel/message context.

This is different from a normal health monitor: it is a Discord-channel watcher that treats new alert messages as work items and launches a separate Zeus resolution run.

## Validated pattern

1. Create a deterministic polling script in `/root/mgs-agent/scripts/`.
2. Read the Zeus Discord bot token from the Zeus profile env, not from chat context.
3. Poll `GET /channels/{channel_id}/messages?limit=N` via Discord Bot API.
4. Keep a JSON state file with:
   - `last_seen_id`
   - `processed.{message_id}`
   - processing status / reply id / error
5. On first install, run `--init` to baseline to the newest existing message so old alerts are not reprocessed.
6. Candidate detection should be conservative:
   - include bot/webhook/embed messages only;
   - include failure terms such as `alerta`, `falhando`, `failed`, `erro`, `critical`, `indisponível`, `down`, `stale`, `timeout`, `restart de serviço detectado`;
   - skip `[REPORT-INFRA]`, self-improvement messages, cost/usage heartbeat, and resolution/status embeds.
7. Persist state as `processing` **before** launching the external action. This prevents duplicate loops if the resolver crashes mid-run.
8. Launch resolution outside the active Discord conversation using a Zeus oneshot (`hermes -p zeus -z ...`) with `HERMES_BACKGROUND_NOTIFICATIONS=off` and a bounded timeout.
9. The oneshot prompt must instruct Zeus to investigate runtime/canonical sources, fix only safe in-scope issues, and return a short PT-BR final response. It must not post directly to Discord; the watcher posts the final reply.
10. Reply to the original Discord message via `message_reference`, with `allowed_mentions: {parse: []}` to avoid accidental pings.
11. Cron should use `flock -n` and write to a dedicated log.
12. Validate with: `py_compile`, Discord GET, `--init`, dry-run/manual run, state JSON inspection, and cron entry check.

## Pitfalls

- Do not use Hermes `notify_on_complete=true` or script stdout delivery for this pattern. It can dump raw output into Discord.
- Do not start by processing history. Always baseline first with `--init` unless Rodolfo explicitly asks to triage old alerts.
- Do not classify `[REPORT-INFRA]` as a failed alert. REPORT-INFRA messages have their own processing path.
- Do not let the child Zeus run post directly into Discord; centralize posting in the watcher so replies stay attached to the original alert and are deduplicated.
- Treat destructive production fixes, credentials, billing, and scope changes as escalation/blockers inside the resolution response, not as autonomous actions.

## Example artifact names

- Script: `/root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py`
- State: `/root/mgs-agent/data/alerts-infra-failed-alert-resolver-state.json`
- Log: `/root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log`
- Cron: `2-57/5 * * * * flock -n /var/lock/alerts_infra_failed_alert_resolver.lock /root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py >> /root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log 2>&1`
