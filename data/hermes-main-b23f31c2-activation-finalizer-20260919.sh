#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-stage-main-469296c7-mgs
NEW_LAUNCHER=/root/.local/bin/hermes-main-b23f31c2-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-main-14efb460-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_HEAD=97281690c498129887512cfee462b086ee200d04
EXPECTED_UPSTREAM=b23f31c2bd4977fa49f493e38816b7e70c666a55
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-09-19-main-b23f31c2.patch
PATCH_SHA=e7adce639c314c9dd080c2ca19661c59a76937d5f343f1adc8277f1f1d1c4130
MGS_GUARD=$ROOT/scripts/ensure-hermes-mgs-patches.sh
REGRESSION=$ROOT/scripts/run-hermes-post-upstream-regression.sh
SAFE_RESTART=$ROOT/scripts/mgs-gateway-restart-safe.sh
REPORT_HELPER=$ROOT/scripts/send-report-infra-embed.sh
DISCORD_POST=$ROOT/scripts/discord-bot-post.py
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260919T155128Z-vps-hermes-update/activation-b23-targets.sha256
PIP_FREEZE_SHA=/root/.hermes/secure-backups/vps-maintenance/20260919T155128Z-vps-hermes-update/candidate-b23-pip-freeze.sha256
EVIDENCE=/root/.hermes/secure-backups/vps-maintenance/20260919T155128Z-vps-hermes-update
CLEANUP_MANIFEST=$ROOT/data/hermes-cleanup-manifest-20260919-b23f31c2.json
CLEANUP_MANIFEST_SHA=56cca798e9764fba093f34028c826fab40cee383dbb881a1e0b6c6e9d2b74a7a
CLEANUP_RESULT=$ROOT/data/hermes-cleanup-manifest-20260919-b23f31c2-result.json
RESULT=$ROOT/data/hermes-main-b23f31c2-activation-result.json
CHECKPOINT_ID=ZEUS-VPS-HERMES-UPDATE-20260919
THREAD_ID=1550646583367045221
CUTOVER_AUTH=1550910739626332271
CLEANUP_AUTH=1550919292315504671
LOCK=/run/lock/mgs-hermes-main-b23f31c2-activation.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-main-b23f31c2-activation-${STAMP}.log
SWITCHED=0
ROLLBACK_DONE=0
RUNTIME_ACCEPTED=0
REPORT_ID=""
POST_CUTOFF_COUNT=unknown

mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock "$EVIDENCE"
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
row={"timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"agent":"zeus-b23f31c2-finalizer","detail":detail}
with pathlib.Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
PY
}
atomic_launcher(){
  local target="$1" tmp="$CANONICAL.tmp.$$"
  ln -s "$target" "$tmp"
  mv -Tf "$tmp" "$CANONICAL"
  [[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$target")" ]]
}
write_result(){
  local status="$1" detail="$2" report_id="${3:-}"
  python3 - "$RESULT" "$status" "$detail" "$LOG" "$report_id" "$POST_CUTOFF_COUNT" <<'PY'
import datetime,json,os,pathlib,subprocess,sys,tempfile
path=pathlib.Path(sys.argv[1]); status,detail,log,report_id,post_cutoff=sys.argv[2:]
def show(unit,key):
 p=subprocess.run(['systemctl','show',unit,'-p',key,'--value'],text=True,capture_output=True);return p.stdout.strip()
def firstline(cmd):
 p=subprocess.run(cmd,text=True,capture_output=True);return next((x for x in (p.stdout+p.stderr).splitlines() if x.strip()),'')
services={}
for agent in ('ares','atena','zeus'):
 unit=f'{agent}-gateway.service';services[agent]={'active':show(unit,'ActiveState'),'sub':show(unit,'SubState'),'pid':show(unit,'MainPID'),'started':show(unit,'ExecMainStartTimestamp'),'restarts':show(unit,'NRestarts'),'exec_status':show(unit,'ExecMainStatus')}
data={'status':status,'detail':detail,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':'0.21.3','release_tag':'v2026.9.14+main-b23f31c2','upstream_sha':'b23f31c2bd4977fa49f493e38816b7e70c666a55','port_commit':'97281690c498129887512cfee462b086ee200d04','cutoff_policy':'SHA frozen at authorized resumption; later commits are a new update cycle','post_cutoff_commits':post_cutoff,'restart_order':['ares','atena','zeus'],'canonical_launcher':str(pathlib.Path('/root/.local/bin/hermes').resolve()),'version_line':firstline(['/root/.local/bin/hermes','--version']),'services':services,'finance_model_route':{'thread_id':'1545426987756298340','model':'gpt-6-astra','provider':'openai-codex','topic_policy':True},'report_infra_message_id':report_id or None,'cleanup_result':'/root/mgs-agent/data/hermes-cleanup-manifest-20260919-b23f31c2-result.json','log':log}
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o644);os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
}
prepare_and_run_restart(){
  local reason="$1" repo="$2" output finalizer
  output="$(HERMES_BIN="$CANONICAL" HERMES_REPO="$repo" "$SAFE_RESTART" --agents 'ares atena zeus' --reason "$reason" --delay 20)"
  finalizer="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'Prepared detached finalizer only \(no restart executed\): (\S+)',sys.argv[1])
if not m:raise SystemExit(1)
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
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
token=os.environ.get('DISCORD_BOT_TOKEN');assert token
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{message_id}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
assert str(data.get('channel_id'))==channel and data.get('content','')==expected_content
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
if not m:raise SystemExit(1)
print(m.group(1))
PY
)"
  discord_readback "$THREAD_ID" "$message_id" "$content" 0
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR;set +e
  log "FAIL rc=$rc line=$line switched=$SWITCHED runtime_accepted=$RUNTIME_ACCEPTED"
  audit hermes_main_b23f31c2_activation_failed "rc=$rc line=$line switched=$SWITCHED accepted=$RUNTIME_ACCEPTED log=$LOG"
  if [[ "$SWITCHED" == 1 && "$RUNTIME_ACCEPTED" == 0 ]]; then
    log 'Starting automatic rollback to prior main runtime'
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_run_restart 'rollback-hermes-main-b23f31c2-activation' '/root/.hermes/hermes-agent-stage-main-14efb460-mgs'; then ROLLBACK_DONE=1;log 'Rollback completed';else log 'Rollback failed';fi
  fi
  local status=failed;[[ "$RUNTIME_ACCEPTED" == 1 ]] && status=partial_governance_failure
  write_result "$status" "rc=$rc line=$line rollback_done=$ROLLBACK_DONE runtime_accepted=$RUNTIME_ACCEPTED" "$REPORT_ID" || true
  post_callback "**Resultado:** falha no update controlado do Hermes.\n**Estado real:** runtime_accepted=$RUNTIME_ACCEPTED; rollback_done=$ROLLBACK_DONE.\n**Pendência:** Zeus precisa reconciliar \`$RESULT\`.\n**Evidência:** \`$LOG\`." || true
  exit "$rc"
}
trap on_error ERR

