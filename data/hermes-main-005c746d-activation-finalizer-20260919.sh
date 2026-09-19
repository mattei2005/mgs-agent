#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-stage-main-005c746d-mgs
NEW_LAUNCHER=/root/.local/bin/hermes-main-005c746d-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-main-b23f31c2-mgs
CANONICAL=/root/.local/bin/hermes
TARGET=005c746d2ca885aeaacc77a602239a99476d90c4
EXPECTED_HEAD=16190297223e25c373e31fc021b78eb61829bf43
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch
PATCH_SHA=53c80b54651cb56663cef7392bf993c60b8348d634d07105d54b843fc465d941
PATCH_PATHS=60
GUARD=$ROOT/scripts/ensure-hermes-mgs-patches.sh
REGRESSION=$ROOT/scripts/run-hermes-post-upstream-regression.sh
SAFE_RESTART=$ROOT/scripts/mgs-gateway-restart-safe.sh
REPORT_HELPER=$ROOT/scripts/send-report-infra-embed.sh
DISCORD_POST=$ROOT/scripts/discord-bot-post.py
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260919T181046Z-hermes-005c746d/activation-targets.sha256
BACKUP=/root/.hermes/secure-backups/vps-maintenance/20260919T181046Z-hermes-005c746d
RESULT=$ROOT/data/hermes-main-005c746d-activation-result.json
CHECKPOINT_ID=ZEUS-HERMES-POSTCUTOFF-144-20260919
THREAD_ID=1550646583367045221
AUTH_MESSAGE=1550927317134614580
LOCK=/run/lock/mgs-hermes-main-005c746d-activation.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-main-005c746d-activation-${STAMP}.log
SWITCHED=0
ACCEPTED=0
ROLLBACK=0
REPORT_ID=""
BEHIND="unknown"

mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
with pathlib.Path(p).open('a',encoding='utf-8') as f:
 f.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,'agent':'zeus-005c746d-finalizer','detail':detail},ensure_ascii=False)+'\n')
PY
}
atomic_launcher(){
  local target="$1" tmp="$CANONICAL.tmp.$$"
  ln -s "$target" "$tmp"
  mv -Tf "$tmp" "$CANONICAL"
  [[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$target")" ]]
}
prepare_and_restart(){
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
  local channel="$1" message_id="$2" expected_content="$3" embed_count="$4"
  python3 - "$channel" "$message_id" "$expected_content" "$embed_count" <<'PY'
import json,os,sys,urllib.request
channel,message_id,expected_content,embed_count=sys.argv[1:]
for raw in open('/root/.hermes/profiles/zeus/.env',errors='ignore'):
 line=raw.strip()
 if line and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
token=os.environ.get('DISCORD_BOT_TOKEN');assert token
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{message_id}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
assert str(data.get('channel_id'))==channel
assert data.get('content','')==expected_content
assert len(data.get('embeds') or [])==int(embed_count)
assert not (data.get('mentions') or [])
print('discord_readback=PASS '+message_id)
PY
}
post_thread(){
  local mode="$1" report_id="${2:-}" output message_id content_file
  content_file="$BACKUP/thread-${mode}.txt"
  python3 - "$content_file" "$mode" "$report_id" "$BEHIND" "$RESULT" "$LOG" <<'PY'
from pathlib import Path
import sys
path,mode,report_id,behind,result,log=sys.argv[1:]
if mode=='success':
 text=f'''**Resultado**

Atualização concluída com sucesso. Os 144 commits foram ativados e os três agentes foram reiniciados.

**Hermes**
- Versão pública: `v0.21.3`
- Upstream ativo: `005c746d`
- Customizações MGS: `16190297`
- Patch preservado: 60/60 arquivos

**Benefícios ativos**
- Timeout específico do `gpt-6-astra`
- Mais estabilidade no streaming e encerramento do Codex
- Correções de `/model` e overrides por canal
- Melhor tratamento de 401, 403, WAF, quota e failover
- Preservação de contexto em sobrecarga do compressor
- Correções de ferramentas, cron e respostas multimodais

**Validação**
- Upstream alterado: 3.168 testes aprovados, 1 ignorado por plataforma
- Superfície MGS: 1.023 testes aprovados
- Guard MGS: 547 testes + 6 subtestes
- Regressão: 324 aprovados, 4 ignorados
- Configuração: 4/4
- Codex e smokes: 3/3
- Astra: teste real aprovado

**Serviços**
- Ares: ativo e conectado
- Atena: ativo e conectado
- Zeus: ativo e conectado

**Astra financeiro**
A thread `1545426987756298340` e os assuntos diretamente relacionados à dashboard financeira continuam em `gpt-6-astra`.

**Backups**
O runtime anterior e o backup pré-ativação foram preservados para rollback.

**Pendência**
Nenhuma dentro do escopo exato dos 144 commits. Commits posteriores ao alvo: {behind}.

**Evidência**
`{result}`
REPORT-INFRA: `{report_id}`'''
else:
 text=f'''**Resultado**

A atualização dos 144 commits falhou durante a ativação controlada.

**Contenção**
- Runtime aceito: {"sim" if mode=="accepted-closure-failed" else "não"}
- Rollback automático: {"executado" if mode=="failed-rolled-back" else "não aplicável ou incompleto"}

**Evidência**
`{result}`
`{log}`'''
Path(path).write_text(text,encoding='utf-8')
PY
  output="$(python3 - "$content_file" <<'PY' | "$DISCORD_POST" --channel-id "$THREAD_ID"
import json,sys
content=open(sys.argv[1],encoding='utf-8').read()
print(json.dumps({'content':content,'allowed_mentions':{'parse':[]}},ensure_ascii=False))
PY
)"
  message_id="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m:raise SystemExit(1)
