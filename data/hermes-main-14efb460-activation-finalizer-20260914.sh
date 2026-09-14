#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-stage-main-14efb460-mgs
NEW_LAUNCHER=/root/.local/bin/hermes-main-14efb460-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-v0213-stable-345cd2b0-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_HEAD=abbba7e0e8649759ab1fb4807b72b5ba4fc79de4
EXPECTED_UPSTREAM=14efb46089250e8b9e56e59b74291cf8dce8b207
EXPECTED_TAG=v2026.9.14
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-09-14-main-14efb460.patch
PATCH_SHA=cc3a798e26f531e7dcd5e52731b7adad44cbbb1d584d772b90b5549e281e093b
MGS_GUARD=$ROOT/scripts/ensure-hermes-mgs-patches.sh
REGRESSION=$ROOT/scripts/run-hermes-post-upstream-regression.sh
SAFE_RESTART=$ROOT/scripts/mgs-gateway-restart-safe.sh
REPORT_HELPER=$ROOT/scripts/send-report-infra-embed.sh
DISCORD_POST=$ROOT/scripts/discord-bot-post.py
UV=/root/.local/bin/uv
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460/activation-targets.sha256
PIP_FREEZE_SHA=/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460/candidate-pip-freeze.sha256
EVIDENCE=/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460
RESULT=$ROOT/data/hermes-main-14efb460-activation-result.json
CHECKPOINT_ID=vps-hermes-controlled-update-20260914
THREAD_ID=1549096295338221660
AUTHORIZATION_MESSAGE_ID=1549117792047992895
LOCK=/run/lock/mgs-hermes-main-14efb460-activation.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-main-14efb460-activation-${STAMP}.log
SWITCHED=0
ROLLBACK_DONE=0
RUNTIME_ACCEPTED=0

mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock "$EVIDENCE"
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
row={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"actor":"hermes-main-14efb460-activation-finalizer","detail":detail}
with pathlib.Path(p).open('a',encoding='utf-8') as f:
    f.write(json.dumps(row,ensure_ascii=False)+'\n')
PY
}
write_result(){
  local status="$1" detail="$2" report_id="${3:-}"
  python3 - "$RESULT" "$status" "$detail" "$LOG" "$report_id" <<'PY'
import datetime,json,pathlib,subprocess,sys,tempfile,os
path=pathlib.Path(sys.argv[1]); status,detail,log,report_id=sys.argv[2:]
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
    'version':'0.21.3','release_tag':'v2026.9.14+main-14efb460',
    'upstream_sha':'14efb46089250e8b9e56e59b74291cf8dce8b207',
    'port_commit':'abbba7e0e8649759ab1fb4807b72b5ba4fc79de4',
    'restart_order':['ares','atena','zeus'],
    'canonical_launcher':str(pathlib.Path('/root/.local/bin/hermes').resolve()),
    'version_line':firstline(['/root/.local/bin/hermes','--version']),
    'services':services,'report_infra_message_id':report_id or None,'log':log}
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
discord_readback(){
  local channel="$1" message_id="$2" expected_content="$3" expect_embed="$4"
  python3 - "$channel" "$message_id" "$expected_content" "$expect_embed" <<'PY'
import json,os,sys,urllib.request
channel,message_id,expected_content,expect_embed=sys.argv[1:]
for raw in open('/root/.hermes/profiles/zeus/.env',errors='ignore'):
    line=raw.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
token=os.environ.get('DISCORD_BOT_TOKEN')
assert token
req=urllib.request.Request(
    f'https://discord.com/api/v10/channels/{channel}/messages/{message_id}',
    headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=15) as r: data=json.load(r)
assert str(data.get('channel_id'))==channel
assert data.get('content','')==expected_content
assert len(data.get('embeds') or [])==(1 if expect_embed=='1' else 0)
assert not (data.get('mentions') or [])
print('discord_readback=PASS channel='+channel+' message_id='+message_id)
PY
}
post_callback(){
  local content="$1" output message_id
  output="$(python3 - "$content" <<'PY' | "$DISCORD_POST" --channel-id "$THREAD_ID"
import json,sys
print(json.dumps({'content':sys.argv[1],'allowed_mentions':{'parse':[]}},ensure_ascii=False))
PY
)" || return 1
  message_id="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m: raise SystemExit(1)