log 'START Hermes main b23f31c2 controlled activation'
audit hermes_main_b23f31c2_activation_started "cutover_auth=$CUTOVER_AUTH cleanup_auth=$CLEANUP_AUTH target=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD order=ares,atena,zeus"
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$OLD_LAUNCHER")" ]]
[[ "$(readlink -f "$NEW_LAUNCHER")" == "$REPO/.venv/bin/hermes" ]]
sha256sum -c "$SNAPSHOT"
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$PATCH_SHA" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ "$(git -C "$REPO" rev-parse HEAD^)" == "$EXPECTED_UPSTREAM" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
git -C "$REPO" fsck --no-dangling
git -C "$REPO" apply --reverse --check "$PATCH"
[[ "$(sha256sum "$EVIDENCE/candidate-b23-pip-freeze.txt" | cut -d' ' -f1)" == "$(cut -d' ' -f1 "$PIP_FREEZE_SHA")" ]]
/root/.local/bin/uv pip check --python "$REPO/.venv/bin/python"
mapfile -t py_paths < <(git -C "$REPO" diff --name-only "$EXPECTED_UPSTREAM..$EXPECTED_HEAD" -- '*.py')
py_abs=();for p in "${py_paths[@]}";do py_abs+=("$REPO/$p");done
"$REPO/.venv/bin/python" -m py_compile "${py_abs[@]}"
for profile in ares atena zeus;do
 HERMES_HOME="/root/.hermes/profiles/$profile" "$NEW_LAUNCHER" config check >"$EVIDENCE/finalizer-b23-pre-config-$profile.log" 2>&1
 HERMES_HOME="/root/.hermes/profiles/$profile" "$NEW_LAUNCHER" auth status openai-codex >"$EVIDENCE/finalizer-b23-pre-auth-$profile.log" 2>&1
 python3 - "$EVIDENCE/finalizer-b23-pre-auth-$profile.log" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace').lower();assert 'logged in' in s;assert 'consolidated forked' not in s and 'borrows the root grant' not in s
PY
done
HERMES_HOME=/root/.hermes "$NEW_LAUNCHER" config check >"$EVIDENCE/finalizer-b23-pre-config-root.log" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-b23-pre-guard.log" "$MGS_GUARD" >"$EVIDENCE/finalizer-b23-pre-guard.stdout" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-b23-pre-regression.log" "$REGRESSION" >"$EVIDENCE/finalizer-b23-pre-regression.stdout" 2>&1
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
python3 - <<'PY' >"$EVIDENCE/pre-activation-b23-pids.json"
import json,subprocess
print(json.dumps({a:subprocess.run(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True,capture_output=True).stdout.strip() for a in ('ares','atena','zeus')}))
PY

atomic_launcher "$NEW_LAUNCHER"
SWITCHED=1
"$CANONICAL" --version | python3 -c 'import sys;line=next((x for x in sys.stdin if x.strip()),"").strip();assert "upstream b23f31c2" in line and "local 97281690" in line,line'
prepare_and_run_restart 'hermes-main-b23f31c2-activation' "$REPO"

for agent in ares atena zeus;do
 svc="$agent-gateway.service";[[ "$(systemctl is-active "$svc")" == active ]];[[ "$(systemctl show "$svc" -p SubState --value)" == running ]];[[ "$(systemctl show "$svc" -p ExecMainStatus --value)" == 0 ]]
done
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$NEW_LAUNCHER")" ]]
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
python3 - "$EVIDENCE/pre-activation-b23-pids.json" "$EXPECTED_HEAD" <<'PY'
import json,pathlib,subprocess,sys
pre=json.load(open(sys.argv[1]));expected=sys.argv[2]
for a in ('ares','atena','zeus'):
 unit=a+'-gateway.service';pid=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip();assert pid and pid!='0' and pid!=pre[a],(a,pre[a],pid)
 state=json.loads(pathlib.Path(f'/root/.hermes/profiles/{a}/gateway_state.json').read_text());discord=(state.get('platforms') or {}).get('discord') or {}
 assert state.get('code_sha')==expected,(a,state.get('code_sha'))
 assert discord.get('state')=='connected',(a,discord)
 assert str(discord.get('writer_pid'))==pid,(a,discord.get('writer_pid'),pid)
 print(a,'gateway_state=PASS pid='+pid)
PY
sha256sum -c "$SNAPSHOT"
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-b23-post-guard.log" "$MGS_GUARD" >"$EVIDENCE/finalizer-b23-post-guard.stdout" 2>&1
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$EVIDENCE/finalizer-b23-post-regression.log" "$REGRESSION" >"$EVIDENCE/finalizer-b23-post-regression.stdout" 2>&1
for profile in ares atena zeus;do
 marker="MGS_MAIN_B23F31C2_${profile^^}_POST_OK";out="$EVIDENCE/finalizer-b23-post-smoke-$profile.log"
 HERMES_HOME="/root/.hermes/profiles/$profile" "$CANONICAL" -z "Respond exactly $marker and nothing else." >"$out" 2>&1
 python3 - "$out" "$marker" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace');marker=sys.argv[2];lines=[x.strip() for x in s.splitlines() if x.strip()];assert s.count(marker)==1 and lines[-1]==marker,(s.count(marker),lines[-1] if lines else '')
