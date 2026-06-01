# Cron recovery after disk-full / ENOSPC — MGS

Use after a disk-full incident, VPS update, or gateway outage produces repeated Discord alerts like `Cron com erro no log` with `Traceback`, `No space left on device`, `JSONDecodeError`, or stale-log alerts.

## Triage principle

Do not trust alert screenshots alone. Classify each alert as **active**, **resolved**, **historical**, or **state-corruption** by inspecting current log tails, state files, syntax, and manual safe execution.

## Checklist

```bash
cd /root/mgs-agent

date
df -h /
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service || true
crontab -l | grep -E 'monitor-service-restarts|monitor-cron-stale-logs|hermes-news-explainer|monitor-auto-push|mgs-agent' || true
```

For scripts mentioned in alerts:

```bash
python3 -m py_compile scripts/hermes-news-explainer.py
bash -n scripts/monitor-service-restarts.sh
bash -n scripts/monitor-cron-stale-logs.sh
bash -n scripts/monitor-auto-push.sh
```

Validate state JSONs. A zero-byte JSON after ENOSPC is common and must be rebuilt, not ignored:

```bash
for f in \
  data/hermes-news-explainer-state.json \
  data/service-restart-state.json \
  data/cron-stale-logs-state.json \
  data/auto-push-monitor.json; do
  [ -f "$f" ] && python3 -m json.tool "$f" >/dev/null && echo "OK $f" || echo "BROKEN/MISSING $f"
done
```

## Rebuild `service-restart-state.json` after corruption

If `data/service-restart-state.json` is empty/broken, back it up and recreate baselines from current `NRestarts`. This prevents the restart monitor from repeatedly alerting on historical restarts caused by the incident.

```bash
cd /root/mgs-agent
TS=$(date +%Y%m%d-%H%M%S)
[ -f data/service-restart-state.json ] && cp -a data/service-restart-state.json "data/service-restart-state.json.corrupt-$TS.bak"
python3 - <<'PY'
import json, subprocess, datetime
services=['zeus-gateway','atena-gateway','mgs-autocommit']
now=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()+'Z'
state={'_meta':{'description':'Estado do monitor service-restart-watcher','created':now,'thresholds':{'info':3,'warn':5},'window_hours':24,'anti_spam_hours':12,'reinitialized_after':'disk-full incident'},'services':{}}
for svc in services:
    out=subprocess.run(['systemctl','show',f'{svc}.service','-p','NRestarts'],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout.strip()
    try: n=int(out.split('=',1)[1])
    except Exception: n=0
    state['services'][svc]={'baseline_nrestarts':n,'baseline_timestamp':now,'window_start':now,'last_alert_sent':None,'last_alert_level':None}
with open('/root/mgs-agent/data/service-restart-state.json','w') as f:
    json.dump(state,f,indent=2)
print(json.dumps({svc: state['services'][svc]['baseline_nrestarts'] for svc in services}, indent=2))
PY
python3 -m json.tool data/service-restart-state.json >/dev/null
```

## Manual safe executions

Use dry-run modes to avoid false Discord spam:

```bash
cd /root/mgs-agent

echo "=== manual validation start $(date -Iseconds) after disk-full incident ===" >> logs/hermes-news-explainer.log
python3 scripts/hermes-news-explainer.py --dry-run >> logs/hermes-news-explainer.log 2>&1

echo "=== manual validation start $(date -Iseconds) after disk-full incident ===" >> logs/monitor-service-restarts.log
MGS_DRY_RUN=1 bash scripts/monitor-service-restarts.sh >> logs/monitor-service-restarts.log 2>&1

echo "=== manual validation start $(date -Iseconds) after disk-full incident ===" >> logs/monitor-auto-push.log
bash scripts/monitor-auto-push.sh >> logs/monitor-auto-push.log 2>&1
```

Then evaluate the watchdog without posting:

```bash
bash scripts/monitor-cron-stale-logs.sh --dry-run
```

Expected result: all jobs `OK` except `monitor-cron-stale-logs.sh | SKIP | watchdog self-skip`, and `problems=0`.

## Clear stale alert state

If dry-run reports `problems=0 resolved=N`, run the stale monitor once for real so Discord/state gets resolution and stops anti-spam loops:

```bash
bash scripts/monitor-cron-stale-logs.sh >> logs/monitor-cron-stale-logs.log 2>&1
bash scripts/monitor-cron-stale-logs.sh --dry-run | tail -25
```

## mgs-autocommit nuance

`mgs-autocommit.service` may be `inactive/dead` with `status=0/SUCCESS` because the inotify watcher process exited cleanly. Its historical `NRestarts` can still trigger the restart monitor. Treat separately from Hermes gateways:

```bash
systemctl show mgs-autocommit.service -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp -p NRestarts --no-pager
journalctl -u mgs-autocommit.service --since '2 hours ago' --no-pager -p warning..alert | tail -80
```

Do not restart it automatically unless the user wants the watcher live again; provide:

```bash
systemctl start mgs-autocommit.service
sleep 3
systemctl show mgs-autocommit.service -p ActiveState -p SubState -p MainPID -p NRestarts --no-pager
```

## Reporting shape

Use a compact table:

```text
Cron / item                    Status agora  Validação
------------------------------ ------------- --------------------------------
hermes-news-explainer.py       OK            py_compile OK; --dry-run OK
monitor-service-restarts.sh    OK            bash -n OK; MGS_DRY_RUN=1 OK
monitor-cron-stale-logs.sh     OK            dry-run problems=0
monitor-auto-push.sh           OK            manual OK; state JSON OK
```

Mention whether a green `resolved` embed may have been sent by the real stale monitor run.