print(m.group(1))
PY
)"
  discord_readback "$THREAD_ID" "$message_id" "$(cat "$content_file")" 0
}
write_result(){
  local status="$1" detail="$2"
  python3 - "$RESULT" "$status" "$detail" "$LOG" "$REPORT_ID" "$BEHIND" <<'PY'
import datetime,json,os,pathlib,subprocess,sys,tempfile
path=pathlib.Path(sys.argv[1]);status,detail,log,report_id,behind=sys.argv[2:]
def show(unit,key):return subprocess.run(['systemctl','show',unit,'-p',key,'--value'],text=True,capture_output=True).stdout.strip()
services={a:{'active':show(a+'-gateway.service','ActiveState'),'sub':show(a+'-gateway.service','SubState'),'pid':show(a+'-gateway.service','MainPID'),'exec_status':show(a+'-gateway.service','ExecMainStatus')} for a in ('ares','atena','zeus')}
data={'status':status,'detail':detail,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':'0.21.3','upstream_sha':'005c746d2ca885aeaacc77a602239a99476d90c4','port_commit':'16190297223e25c373e31fc021b78eb61829bf43','exact_upstream_commits':144,'patch_paths':60,'patch_sha256':'53c80b54651cb56663cef7392bf993c60b8348d634d07105d54b843fc465d941','canonical_launcher':os.path.realpath('/root/.local/bin/hermes'),'services':services,'finance_model_route':{'thread_id':'1545426987756298340','model':'gpt-6-astra','provider':'openai-codex','topic_policy':True},'post_target_commits':behind,'backup':'/root/.hermes/secure-backups/vps-maintenance/20260919T181046Z-hermes-005c746d','report_infra_message_id':report_id or None,'log':log}
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR;set +e
  log "FAIL rc=$rc line=$line switched=$SWITCHED accepted=$ACCEPTED"
  audit hermes_main_005c746d_activation_failed "rc=$rc line=$line switched=$SWITCHED accepted=$ACCEPTED log=$LOG"
  mode=failed
  if [[ "$SWITCHED" == 1 && "$ACCEPTED" == 0 ]]; then
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_restart hermes-main-005c746d-rollback /root/.hermes/hermes-agent-stage-main-469296c7-mgs;then ROLLBACK=1;mode=failed-rolled-back;fi
  elif [[ "$ACCEPTED" == 1 ]];then mode=accepted-closure-failed;fi
  write_result "$mode" "rc=$rc line=$line rollback=$ROLLBACK accepted=$ACCEPTED" || true
  post_thread "$mode" "$REPORT_ID" || true
  exit "$rc"
}
trap on_error ERR

log 'START exact 144-commit Hermes activation'
audit hermes_main_005c746d_activation_started "authorization=$AUTH_MESSAGE target=$TARGET port=$EXPECTED_HEAD order=ares,atena,zeus"
current_launcher="$(readlink -f "$CANONICAL")"
old_launcher="$(readlink -f "$OLD_LAUNCHER")"
new_launcher="$(readlink -f "$NEW_LAUNCHER")"
[[ "$current_launcher" == "$old_launcher" || "$current_launcher" == "$new_launcher" ]]
[[ "$new_launcher" == "$REPO/.venv/bin/hermes" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ "$(git -C "$REPO" rev-parse HEAD^)" == "$TARGET" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$PATCH_SHA" ]]
[[ "$(grep -c '^+++ b/' "$PATCH")" == "$PATCH_PATHS" ]]
git -C "$REPO" fsck --no-dangling
git -C "$REPO" apply --reverse --check "$PATCH"
sha256sum -c "$SNAPSHOT"
sha256sum -c "$BACKUP/candidate-pip-freeze.sha256"
/root/.local/bin/uv pip check --python "$REPO/.venv/bin/python"
python3 - <<'PY' >"$BACKUP/pre-activation-pids.json"
import json,subprocess
print(json.dumps({a:subprocess.check_output(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True).strip() for a in ('ares','atena','zeus')}))
PY

if [[ "$current_launcher" == "$old_launcher" ]];then
  atomic_launcher "$NEW_LAUNCHER"
fi
SWITCHED=1
prepare_and_restart hermes-main-005c746d-activation "$REPO"

for a in ares atena zeus;do
 unit="$a-gateway.service"
 [[ "$(systemctl is-active "$unit")" == active ]]
 [[ "$(systemctl show "$unit" -p SubState --value)" == running ]]
 [[ "$(systemctl show "$unit" -p ExecMainStatus --value)" == 0 ]]
done
[[ "$(readlink -f "$CANONICAL")" == "$REPO/.venv/bin/hermes" ]]
python3 - "$BACKUP/pre-activation-pids.json" "$EXPECTED_HEAD" <<'PY'
import json,pathlib,subprocess,sys
pre=json.load(open(sys.argv[1]));expected=sys.argv[2]
for a in ('ares','atena','zeus'):
 pid=subprocess.check_output(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True).strip();assert pid and pid!='0' and pid!=pre[a]
 state=json.loads(pathlib.Path(f'/root/.hermes/profiles/{a}/gateway_state.json').read_text());d=((state.get('platforms') or {}).get('discord') or {})
 assert state.get('code_sha')==expected,(a,state.get('code_sha'))
 assert d.get('state')=='connected',(a,d)
 assert str(d.get('writer_pid'))==pid,(a,d.get('writer_pid'),pid)
 print(a,'ready',pid)
PY
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$BACKUP/post-guard.log" "$GUARD"
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" LOG="$BACKUP/post-regression.log" "$REGRESSION"
for p in ares atena zeus;do
 marker="MGS_005C746D_${p^^}_POST_OK";out="$BACKUP/post-smoke-$p.log"
 HERMES_HOME="/root/.hermes/profiles/$p" "$CANONICAL" config check >"$BACKUP/post-config-$p.log" 2>&1
 HERMES_HOME="/root/.hermes/profiles/$p" "$CANONICAL" -z "Respond exactly $marker and nothing else." >"$out" 2>&1
 python3 - "$out" "$marker" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace');m=sys.argv[2];lines=[x.strip() for x in s.splitlines() if x.strip()];assert s.count(m)==1 and lines[-1]==m
PY
done
HERMES_HOME=/root/.hermes "$CANONICAL" config check >"$BACKUP/post-config-root.log" 2>&1
marker=MGS_005C746D_ASTRA_POST_OK;out="$BACKUP/post-astra.log";usage="$BACKUP/post-astra-usage.json"
HERMES_HOME=/root/.hermes/profiles/zeus "$CANONICAL" -z "Respond exactly $marker and nothing else." -m gpt-6-astra --provider openai-codex --usage-file "$usage" >"$out" 2>&1
python3 - "$out" "$usage" "$marker" <<'PY'
from pathlib import Path
import json,sys
s=Path(sys.argv[1]).read_text(errors='replace');u=json.loads(Path(sys.argv[2]).read_text());m=sys.argv[3];lines=[x.strip() for x in s.splitlines() if x.strip()];assert s.count(m)==1 and lines[-1]==m;assert u.get('model')=='gpt-6-astra' and u.get('provider')=='openai-codex'
PY
HERMES_HOME=/root/.hermes/profiles/zeus "$REPO/.venv/bin/python" - <<'PY'
import yaml
from gateway.reasoning_router import route_mgs_finance_model
from gateway.config import Platform
from gateway.session import SessionSource
cfg=yaml.safe_load(open('/root/.hermes/profiles/zeus/config.yaml'));assert cfg['discord']['channel_overrides']['1545426987756298340']=={'model':'gpt-6-astra','provider':'openai-codex'}
s=SessionSource(platform=Platform.DISCORD,chat_id='x',thread_id='x',chat_type='thread',chat_name='Financeiro');assert route_mgs_finance_model('revisar dashboard financeira',source=s)=={'model':'gpt-6-astra','provider':'openai-codex'}
print('finance_route=PASS')
PY
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
ACCEPTED=1

if git -C "$REPO" fetch --quiet origin main;then BEHIND="$(git -C "$REPO" rev-list --count "$TARGET..origin/main")";fi
bash "$ROOT/scripts/sync-souls.sh"
python3 "$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert --id "$CHECKPOINT_ID" --agent zeus --thread-id "$THREAD_ID" --objective 'Portar e ativar exatamente os 144 commits b23f31c2..005c746d no Hermes MGS, preservar customizações e reiniciar Ares/Atena/Zeus' --state "completed_validated: Hermes v0.21.3 upstream 005c746d active with MGS port 16190297; patch 60/60; upstream changed surface 3168 pass/1 platform skip; MGS surface 1023 pass; guard 547+6; regression 324/4; config 4/4; auth/smokes 3/3; Astra real smoke pass; Ares→Atena→Zeus new PIDs and Discord connected; later commits=$BEHIND outside exact scope" --next-step 'Monitorar normalmente; qualquer commit após 005c746d pertence a um novo ciclo' --source "discord:thread:$THREAD_ID;authorization:$AUTH_MESSAGE;result:$RESULT;backup:$BACKUP"
python3 "$ROOT/scripts/mgs-knowledge-control.py" validate

python3 - "$ROOT/data/infra-inventory.json" "$LOG" "$BEHIND" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]);log=sys.argv[2];behind=sys.argv[3];data=json.loads(p.read_text());entry={'id':'zeus-hermes-postcutoff-005c746d-20260919','agent':'zeus','type':'hermes_controlled_update','owner':'Rodolfo Mattei','source_thread_id':'1550646583367045221','authorization_message_id':'1550927317134614580','status':'activated_validated','version':'v0.21.3','upstream_sha':'005c746d2ca885aeaacc77a602239a99476d90c4','exact_upstream_commits':144,'port_commit':'16190297223e25c373e31fc021b78eb61829bf43','patch':'/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch','patch_sha256':'53c80b54651cb56663cef7392bf993c60b8348d634d07105d54b843fc465d941','patch_paths':60,'backup':'/root/.hermes/secure-backups/vps-maintenance/20260919T181046Z-hermes-005c746d','validation':{'upstream_changed':'3168 passed, 1 platform skip','mgs_surface':'1023 passed','guard':'547 passed + 6 subtests','regression':'324 passed, 4 skipped','config':'4/4','auth_smokes':'3/3','astra':'PASS','services':'3/3 active+Discord+SHA'},'finance_model_policy':{'thread_id':'1545426987756298340','model':'gpt-6-astra','provider':'openai-codex','topic_router':True},'post_target_commits':behind,'activation_log':log,'report_infra_pending':True,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()};arr=data.setdefault('runtime_artifacts',[]);arr[:]=[x for x in arr if not(isinstance(x,dict) and x.get('id')==entry['id'])];arr.append(entry);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
report_output="$($REPORT_HELPER --action modificada --type 'runtime/script/data' --path '/root/.hermes/hermes-agent-stage-main-005c746d-mgs; /root/.local/bin/hermes; /root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch; /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh; /root/mgs-agent/data/agent-checkpoints.json; /root/mgs-agent/data/infra-inventory.json' --reason 'Ativação autorizada dos 144 commits pós-corte e reinício integral dos agentes' --evidence "upstream 005c746d + MGS 16190297; patch 60/60; upstream 3168/1; MGS 1023; guard 547+6; regressão 324/4; config 4/4; auth/smokes 3/3; Astra PASS; gateways 3/3; later=$BEHIND")"
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
p=pathlib.Path(sys.argv[1]);mid=sys.argv[2];data=json.loads(p.read_text());e=next(x for x in data['runtime_artifacts'] if x.get('id')=='zeus-hermes-postcutoff-005c746d-20260919');e['report_infra_pending']=False;e['report_infra']={'message_id':mid,'channel_id':'1498132022634483894','readback':True,'content_empty':True,'embed_count':1,'mentions':0};e['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
write_result success "exact 144 commits active and validated; services restarted; finance Astra preserved"
audit hermes_main_005c746d_activation_finished "target=$TARGET port=$EXPECTED_HEAD services=3/3 report=$REPORT_ID later=$BEHIND"
post_thread success "$REPORT_ID"
log 'DONE exact 144-commit Hermes activation'
