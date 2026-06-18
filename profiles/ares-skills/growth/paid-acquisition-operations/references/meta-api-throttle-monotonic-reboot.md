# Meta API throttle — monotonic state after reboot

## Trigger

Use this reference when Ares Meta scripts or Hermes cron jobs start timing out while holding `data/ares/meta-ads/cache/meta-api-throttle-state.json`, especially after a VPS reboot or service restart.

## Symptom observed

- Meta cron/script appears stuck before/inside Graph API calls.
- `lsof data/ares/meta-ads/cache/meta-api-throttle-state.json` shows a Python Meta script holding the throttle file.
- `cronjob list` may show intraday/HOA as `script timed out after 120s`.
- `ps` shows stale `ares-meta-*` process even though Graph itself is reachable.

## Root cause

`time.monotonic()` is boot/process-local. Persisting a raw monotonic timestamp to disk can become invalid after reboot. If the persisted `last_request_monotonic` is much larger than the current boot's `time.monotonic()`, throttle math can compute a huge positive wait and sleep for hours/days while holding the cross-process lock.

Bad pattern:

```python
last = float(state.get('last_request_monotonic') or 0)
wait = MIN_INTERVAL_SECONDS - (time.monotonic() - last)
if wait > 0:
    time.sleep(wait)
```

## Durable fix pattern

Clamp impossible future monotonic values before sleeping, and never sleep longer than the configured min interval:

```python
now = time.monotonic()
last = float(state.get('last_request_monotonic') or 0)
if last > now:
    last = 0
wait = MIN_INTERVAL_SECONDS - (now - last)
if 0 < wait <= MIN_INTERVAL_SECONDS:
    time.sleep(wait)
    now = time.monotonic()
```

## Diagnostic commands

```bash
ps -eo pid,ppid,etime,stat,cmd | grep -E 'ares-meta-(auth-check|cron-runner|hoa-manager)|ares-meta' | grep -v grep || true
lsof /root/mgs-agent/data/ares/meta-ads/cache/meta-api-throttle-state.json 2>/dev/null || true
python3 - <<'PY'
import time, json
p='/root/mgs-agent/data/ares/meta-ads/cache/meta-api-throttle-state.json'
s=json.load(open(p))
print('now', time.monotonic())
print('last', s.get('last_request_monotonic'))
print('wait', s.get('min_interval_seconds',0) - (time.monotonic()-s.get('last_request_monotonic',0)))
PY
```

## Verification

1. `python3 -m py_compile scripts/ares-meta-common.py`.
2. Run a quick Graph smoke test with `ARES_META_MIN_INTERVAL_SECONDS=0` to isolate token/API validity from throttle behavior.
3. Trigger or run the script-only cron once and confirm it exits quickly.
4. If Graph returns OAuth/API errors, treat those separately from throttle timeout; do not keep retrying timed-out cron jobs.