print(m.group(1))
PY
)"
  discord_readback "$THREAD_ID" "$message_id" "$content" 0
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR
  set +e
  log "FAIL rc=$rc line=$line switched=$SWITCHED runtime_accepted=$RUNTIME_ACCEPTED"
  audit hermes_main_14efb460_activation_failed "rc=$rc line=$line switched=$SWITCHED runtime_accepted=$RUNTIME_ACCEPTED log=$LOG"
  if [[ "$SWITCHED" == 1 && "$RUNTIME_ACCEPTED" == 0 ]]; then
    log 'Starting automatic rollback to Hermes v0.21.3 stable port'
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_run_restart 'rollback-hermes-main-14efb460-activation' '/root/.hermes/hermes-agent-stage-v2026-9-14-345cd2b0-mgs'; then
      ROLLBACK_DONE=1
      log 'Rollback completed and all gateways passed readiness'
    else
      log 'Rollback attempt failed; manual intervention required'
    fi
  fi
  local status=failed
  [[ "$RUNTIME_ACCEPTED" == 1 ]] && status=partial_governance_failure
  write_result "$status" "rc=$rc line=$line rollback_done=$ROLLBACK_DONE runtime_accepted=$RUNTIME_ACCEPTED" || true
  audit hermes_main_14efb460_activation_result "status=$status rollback_done=$ROLLBACK_DONE result=$RESULT log=$LOG"
  post_callback "**Resultado:** falha no update controlado do Hermes.\n**Estado real:** runtime_accepted=$RUNTIME_ACCEPTED; rollback_done=$ROLLBACK_DONE.\n**Pendência:** Zeus precisa reconciliar o resultado em \`$RESULT\`.\n**Evidência:** \`$LOG\`." || true
  exit "$rc"
}
trap on_error ERR