PY
 HERMES_HOME="/root/.hermes/profiles/$profile" "$CANONICAL" config check >"$EVIDENCE/finalizer-b23-post-config-$profile.log" 2>&1
done
HERMES_HOME=/root/.hermes "$CANONICAL" config check >"$EVIDENCE/finalizer-b23-post-config-root.log" 2>&1

HERMES_HOME=/root/.hermes/profiles/zeus "$REPO/.venv/bin/python" - <<'PY'
import json,yaml
from gateway.reasoning_router import route_mgs_finance_model
from gateway.run import _get_channel_override,load_gateway_config_for_runner
from gateway.config import Platform
from gateway.session import SessionSource
live=yaml.safe_load(open('/root/.hermes/profiles/zeus/config.yaml'));mirror=yaml.safe_load(open('/root/mgs-agent/profiles/zeus-config.yaml'))
expected={'model':'gpt-6-astra','provider':'openai-codex'}
assert live['discord']['channel_overrides']['1545426987756298340']==expected
assert mirror['discord']['channel_overrides']['1545426987756298340']==expected
cfg=load_gateway_config_for_runner();ov=_get_channel_override(cfg,Platform.DISCORD,'1545426987756298340',thread_id='1545426987756298340',parent_id='1496267442899521627');assert ov and ov.model=='gpt-6-astra' and ov.provider=='openai-codex'
source=SessionSource(platform=Platform.DISCORD,chat_id='1545426987756298340',thread_id='1545426987756298340',chat_type='thread',chat_name='Dashboard financeira MGS')
assert route_mgs_finance_model('confere o fechamento',source=source)==expected
source2=SessionSource(platform=Platform.DISCORD,chat_id='new',thread_id='new',chat_type='thread',chat_name='Projeto')
assert route_mgs_finance_model('revisar a dashboard financeira',source=source2)==expected
assert route_mgs_finance_model('confere o WordPress',source=source2) is None
print('finance_astra_route=PASS')
PY
astra_usage="$EVIDENCE/finalizer-b23-astra-usage.json";astra_out="$EVIDENCE/finalizer-b23-astra-smoke.log";astra_marker=MGS_FINANCE_ASTRA_POST_OK
HERMES_HOME=/root/.hermes/profiles/zeus "$CANONICAL" -z "Respond exactly $astra_marker and nothing else." -m gpt-6-astra --provider openai-codex --usage-file "$astra_usage" >"$astra_out" 2>&1
python3 - "$astra_out" "$astra_usage" "$astra_marker" <<'PY'
import json,sys
text=open(sys.argv[1],errors='replace').read();usage=json.load(open(sys.argv[2]));marker=sys.argv[3];lines=[x.strip() for x in text.splitlines() if x.strip()]
assert text.count(marker)==1 and lines[-1]==marker
assert usage.get('model')=='gpt-6-astra' and usage.get('provider')=='openai-codex'
print('astra_smoke=PASS')
PY

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
     if kl in ('access_token','access') and 'openai-codex' in np:out['access'].add(v)
     if kl in ('refresh_token','refresh') and 'openai-codex' in np:out['refresh'].add(v)
    else:rec(v,np)
  elif isinstance(x,list):
   for v in x:rec(v,path)
 rec(obj);return out
v={p:vals(json.loads(Path(f'/root/.hermes/profiles/{p}/auth.json').read_text())) for p in profiles}
for p in profiles:assert v[p]['access'] and v[p]['refresh']
for i,p in enumerate(profiles):
 for q in profiles[i+1:]:assert not(v[p]['access']&v[q]['access']) and not(v[p]['refresh']&v[q]['refresh'])
print('oauth_independence=PASS')
PY

