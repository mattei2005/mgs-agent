#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-stage-v2026-9-7-2237be35-mgs
NEW_LAUNCHER=/root/.local/bin/hermes-v0211-stable-2237be35-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-v0210-stable-29112bef-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_HEAD=8a7dbc8ced04ae5ca3fba76f46cead843ac723f5
EXPECTED_UPSTREAM=2237be355906fbe6065ce1815711eee52b2d646e
EXPECTED_TAG=v2026.9.7
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-09-10-v0211-2237be35.patch
PATCH_SHA=d8ee78770282c760e0a49871558b2be030e6c4e512bd353f23cd5c9bac50bdd1
MGS_GUARD=$ROOT/scripts/ensure-hermes-mgs-patches.sh
REGRESSION=$ROOT/scripts/run-hermes-post-upstream-regression.sh
SAFE_RESTART=$ROOT/scripts/mgs-gateway-restart-safe.sh
UV=/root/.local/bin/uv
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260910T081838-0400-vps-hermes-v0211/activation-targets.sha256
PIP_FREEZE_SHA=/root/.hermes/secure-backups/vps-maintenance/20260910T081838-0400-vps-hermes-v0211/candidate-pip-freeze.sha256
EVIDENCE=/root/.hermes/secure-backups/vps-maintenance/20260910T081838-0400-vps-hermes-v0211
RESULT=$ROOT/data/hermes-v0211-activation-result.json
LOCK=/run/lock/mgs-hermes-v0211-activation.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-v0211-activation-${STAMP}.log
SWITCHED=0
ROLLBACK_DONE=0

mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock "$EVIDENCE"
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
row={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"actor":"hermes-v0211-activation-finalizer","detail":detail}
with pathlib.Path(p).open('a',encoding='utf-8') as f:
    f.write(json.dumps(row,ensure_ascii=False)+'\n')
PY
}
write_result(){
  local status="$1" detail="$2"
  python3 - "$RESULT" "$status" "$detail" "$LOG" <<'PY'
import datetime,json,pathlib,subprocess,sys,tempfile,os
path=pathlib.Path(sys.argv[1]); status,detail,log=sys.argv[2:]
def show(unit,key):
    p=subprocess.run(['systemctl','show',unit,'-p',key,'--value'],text=True,capture_output=True)
    return p.stdout.strip()
def firstline(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    return next((x for x in (p.stdout+p.stderr).splitlines() if x.strip()),'')
services={}
for agent in ('ares','atena','zeus'):
    unit=f'{agent}-gateway.service'
    services[agent]={
        'active':show(unit,'ActiveState'),'sub':show(unit,'SubState'),
        'pid':show(unit,'MainPID'),'started':show(unit,'ExecMainStartTimestamp'),
        'restarts':show(unit,'NRestarts'),'exec_status':show(unit,'ExecMainStatus')}
data={
    'status':status,'detail':detail,
    'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'version':'0.21.1','release_tag':'v2026.9.7',
    'upstream_sha':'2237be355906fbe6065ce1815711eee52b2d646e',
    'port_commit':'8a7dbc8ced04ae5ca3fba76f46cead843ac723f5',
    'restart_order':['ares','atena','zeus'],
    'canonical_launcher':str(pathlib.Path('/root/.local/bin/hermes').resolve()),
    'version_line':firstline(['/root/.local/bin/hermes','--version']),
    'services':services,'log':log}
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.chmod(tmp,0o644);os.replace(tmp,path)
finally:
    if os.path.exists(tmp): os.unlink(tmp)
PY
}
atomic_launcher(){
  local target="$1" tmp="$CANONICAL.tmp.$$"
  ln -s "$target" "$tmp"
  mv -Tf "$tmp" "$CANONICAL"
  [[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$target")" ]]
}
prepare_and_run_restart(){
  local reason="$1" repo="$2" output finalizer
  output="$(HERMES_BIN="$CANONICAL" HERMES_REPO="$repo" "$SAFE_RESTART" --agents 'ares atena zeus' --reason "$reason" --delay 90)"
  finalizer="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'Prepared detached finalizer only \(no restart executed\): (\S+)',sys.argv[1])
if not m: raise SystemExit(1)
print(m.group(1))
PY
)"
  [[ -x "$finalizer" ]]
  "$finalizer"
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR
  set +e
  log "FAIL rc=$rc line=$line switched=$SWITCHED"
  audit hermes_v0211_activation_failed "rc=$rc line=$line switched=$SWITCHED log=$LOG"
  if [[ "$SWITCHED" == 1 ]]; then
    log 'Starting automatic rollback to Hermes v0.21.0'
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_run_restart 'rollback-hermes-v0211-activation' '/root/.hermes/hermes-agent-stage-v2026-8-31-29112bef'; then
      ROLLBACK_DONE=1
      log 'Rollback completed and all gateways passed readiness'
    else
      log 'Rollback attempt failed; manual intervention required'
    fi
  fi
  write_result failed "rc=$rc line=$line rollback_done=$ROLLBACK_DONE" || true
  audit hermes_v0211_activation_result "status=failed rollback_done=$ROLLBACK_DONE result=$RESULT log=$LOG"
  exit "$rc"
}
trap on_error ERR

