# Cron semantic error audit — MGS repo scan lesson

Use this when a cron watchdog says logs are fresh but the user asks for a deep health/audit pass. Fresh `mtime` proves the cron ran; it does **not** prove the cron succeeded.

## Validated failure pattern

`track-article-cost.sh` produced this every 15 minutes while still updating its log, so a stale-log watchdog reported OK:

```text
Pending publications: 0
0
line 76: [[: 0
0: syntax error in expression (error token is "0")
```

Root cause:

```bash
PUB_COUNT=$(printf "%s" "$PUBLICATIONS" | grep -c "create-post OK" || echo 0)
```

When `grep -c` finds zero matches it prints `0` and exits 1. The `|| echo 0` prints a second `0`, so the variable becomes `0\n0`, breaking numeric `[[ ... -eq 0 ]]`.

Safe patterns:

```bash
PUB_COUNT=$(printf "%s" "$PUBLICATIONS" | grep -c "create-post OK" || true)
PUB_COUNT="${PUB_COUNT:-0}"
```

or avoid `grep -c` exit semantics entirely:

```bash
PUB_COUNT=$(python3 - <<'PY'
import os
print(os.environ.get('PUBLICATIONS','').count('create-post OK'))
PY
)
```

## Audit checklist

1. Run the stale-log monitor/dry-run first to separate `cron did not run` from `cron ran but errored`.
2. Scan recent log tails for semantic errors:

```bash
for f in /root/mgs-agent/logs/*.log; do
  c=$(tail -n 300 "$f" 2>/dev/null | grep -Ei 'error|erro|fatal|traceback|exception|failed|falha|critical|syntax error' | wc -l)
  [ "$c" -gt 0 ] && printf '%s %s\n' "$f" "$c"
done
```

3. Search shell scripts for the double-zero pattern:

```bash
grep -RInE 'grep -c .*\|\| echo 0' /root/mgs-agent/scripts /root/mgs-agent/skills 2>/dev/null
```

4. For monitors, semantic health should alert on recent error signatures, not just log `mtime`.

## Reporting rule

If a cron is fresh but logging errors, report as `RODANDO COM ERRO`, not `OK`. Evidence should include the script, line if known, and a redacted log excerpt.