apt-get update -qq
[[ "$(apt-get -s -o Debug::NoLocking=1 upgrade | grep -c '^Inst ' || true)" == 0 ]]
[[ "$(apt-get -s -o Debug::NoLocking=1 full-upgrade | grep -c '^Inst ' || true)" == 0 ]]
[[ ! -e /var/run/reboot-required ]]
[[ "$(uname -r)" == 6.8.0-139-generic ]]
[[ -z "$(systemctl --failed --no-legend --plain)" ]]

# Exact confirmed cleanup of five inactive verification clones.
[[ "$(sha256sum "$CLEANUP_MANIFEST" | cut -d' ' -f1)" == "$CLEANUP_MANIFEST_SHA" ]]
python3 - "$CLEANUP_MANIFEST" "$CLEANUP_RESULT" "$CLEANUP_AUTH" <<'PY'
import datetime,json,os,pathlib,shutil,stat,subprocess,sys,tempfile
manifest=pathlib.Path(sys.argv[1]);result=pathlib.Path(sys.argv[2]);auth=sys.argv[3];m=json.loads(manifest.read_text());before=os.statvfs('/');before_free=before.f_bavail*before.f_frsize
checks=[]
for t in m['targets']:
 root=pathlib.Path(t['path'])
 assert root.exists() and root.is_dir() and not root.is_symlink() and not os.path.ismount(root)
 st=root.stat();assert st.st_ino==t['root_inode'] and st.st_dev==t['root_device']
 files=dirs=links=logical=allocated=0
 for base,dirnames,filenames in os.walk(root,followlinks=False):
  dirs+=1
  for name in filenames:
   p=pathlib.Path(base)/name;s=p.lstat()
   if stat.S_ISLNK(s.st_mode):links+=1
   elif stat.S_ISREG(s.st_mode):files+=1;logical+=s.st_size;allocated+=s.st_blocks*512
   else:raise RuntimeError('unsupported '+str(p))
  for name in list(dirnames):
   p=pathlib.Path(base)/name
   if p.is_symlink():links+=1;dirnames.remove(name)
 assert (files,dirs,links,logical,allocated)==(t['files'],t['directories'],t['symlinks'],t['logical_bytes'],t['allocated_bytes'])
 assert not subprocess.run(['lsof','-t','+D',str(root)],text=True,capture_output=True).stdout.strip()
 checks.append(str(root))
