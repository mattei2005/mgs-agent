# Hermes cron script-only alert routing

Use this when a Hermes `cronjob` runs a deterministic watchdog (`no_agent=true`, `script=...`) and Rodolfo expects operational alerts in Discord.

## Problem pattern

Hermes cron jobs created from a Discord thread default easily to `deliver=origin`. For script-only jobs, `stdout` is delivered verbatim to that origin. If the origin is an operational thread, a later watchdog failure can dump raw logs into an unrelated thread.

Bad shape:

```text
cronjob: no_agent=true
script: monitor-or-watchdog.sh
deliver: origin
script stdout: tail -40 log
```

Observed result:
- alert appears inside the thread where the cron was created;
- message is ugly/raw (`Cronjob Response`, job_id, log tail, split messages);
- no agent formats/summarizes it because `no_agent=true` bypasses the LLM;
- if the wrapper captures `$?` after `if ...; then`, it may report `rc=0` for a failure.

## Correct MGS pattern

1. Set Hermes cron delivery to local/silent:

```python
cronjob(action="update", job_id="...", deliver="local")
```

2. Keep healthy runs completely silent:

```bash
# success path
exit 0     # no stdout, no stderr
```

3. On failure, send a clean Discord embed to the proper alert channel webhook (usually `Discord Webhook - Alerts Infra Channel` / `#alerts-infra`) from inside the script.

4. Persist a small state file so the script sends one alert per failure episode and one green recovery when it returns to OK.

5. Keep the full raw log on VPS and include only path + short truncated detail in Discord.

6. Validate explicitly:

```bash
bash -n /root/mgs-agent/scripts/<watchdog>.sh
/root/mgs-agent/scripts/<watchdog>.sh >/tmp/watchdog.stdout 2>/tmp/watchdog.stderr || rc=$?
printf 'script_rc=%s\n' "${rc:-0}"
printf 'stdout_bytes='; wc -c < /tmp/watchdog.stdout
printf 'stderr_bytes='; wc -c < /tmp/watchdog.stderr
jq -c . /root/mgs-agent/data/<watchdog>-state.json
```

Expected for healthy run:

```text
script_rc=0
stdout_bytes=0
stderr_bytes=0
state.status=ok
```

## Wrapper exit-code pitfall

Do not do this:

```bash
if some_command; then
  exit 0
fi
rc=$?   # under `if`, this can be 0 / wrong for the failed command context
```

Use this instead:

```bash
set +e
some_command >> "$LOG" 2>&1
rc=$?
set -e
if (( rc == 0 )); then
  exit 0
fi
# handle failure with the real rc
```

## Discord layout expectation

For infra alerts, use embed fields, not raw text:

```text
content: <@344196393512075265> alerta de infra: <short reason>
embed.title: short human title
fields: Status, Exit code, Log completo, Resumo técnico, Ação
```

Never use `#zeus-admin-agent` or an arbitrary active thread for automated watchdog output.