log 'START Hermes v0.21.1 controlled activation'
audit hermes_v0211_activation_started "target=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD order=ares,atena,zeus log=$LOG"
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$OLD_LAUNCHER")" ]]
[[ "$(readlink -f "$NEW_LAUNCHER")" == "$REPO/.venv/bin/hermes" ]]
sha256sum -c "$SNAPSHOT"
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$PATCH_SHA" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ "$(git -C "$REPO" rev-parse "$EXPECTED_TAG^{commit}")" == "$EXPECTED_UPSTREAM" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
git -C "$REPO" fsck --no-dangling
git -C "$REPO" merge-base --is-ancestor "$EXPECTED_UPSTREAM" "$EXPECTED_HEAD"
[[ "$(git -C "$REPO" rev-list --count "$EXPECTED_UPSTREAM..$EXPECTED_HEAD")" == 4 ]]
git -C "$REPO" apply --reverse --check "$PATCH"
[[ "$("$UV" pip freeze --python "$REPO/.venv/bin/python" | LC_ALL=C sort | sha256sum | cut -d' ' -f1)" == "$(cut -d' ' -f1 "$PIP_FREEZE_SHA")" ]]
"$UV" pip check --python "$REPO/.venv/bin/python"
mapfile -t py_paths < <(git -C "$REPO" diff --name-only "$EXPECTED_UPSTREAM..$EXPECTED_HEAD" -- '*.py')
[[ ${#py_paths[@]} -gt 0 ]]
py_abs=(); for p in "${py_paths[@]}"; do py_abs+=("$REPO/$p"); done
"$REPO/.venv/bin/python" -m py_compile "${py_abs[@]}"
for profile in ares atena zeus; do
  HERMES_HOME="/root/.hermes/profiles/$profile" "$NEW_LAUNCHER" config check >"$EVIDENCE/finalizer-pre-config-$profile.log" 2>&1
  HERMES_HOME="/root/.hermes/profiles/$profile" "$NEW_LAUNCHER" auth status openai-codex >"$EVIDENCE/finalizer-pre-auth-$profile.log" 2>&1
  python3 - "$EVIDENCE/finalizer-pre-auth-$profile.log" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace').lower()
assert 'logged in' in s
assert 'consolidated forked' not in s and 'borrows the root grant' not in s
PY
done
HERMES_HOME=/root/.hermes "$NEW_LAUNCHER" config check >"$EVIDENCE/finalizer-pre-config-root.log" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-pre-patch-guard.log" "$MGS_GUARD" >"$EVIDENCE/finalizer-pre-patch-guard.stdout" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-pre-regression.log" "$REGRESSION" >"$EVIDENCE/finalizer-pre-regression.stdout" 2>&1
[[ -z "$(git -C "$REPO" status --porcelain)" ]]

python3 - <<'PY' >"$EVIDENCE/pre-activation-pids.json"
import json,subprocess
print(json.dumps({a:subprocess.run(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True,capture_output=True).stdout.strip() for a in ('ares','atena','zeus')}))
PY

atomic_launcher "$NEW_LAUNCHER"
SWITCHED=1
"$CANONICAL" --version | python3 -c 'import sys; line=next((x for x in sys.stdin if x.strip()),"").strip(); assert line.startswith("Hermes Agent v0.21.1 (2026.9.7)"), line'
prepare_and_run_restart 'hermes-v0211-stable-activation' "$REPO"

for agent in ares atena zeus; do
  svc="$agent-gateway.service"
  [[ "$(systemctl is-active "$svc")" == active ]]
  [[ "$(systemctl show "$svc" -p SubState --value)" == running ]]
  [[ "$(systemctl show "$svc" -p ExecMainStatus --value)" == 0 ]]
done
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$NEW_LAUNCHER")" ]]
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
python3 - "$EVIDENCE/pre-activation-pids.json" <<'PY'
import json,subprocess,sys
pre=json.load(open(sys.argv[1]))
for a in ('ares','atena','zeus'):
 p=subprocess.run(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True,capture_output=True,check=True).stdout.strip()
 assert p and p!='0' and p!=pre[a],(a,pre[a],p)
 print(a,'pid_changed=PASS')
PY

REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-post-patch-guard.log" "$MGS_GUARD" >"$EVIDENCE/finalizer-post-patch-guard.stdout" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-post-regression.log" "$REGRESSION" >"$EVIDENCE/finalizer-post-regression.stdout" 2>&1
for profile in ares atena zeus; do
  marker="MGS_V0211_${profile^^}_POST_OK"
  out="$EVIDENCE/finalizer-post-smoke-$profile.log"
  HERMES_HOME="/root/.hermes/profiles/$profile" "$CANONICAL" -z "Respond exactly $marker and nothing else." >"$out" 2>&1
  python3 - "$out" "$marker" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace'); marker=sys.argv[2]
last=next((x.strip() for x in reversed(s.splitlines()) if x.strip()),'')
assert s.count(marker)==1 and last==marker,(s.count(marker),last)
PY
done
python3 - <<'PY'
from pathlib import Path
import json
profiles=['ares','atena','zeus']
def vals(obj):
 out={'access':set(),'refresh':set()}
 def rec(x,path=()):
  if isinstance(x,dict):
   for k,v in x.items():
    kl=k.lower();np=path+(kl,)
    if isinstance(v,str) and v:
     if kl in ('access_token','access') and 'openai-codex' in np: out['access'].add(v)
     if kl in ('refresh_token','refresh') and 'openai-codex' in np: out['refresh'].add(v)
    else: rec(v,np)
  elif isinstance(x,list):
   for v in x: rec(v,path)
 rec(obj);return out
v={p:vals(json.loads(Path(f'/root/.hermes/profiles/{p}/auth.json').read_text())) for p in profiles}
for p in profiles:
 assert v[p]['access'] and v[p]['refresh'],p
for i,p in enumerate(profiles):
 for q in profiles[i+1:]:
  assert not (v[p]['access']&v[q]['access']),(p,q,'access')
  assert not (v[p]['refresh']&v[q]['refresh']),(p,q,'refresh')
root=json.loads(Path('/root/.hermes/auth.json').read_text())
assert 'openai-codex' not in (root.get('providers') or {})
assert 'openai-codex' not in (root.get('credential_pool') or {})
print('oauth_independence=PASS')
PY
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
write_result success 'Hermes v0.21.1 active; stable target 2237be35; MGS port 8a7dbc8c; services/readiness 3/3; guard/regression/smokes/auth PASS'
audit hermes_v0211_activation_finished "version=0.21.1 upstream=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD services=3/3 smokes=3/3 result=$RESULT log=$LOG"
log 'DONE Hermes v0.21.1 controlled activation'
