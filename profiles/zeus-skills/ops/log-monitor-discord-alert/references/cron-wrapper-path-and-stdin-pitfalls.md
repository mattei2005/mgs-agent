# Cron wrapper PATH and stdin pitfalls

Use this when a cron monitor calls another wrapper script (for example a health monitor that invokes a Python/uv wrapper) and the manual run works but the cron run fails.

## Durable lessons

1. Validate monitors in a cron-like empty environment, not only in the interactive shell:

```bash
env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin DRY_RUN=1 /root/mgs-agent/scripts/monitor-NAME.sh
```

2. If a wrapper depends on binaries installed under root user paths such as `/root/.local/bin`, make the wrapper itself cron-safe:

```bash
export PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
```

Do this in the wrapper that needs the binary, not only in the monitor, so every caller gets the same behavior.

3. Do not pipe command output into `python3 - <<'PY' ...` and then expect Python to read stdin. The here-doc already consumes stdin for the script body. Use a temp file or argv instead:

```bash
RAW_FILE="$(mktemp)"
printf '%s' "$output" > "$RAW_FILE"
python3 - "$RAW_FILE" <<'PY'
import json, sys
raw = open(sys.argv[1], errors="replace").read()
print(json.loads(raw).get("status"))
PY
rm -f "$RAW_FILE"
```

4. If a monitor sends a false alert and then recovers, reset alert state fields such as `last_alert_sent` on recovery when you want a future real failure to alert immediately instead of being suppressed by the previous false-positive anti-spam window.

## Validation checklist

- `bash -n wrapper monitor`
- wrapper works under `env -i ...`
- monitor dry-run works under `env -i ...`
- monitor real run ends `status=ok failures=0`
- state file has `last_status=ok`, empty failure details, and alert state reset if appropriate
- REPORT-INFRA + inventory update if script/cron/data changed