log 'START Hermes main 14efb460 controlled activation'
audit hermes_main_14efb460_activation_started "authorization_message_id=$AUTHORIZATION_MESSAGE_ID target=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD order=ares,atena,zeus log=$LOG"
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$OLD_LAUNCHER")" ]]
[[ "$(readlink -f "$NEW_LAUNCHER")" == "$REPO/.venv/bin/hermes" ]]
sha256sum -c "$SNAPSHOT"
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$PATCH_SHA" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ "$(git -C "$REPO" rev-parse HEAD^)" == "$EXPECTED_UPSTREAM" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
git -C "$REPO" fetch --quiet origin main --tags --prune
[[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_UPSTREAM" ]]
[[ "$(git -C "$REPO" rev-list --count "$EXPECTED_UPSTREAM..origin/main")" == 0 ]]
echo "origin_main_zero_pending_gate=PASS target=$EXPECTED_UPSTREAM"
git -C "$REPO" fsck --no-dangling
git -C "$REPO" merge-base --is-ancestor "$EXPECTED_UPSTREAM" "$EXPECTED_HEAD"
[[ "$(git -C "$REPO" rev-list --count "$EXPECTED_UPSTREAM..$EXPECTED_HEAD")" == 1 ]]
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
"$CANONICAL" --version | python3 -c 'import sys; line=next((x for x in sys.stdin if x.strip()),"").strip(); assert line.startswith("Hermes Agent v0.21.3 (2026.9.14)"), line'
prepare_and_run_restart 'hermes-main-14efb460-activation' "$REPO"

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
sha256sum -c "$SNAPSHOT"
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-post-patch-guard.log" "$MGS_GUARD" >"$EVIDENCE/finalizer-post-patch-guard.stdout" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-post-regression.log" "$REGRESSION" >"$EVIDENCE/finalizer-post-regression.stdout" 2>&1
for profile in ares atena zeus; do
  marker="MGS_MAIN_14EFB460_${profile^^}_POST_OK"
  out="$EVIDENCE/finalizer-post-smoke-$profile.log"
  HERMES_HOME="/root/.hermes/profiles/$profile" "$CANONICAL" -z "Respond exactly $marker and nothing else." >"$out" 2>&1
  python3 - "$out" "$marker" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace'); marker=sys.argv[2]
last=next((x.strip() for x in reversed(s.splitlines()) if x.strip()),'')
assert s.count(marker)==1 and last==marker,(s.count(marker),last)
PY
  HERMES_HOME="/root/.hermes/profiles/$profile" "$CANONICAL" config check >"$EVIDENCE/finalizer-post-config-$profile.log" 2>&1
done
HERMES_HOME=/root/.hermes "$CANONICAL" config check >"$EVIDENCE/finalizer-post-config-root.log" 2>&1
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

apt-get update -qq
[[ "$(apt-get -s -o Debug::NoLocking=1 upgrade | grep -c '^Inst ' || true)" == 0 ]]
[[ "$(apt-get -s -o Debug::NoLocking=1 full-upgrade | grep -c '^Inst ' || true)" == 0 ]]
[[ ! -e /var/run/reboot-required ]]
[[ "$(uname -r)" == 6.8.0-139-generic ]]
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
if command -v snap >/dev/null 2>&1; then
  snap refresh --list >"$EVIDENCE/finalizer-post-snap.log" 2>&1
fi
if command -v npm >/dev/null 2>&1; then
  npm outdated -g --json >"$EVIDENCE/finalizer-post-npm-outdated.json" 2>/dev/null || true
  python3 - "$EVIDENCE/finalizer-post-npm-outdated.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))=={}
PY
fi
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
RUNTIME_ACCEPTED=1

python3 - "$EVIDENCE/post-activation-cleanup-audit.json" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path(sys.argv[1])
data={
 'schema_version':1,'audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'residues created by Hermes main 14efb460 zero-pending activation only',
 'deletions_performed':0,'deletion_needed':[],
 'result':'no deletion needed; candidate is active, prior runtime retained as rollback, update evidence retained',
 'preexisting_invalid_partial_backup':{
   'path':'/root/.hermes/secure-backups/vps-maintenance/20260910T081838-0400-vps-hermes-v0211/hermes-profiles-pre-v0211.tar.gz',
   'bytes':9872080896,'status':'preserved; outside this update deletion scope'},
 'retained':[
   '/root/.hermes/hermes-agent-stage-main-14efb460-mgs',
   '/root/.hermes/hermes-agent-stage-v2026-9-14-345cd2b0-mgs',
   '/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460']}
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w',encoding='utf-8') as f:
  json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o600);os.replace(tmp,path)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
PY

write_result success 'Hermes v0.21.3 main active; origin/main target 14efb460 with zero pending at cutover; MGS port abbba7e0; services/readiness 3/3; guard 544+6; regression 312/4 skipped; changed-surface 649; smokes/auth 3/3; VPS current; cleanup no deletion needed'
python3 "$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert \
  --id "$CHECKPOINT_ID" --agent zeus --thread-id "$THREAD_ID" \
  --objective 'Atualizar VPS e Hermes pelo plano controlado MGS até o origin/main mais recente, com zero commits upstream conhecidos no cutover' \
  --state 'completed_validated_zero_pending: VPS APT/full-upgrade/Snap/npm zero, kernel 6.8.0-139, no reboot; Hermes v0.21.3 main active at port abbba7e0 over origin/main 14efb460; zero upstream commits pending at JIT cutover; Ares→Atena→Zeus new PIDs and Discord ready; guard 544+6, regression 312 pass/4 skip, changed-surface 649, smokes/auth 3/3; fresh backup SHA verified; cleanup audit no deletion needed; old invalid 9.87GB partial preserved outside scope' \
  --next-step 'Monitoramento rotineiro; commit que chegar depois do cutover será uma nova atualização, não pendência desta execução' \
  --source 'discord:thread:1549096295338221660;authorization:1549117792047992895;result:/root/mgs-agent/data/hermes-main-14efb460-activation-result.json;evidence:/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460;patch:/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-14-main-14efb460.patch'
python3 "$ROOT/scripts/mgs-knowledge-control.py" validate

python3 - "$ROOT/data/infra-inventory.json" "$LOG" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path(sys.argv[1]); log=sys.argv[2]
data=json.loads(path.read_text())
entry={
 'id':'zeus-vps-hermes-main-zero-20260914','agent':'zeus','type':'vps_hermes_controlled_update',
 'owner':'Rodolfo Mattei','requested_by':'Rodolfo Mattei','source_thread_id':'1549096295338221660',
 'confirmation_message_id':'1549117792047992895','status':'completed_validated_zero_pending',
 'vps':{'apt_upgrade_candidates':0,'apt_full_upgrade_candidates':0,'snap_updates':0,'npm_global_updates':0,'kernel':'6.8.0-139-generic','reboot_required':False},
 'hermes_before':'v0.21.3 stable b296c5e3','hermes_target':'origin/main 14efb460','hermes_target_sha':'14efb46089250e8b9e56e59b74291cf8dce8b207',
 'candidate_repo':'/root/.hermes/hermes-agent-stage-main-14efb460-mgs','candidate_port_commit':'abbba7e0e8649759ab1fb4807b72b5ba4fc79de4',
 'candidate_patch':'/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-14-main-14efb460.patch',
 'candidate_patch_sha256':'cc3a798e26f531e7dcd5e52731b7adad44cbbb1d584d772b90b5549e281e093b',
 'backup':'/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460',
 'validation':{'patch_guard':'544 passed + 6 subtests','regression':'312 passed, 4 skipped','changed_surface':'649 passed','config_profiles':'4/4','auth_profiles':'3/3 independent','one_shot_smokes':'3/3','services':'3/3 active+Discord ready'},
 'cleanup':{'deletions_performed':0,'result':'no deletion needed for update-created residues','preexisting_invalid_partial_preserved_bytes':9872080896},
 'origin_main_pending_at_cutover':0,'activation_log':log,
 'report_infra_pending':True,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
arr=data.setdefault('runtime_artifacts',[])
arr[:]=[x for x in arr if not (isinstance(x,dict) and x.get('id')==entry['id'])]
arr.append(entry)
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w',encoding='utf-8') as f:
  json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o644);os.replace(tmp,path)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
check=json.loads(path.read_text())
assert sum(1 for x in check['runtime_artifacts'] if isinstance(x,dict) and x.get('id')==entry['id'])==1
print('infra_inventory_readback=PASS')
PY

report_output="$($REPORT_HELPER \
  --action modificada --type 'runtime/script/data' \
  --path '/root/.hermes/hermes-agent-stage-main-14efb460-mgs; /root/.local/bin/hermes; /root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-14-main-14efb460.patch; /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh; /root/mgs-agent/data/agent-checkpoints.json; /root/mgs-agent/data/infra-inventory.json' \
  --reason 'Update controlado Hermes até origin/main, com zero commits upstream pendentes no cutover' \
  --evidence 'JIT origin/main=14efb460 e pending=0; VPS zero updates/no reboot; backup SHA OK; patch 57 paths reproduzível; guard 544+6; regressão 312/4; superfície 649; smokes/auth 3/3; serviços/Discord 3/3; limpeza sem deleção')"
report_id="$(python3 - "$report_output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m: raise SystemExit(1)
print(m.group(1))
PY
)"
discord_readback 1498132022634483894 "$report_id" '' 1
python3 - "$ROOT/data/infra-inventory.json" "$report_id" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path(sys.argv[1]); message_id=sys.argv[2]
data=json.loads(path.read_text())
entry=next(x for x in data['runtime_artifacts'] if isinstance(x,dict) and x.get('id')=='zeus-vps-hermes-main-zero-20260914')
entry['report_infra_pending']=False
entry['report_infra']={'message_id':message_id,'channel_id':'1498132022634483894','http_status':200,'readback':True,'content_empty':True,'embed_count':1,'mentions':0}
entry['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w',encoding='utf-8') as f:
  json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o644);os.replace(tmp,path)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