audit=pathlib.Path('/root/mgs-agent/logs/events-audit.jsonl')
with audit.open('a') as f:f.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':'critical_delete_started','agent':'zeus-b23f31c2-finalizer','authorization_message_id':auth,'manifest':str(manifest),'manifest_sha256':'56cca798e9764fba093f34028c826fab40cee383dbb881a1e0b6c6e9d2b74a7a','targets':len(checks),'bytes':m['totals']['allocated_bytes']})+'\n')
for raw in checks:shutil.rmtree(raw)
assert all(not pathlib.Path(raw).exists() for raw in checks)
after=os.statvfs('/');gain=after.f_bavail*after.f_frsize-before_free
data={'status':'success','authorization_message_id':auth,'manifest_sha256':'56cca798e9764fba093f34028c826fab40cee383dbb881a1e0b6c6e9d2b74a7a','deleted_targets':checks,'targets_absent':len(checks),'authorized_allocated_bytes':m['totals']['allocated_bytes'],'observed_free_gain_bytes':gain,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
fd,tmp=tempfile.mkstemp(dir=result.parent,prefix=result.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,result)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
with audit.open('a') as f:f.write(json.dumps({'timestamp':data['validated_at'],'event':'critical_delete_completed','agent':'zeus-b23f31c2-finalizer','authorization_message_id':auth,'targets_absent':len(checks),'authorized_allocated_bytes':m['totals']['allocated_bytes'],'observed_free_gain_bytes':gain})+'\n')
print(json.dumps(data,sort_keys=True))
PY
for agent in ares atena zeus;do [[ "$(systemctl is-active "$agent-gateway.service")" == active ]];done
[[ "$(readlink -f "$CANONICAL")" == "$REPO/.venv/bin/hermes" ]]
RUNTIME_ACCEPTED=1

# Later upstream work is recorded but does not invalidate the authorized cutoff.
if git -C "$REPO" fetch --quiet origin main --tags;then POST_CUTOFF_COUNT="$(git -C "$REPO" rev-list --count "$EXPECTED_UPSTREAM..origin/main")";fi
bash "$ROOT/scripts/sync-souls.sh"
python3 "$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert --id "$CHECKPOINT_ID" --agent zeus --thread-id "$THREAD_ID" --objective 'Atualizar VPS/Hermes com corte operacional autorizado, reiniciar agentes e tornar Astra obrigatório para dashboard financeira' --state "completed_validated_cutoff: VPS exact packages current, no reboot; Hermes v0.21.3 main cutoff b23f31c2 active via port 97281690; post-cutoff commits=$POST_CUTOFF_COUNT belong to next update; Ares→Atena→Zeus new PIDs, gateway_state code SHA and Discord ready; guard 547+6, regression 322/4, changed-surface 729, config 4/4, auth/smokes 3/3; finance thread 1545426987756298340 and finance-topic router resolve gpt-6-astra; Astra real smoke pass; cleanup 5/5 targets absent" --next-step 'Monitorar normalmente; commits publicados após o corte b23f31c2 são uma nova atualização futura' --source "discord:thread:$THREAD_ID;cutover_auth:$CUTOVER_AUTH;cleanup_auth:$CLEANUP_AUTH;result:$RESULT;cleanup:$CLEANUP_RESULT"
python3 "$ROOT/scripts/mgs-knowledge-control.py" validate

python3 - "$ROOT/data/infra-inventory.json" "$LOG" "$POST_CUTOFF_COUNT" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path(sys.argv[1]);log=sys.argv[2];post=sys.argv[3];data=json.loads(path.read_text());entry={'id':'zeus-vps-hermes-cutoff-b23f31c2-20260919','agent':'zeus','type':'vps_hermes_controlled_update','owner':'Rodolfo Mattei','requested_by':'Rodolfo Mattei','source_thread_id':'1550646583367045221','cutover_confirmation_message_id':'1550910739626332271','cleanup_confirmation_message_id':'1550919292315504671','status':'completed_validated_cutoff','vps':{'apt_upgrade_candidates':0,'apt_full_upgrade_candidates':0,'kernel':'6.8.0-139-generic','reboot_required':False},'hermes_before':'v0.21.3 main 14efb460 + abbba7e0','hermes_target':'origin/main cutoff b23f31c2','hermes_target_sha':'b23f31c2bd4977fa49f493e38816b7e70c666a55','candidate_repo':'/root/.hermes/hermes-agent-stage-main-469296c7-mgs','candidate_port_commit':'97281690c498129887512cfee462b086ee200d04','candidate_patch':'/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-b23f31c2.patch','candidate_patch_sha256':'e7adce639c314c9dd080c2ca19661c59a76937d5f343f1adc8277f1f1d1c4130','backup':'/root/.hermes/secure-backups/vps-maintenance/20260919T155128Z-vps-hermes-update','cutoff_policy':'commits after frozen resumption SHA are a new update cycle','post_cutoff_commits':post,'finance_model_policy':{'thread_id':'1545426987756298340','model':'gpt-6-astra','provider':'openai-codex','topic_router':True},'validation':{'patch_reproduction':'59/59','patch_guard':'547 passed + 6 subtests','regression':'322 passed, 4 skipped','changed_surface':'729 passed','config_profiles':'4/4','auth_profiles':'3/3 independent','one_shot_smokes':'3/3','finance_astra_smoke':'PASS','services':'3/3 active+Discord ready+code SHA'},'cleanup':{'targets_deleted':5,'result':'confirmed update-created verification clones absent','manifest':'/root/mgs-agent/data/hermes-cleanup-manifest-20260919-b23f31c2.json','result_path':'/root/mgs-agent/data/hermes-cleanup-manifest-20260919-b23f31c2-result.json'},'activation_log':log,'report_infra_pending':True,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()};arr=data.setdefault('runtime_artifacts',[]);arr[:]=[x for x in arr if not(isinstance(x,dict) and x.get('id')==entry['id'])];arr.append(entry);fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
print('infra_inventory_readback=PASS')
PY

report_output="$($REPORT_HELPER --action modificada --type 'runtime/script/config/skill/data' --path '/root/.hermes/hermes-agent-stage-main-469296c7-mgs; /root/.local/bin/hermes; /root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-b23f31c2.patch; /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh; /root/.hermes/profiles/zeus/config.yaml; /root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md; /root/mgs-agent/data/agent-checkpoints.json; /root/mgs-agent/data/infra-inventory.json' --reason 'Cutover Hermes no SHA congelado autorizado, reinício integral dos agentes e Astra obrigatório para finanças' --evidence "VPS zero updates/no reboot; cutoff b23f31c2 port 97281690; patch 59/59; guard 547+6; regressão 322/4; superfície 729; config 4/4; auth+smokes 3/3; gateway_state SHA+Discord 3/3; finance Astra route+smoke PASS; cleanup 5/5 absent; post-cutoff commits=$POST_CUTOFF_COUNT")"
REPORT_ID="$(python3 - "$report_output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m:raise SystemExit(1)
print(m.group(1))
PY
)"
discord_readback 1498132022634483894 "$REPORT_ID" '' 1
python3 - "$ROOT/data/infra-inventory.json" "$REPORT_ID" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path(sys.argv[1]);mid=sys.argv[2];data=json.loads(path.read_text());e=next(x for x in data['runtime_artifacts'] if x.get('id')=='zeus-vps-hermes-cutoff-b23f31c2-20260919');e['report_infra_pending']=False;e['report_infra']={'message_id':mid,'channel_id':'1498132022634483894','http_status':200,'readback':True,'content_empty':True,'embed_count':1,'mentions':0};e['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
print('infra_report_readback=PASS')
PY
write_result success "Hermes active at cutoff b23f31c2 port 97281690; post-cutoff commits=$POST_CUTOFF_COUNT; finance Astra policy active; services/smokes/cleanup validated" "$REPORT_ID"
audit hermes_main_b23f31c2_activation_finished "upstream=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD post_cutoff=$POST_CUTOFF_COUNT services=3/3 finance_astra=PASS cleanup=5/5 report=$REPORT_ID"
callback="**Resultado:** sucesso — VPS e Hermes atualizados pelo corte operacional autorizado.\n**VPS:** APT/full-upgrade zerados; kernel 6.8.0-139; sem reboot necessário.\n**Hermes:** versão continua v0.21.3; código ativo \`b23f31c2\` + port MGS \`97281690\`; commits posteriores ao corte ($POST_CUTOFF_COUNT) pertencem ao próximo ciclo.\n**Benefícios:** 3.304 commits upstream/3.889 arquivos desde o runtime anterior, com 2.104 correções e melhorias concentradas em gateways, providers/modelos, sessões/contexto, update, segurança e desempenho; grande parte Desktop/TUI permanece fora do runtime MGS.\n**Validação:** patch 59/59; guard 547+6; regressão 322/4; superfície 729; config 4/4; Codex e smokes 3/3; Ares, Atena e Zeus reiniciados com SHA correto e Discord conectado.\n**Astra financeiro:** confirmado — thread \`1545426987756298340\` e assuntos diretamente relacionados à dashboard financeira agora resolvem em \`gpt-6-astra\`; smoke real passou.\n**Backups:** backup pré-update e runtime anterior preservados para rollback.\n**Limpeza:** 5/5 clones confirmados removidos; o arquivo parcial de 10,97 GB também permanece ausente.\n**Pendência:** nenhuma deste corte.\n**Evidência:** \`$RESULT\`; REPORT-INFRA \`$REPORT_ID\`."
post_callback "$callback"
log 'DONE Hermes main b23f31c2 controlled activation'
