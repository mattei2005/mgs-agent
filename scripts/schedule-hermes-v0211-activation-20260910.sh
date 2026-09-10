#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/root/mgs-agent
UNIT=mgs-hermes-v0211-activation-20260910
FINALIZER=$ROOT/data/hermes-v0211-activation-finalizer-20260910.sh
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260910T081838-0400-vps-hermes-v0211/activation-targets.sha256
OLD=/root/.local/bin/hermes-v0210-stable-29112bef-mgs
CANONICAL=/root/.local/bin/hermes
LOG=$ROOT/logs/hermes-v0211-activation-scheduler-20260910.log
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
with pathlib.Path(p).open('a') as f:
    f.write(json.dumps({'ts':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,'actor':'hermes-v0211-activation-scheduler','detail':detail},ensure_ascii=False)+'\n')
PY
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR
  log "FAIL rc=$rc line=$line"
  audit hermes_v0211_activation_schedule_failed "rc=$rc line=$line log=$LOG"
  exit "$rc"
}
trap on_error ERR
log 'START detached activation scheduler'
[[ -x "$FINALIZER" ]]
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$OLD")" ]]
sha256sum -c "$SNAPSHOT"
if systemctl is-active --quiet "${UNIT}.service" || systemctl is-active --quiet "${UNIT}.timer"; then
  log 'ABORT activation unit already active'
  exit 75
fi
systemd-run --unit="$UNIT" --on-active=90s --collect --no-block "$FINALIZER"
systemctl show "${UNIT}.timer" -p Id -p ActiveState -p SubState -p NextElapseUSecRealtime --no-pager
python3 - <<'PY'
from pathlib import Path
import json,datetime,tempfile,os
p=Path('/root/mgs-agent/data/infra-inventory.json');d=json.loads(p.read_text());item=next(x for x in d['runtime_artifacts'] if x.get('id')=='zeus-vps-hermes-update-20260909')
item.update({'status':'activation_scheduled','activation_unit':'mgs-hermes-v0211-activation-20260910.service','activation_callback_job_id':'2587aff0d0ad','report_infra_pending':True,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
raw=json.dumps(d,ensure_ascii=False,indent=2)+'\n';fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
try:
    with os.fdopen(fd,'w') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.chmod(tmp,0o644);os.replace(tmp,p)
finally:
    if os.path.exists(tmp):os.unlink(tmp)
r=json.loads(p.read_text());i=next(x for x in r['runtime_artifacts'] if x.get('id')=='zeus-vps-hermes-update-20260909')
assert i['status']=='activation_scheduled' and i['activation_unit']=='mgs-hermes-v0211-activation-20260910.service'
PY
audit hermes_v0211_activation_scheduled 'unit=mgs-hermes-v0211-activation-20260910.service delay=90s order=ares,atena,zeus callback_job=2587aff0d0ad target=8a7dbc8ced04ae5ca3fba76f46cead843ac723f5'
log 'DONE activation scheduled; canonical launcher remains v0.21.0 until finalizer fires'