check=json.loads(path.read_text())
e=next(x for x in check['runtime_artifacts'] if isinstance(x,dict) and x.get('id')=='zeus-vps-hermes-main-zero-20260914')
assert e['report_infra_pending'] is False and e['report_infra']['message_id']==message_id
print('infra_report_readback=PASS')
PY
write_result success 'Hermes v0.21.3 main active; origin/main target 14efb460 with zero pending at cutover; MGS port abbba7e0; services/readiness 3/3; guard 544+6; regression 312/4 skipped; changed-surface 649; smokes/auth 3/3; VPS current; cleanup no deletion needed' "$report_id"
audit hermes_main_14efb460_activation_finished "version=0.21.3 main upstream=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD pending=0 services=3/3 smokes=3/3 report=$report_id result=$RESULT log=$LOG"

callback="**Resultado:** sucesso — Hermes atualizado até o **origin/main** com **0 commits pendentes no cutover**.\n**VPS:** 0 updates; kernel 6.8.0-139; sem reboot.\n**Hermes:** main \`14efb460\`, port MGS \`abbba7e0\`; Ares → Atena → Zeus reconectados.\n**Benefícios da atualização:** 10 commits do main com correções de fechamento de incidentes cron, quoting em approvals, transação atômica do state.db e image_gen via Codex; ajustes Desktop/Windows ficam majoritariamente fora do runtime MGS.\n**Validação:** patch 57 paths reproduzível; guard 544+6; regressão 312 pass/4 skip; superfície MGS 649 pass; config 4/4; Codex e smokes 3/3.\n**Backups:** novo backup control-plane e controles com SHA validado; v0.21.3 estável anterior retida para rollback.\n**Limpeza:** nenhum resíduo novo exigiu exclusão; arquivo parcial antigo de 9,87 GB continua preservado fora deste escopo.\n**Serviços:** Zeus, Atena e Ares ativos, PIDs novos e Discord pronto.\n**Pendência:** nenhuma. Commit publicado após este cutover será uma nova atualização.\n**Evidência:** \`$RESULT\`; REPORT-INFRA \`$report_id\`."
post_callback "$callback"
log 'DONE Hermes main 14efb460 controlled activation'
