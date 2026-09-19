#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-stage-main-005c746d-ctx872-mgs
OLD_REPO=/root/.hermes/hermes-agent-stage-main-005c746d-mgs
NEW_LAUNCHER=/root/.local/bin/hermes-main-005c746d-ctx872-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-main-005c746d-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_HEAD=a92d09625933bb1859b7a615e8e9fc34a0045700
EXPECTED_CONFIG_SHA=44fce6ca93a2651e944756d02ee7f0b23b546758cbb3162a888fa4dd736c84d3
EXPECTED_SKILL_SHA=20d1e952c078a16318593fba8ef2ccdb4654097d5c136772812136a7d935570b
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch
PATCH_SHA=efb1367437cade5411cda5e82fcc67a12fe6cf95fe4cc7c9059d31f1b97f907c
CONFIG=/root/.hermes/profiles/zeus/config.yaml
CONFIG_MIRROR=$ROOT/profiles/zeus-config.yaml
SKILL=/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md
SKILL_MIRROR=$ROOT/profiles/zeus-skills/ops/mgs-finance-dashboard/SKILL.md
BACKUP=/root/.hermes/secure-backups/vps-maintenance/20260919T-context872
SAFE_RESTART=$ROOT/scripts/mgs-gateway-restart-safe.sh
REPORT_HELPER=$ROOT/scripts/send-report-infra-embed.sh
DISCORD_POST=$ROOT/scripts/discord-bot-post.py
THREAD_ID=1550646583367045221
AUTH_ID=1550942971023593605
CHECKPOINT_ID=ZEUS-HERMES-CODEX-CTX872-20260919
RESULT=$ROOT/data/hermes-codex-context872-result.json
LOCK=/run/lock/mgs-hermes-context872.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-codex-context872-${STAMP}.log
SWITCHED=0
RUNTIME_ACCEPTED=0
ROLLBACK_DONE=0
REPORT_ID=""

mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$1" "$2" <<'PY'
import datetime,json,sys
with open('/root/mgs-agent/logs/events-audit.jsonl','a') as f:
 f.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':sys.argv[1],'agent':'zeus-context872-finalizer','detail':sys.argv[2]},ensure_ascii=False)+'\n')
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
  output="$(HERMES_BIN="$CANONICAL" HERMES_REPO="$repo" "$SAFE_RESTART" --agents 'ares atena zeus' --reason "$reason" --delay 20)"
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
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
token=os.environ.get('DISCORD_BOT_TOKEN');assert token
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{message_id}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
assert str(data.get('channel_id'))==channel and data.get('content','')==expected_content
assert len(data.get('embeds') or [])==(1 if expect_embed=='1' else 0)
assert not (data.get('mentions') or [])
print('discord_readback=PASS')
PY
}
post_callback(){
  local content="$1" output message_id
  output="$(python3 - "$content" <<'PY' | "$DISCORD_POST" --channel-id "$THREAD_ID"
import json,sys
print(json.dumps({'content':sys.argv[1],'allowed_mentions':{'parse':[]}},ensure_ascii=False))
PY
)"
  message_id="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m:raise SystemExit(1)
print(m.group(1))
PY
)"
  discord_readback "$THREAD_ID" "$message_id" "$content" 0
}
restore_file(){
  local source="$1" target="$2"
  python3 - "$source" "$target" <<'PY'
import os,pathlib,shutil,sys,tempfile
src=pathlib.Path(sys.argv[1]);dst=pathlib.Path(sys.argv[2]);fd,tmp=tempfile.mkstemp(dir=dst.parent,prefix=dst.name+'.',suffix='.tmp')
os.close(fd)
try:
 shutil.copy2(src,tmp);os.replace(tmp,dst)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
}
write_result(){
  local status="$1" detail="$2" report_id="${3:-}"
  python3 - "$RESULT" "$status" "$detail" "$LOG" "$report_id" <<'PY'
import datetime,json,os,pathlib,subprocess,sys,tempfile
path=pathlib.Path(sys.argv[1]);status,detail,log,report_id=sys.argv[2:]
def show(unit,key):return subprocess.run(['systemctl','show',unit,'-p',key,'--value'],text=True,capture_output=True).stdout.strip()
data={'status':status,'detail':detail,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'effective_context':{'gpt-5.6-sol-900k':872000,'gpt-6-astra-900k':872000},'catalog_base_context':272000,'catalog_max_context':872000,'runtime_head':'a92d09625933bb1859b7a615e8e9fc34a0045700','patch_sha256':'efb1367437cade5411cda5e82fcc67a12fe6cf95fe4cc7c9059d31f1b97f907c','config_sha256':'44fce6ca93a2651e944756d02ee7f0b23b546758cbb3162a888fa4dd736c84d3','restart_order':['ares','atena','zeus'],'services':{a:{'active':show(a+'-gateway.service','ActiveState'),'sub':show(a+'-gateway.service','SubState'),'pid':show(a+'-gateway.service','MainPID'),'exec_status':show(a+'-gateway.service','ExecMainStatus')} for a in ('ares','atena','zeus')},'activation_log':log,'report_infra_message_id':report_id}
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
  log "FAIL rc=$rc line=$line switched=$SWITCHED accepted=$RUNTIME_ACCEPTED"
  audit hermes_codex_context872_failed "rc=$rc line=$line switched=$SWITCHED accepted=$RUNTIME_ACCEPTED log=$LOG"
  if [[ "$SWITCHED" == 1 && "$RUNTIME_ACCEPTED" == 0 ]];then
    restore_file "$BACKUP/config.yaml" "$CONFIG"
    restore_file "$BACKUP/mgs-finance-dashboard.SKILL.pre-872.md" "$SKILL"
    bash "$ROOT/scripts/sync-souls.sh" || true
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_run_restart rollback-hermes-context872 "$OLD_REPO";then ROLLBACK_DONE=1;fi
  fi
  write_result failed "rc=$rc line=$line rollback_done=$ROLLBACK_DONE" "$REPORT_ID" || true
  post_callback $'**Resultado:** falha ao ativar o contexto estendido.\n- O rollback automático foi executado quando necessário.\n- Nenhuma capacidade acima do limite confirmado foi mantida.\n- Evidência: `'$LOG'`.' || true
  exit "$rc"
}
trap on_error ERR

log 'START context 872K activation'
audit hermes_codex_context872_started "authorization=$AUTH_ID target=$EXPECTED_HEAD order=ares,atena,zeus"
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$OLD_LAUNCHER")" ]]
[[ "$(readlink -f "$NEW_LAUNCHER")" == "$REPO/.venv/bin/hermes" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == "$PATCH_SHA" ]]
[[ "$(sha256sum "$CONFIG" | cut -d' ' -f1)" == "$EXPECTED_CONFIG_SHA" ]]
[[ "$(sha256sum "$CONFIG_MIRROR" | cut -d' ' -f1)" == "$EXPECTED_CONFIG_SHA" ]]
[[ "$(sha256sum "$SKILL" | cut -d' ' -f1)" == "$EXPECTED_SKILL_SHA" ]]
[[ "$(sha256sum "$SKILL_MIRROR" | cut -d' ' -f1)" == "$EXPECTED_SKILL_SHA" ]]
/root/.local/bin/uv pip check --python "$REPO/.venv/bin/python"
REPO="$REPO" PYBIN="$REPO/.venv/bin/python" "$ROOT/scripts/ensure-hermes-mgs-patches.sh"

before_pids="$(for a in ares atena zeus;do systemctl show "$a-gateway.service" -p MainPID --value;done | paste -sd, -)"
atomic_launcher "$NEW_LAUNCHER"
SWITCHED=1
prepare_and_run_restart hermes-codex-context872 "$REPO"

python3 - "$EXPECTED_HEAD" "$before_pids" <<'PY'
import json,pathlib,subprocess,sys
expected=sys.argv[1];old=sys.argv[2].split(',')
for i,a in enumerate(('ares','atena','zeus')):
 unit=a+'-gateway.service'
 show=lambda k:subprocess.run(['systemctl','show',unit,'-p',k,'--value'],text=True,capture_output=True).stdout.strip()
 assert show('ActiveState')=='active' and show('SubState')=='running' and show('ExecMainStatus')=='0'
 assert show('MainPID') and show('MainPID')!=old[i]
 state=json.loads(pathlib.Path(f'/root/.hermes/profiles/{a}/gateway_state.json').read_text())
 assert state.get('code_sha')==expected
 assert state.get('gateway_state')=='running'
 assert (state.get('platforms',{}).get('discord',{}).get('state'))=='connected'
print('post_restart_services=PASS')
PY

HERMES_HOME=/root/.hermes/profiles/zeus "$CANONICAL" -z 'Reply with exactly SOL_872_POST_OK' -m gpt-5.6-sol-900k --provider openai-codex --reasoning low --ignore-rules --usage-file "$BACKUP/sol-872-post-usage.json" > "$BACKUP/sol-872-post.log" 2>&1
HERMES_HOME=/root/.hermes/profiles/zeus "$CANONICAL" -z 'Reply with exactly ASTRA_872_POST_OK' -m gpt-6-astra-900k --provider openai-codex --reasoning low --ignore-rules --usage-file "$BACKUP/astra-872-post-usage.json" > "$BACKUP/astra-872-post.log" 2>&1
python3 - <<'PY'
import json,pathlib
for marker,name in [('SOL_872_POST_OK','sol'),('ASTRA_872_POST_OK','astra')]:
 text=pathlib.Path(f'/root/.hermes/secure-backups/vps-maintenance/20260919T-context872/{name}-872-post.log').read_text(errors='replace')
 usage=json.loads(pathlib.Path(f'/root/.hermes/secure-backups/vps-maintenance/20260919T-context872/{name}-872-post-usage.json').read_text())
 assert [x.strip() for x in text.splitlines() if x.strip()][-1]==marker
 assert usage.get('provider')=='openai-codex' and usage.get('api_calls')==1
print('post_restart_smokes=PASS')
PY
HERMES_HOME=/root/.hermes/profiles/zeus "$REPO/.venv/bin/python" - <<'PY'
import json,yaml
from agent.auxiliary_client import _read_codex_access_token
from agent.model_metadata import get_model_context_length,_codex_oauth_context_cache
cfg=yaml.safe_load(open('/root/.hermes/profiles/zeus/config.yaml'));assert 'context_length' not in cfg['model']
t=_read_codex_access_token();assert t
_codex_oauth_context_cache.clear()
kwargs={'base_url':cfg['model']['base_url'],'api_key':t,'provider':'openai-codex'}
assert get_model_context_length('gpt-5.6-sol-900k',**kwargs)==872000
assert get_model_context_length('gpt-6-astra-900k',**kwargs)==872000
assert cfg['discord']['channel_overrides']['1545426987756298340']=={'model':'gpt-6-astra-900k','provider':'openai-codex'}
print('context_872_readback=PASS')
PY
RUNTIME_ACCEPTED=1

python3 "$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert --id "$CHECKPOINT_ID" --agent zeus --thread-id "$THREAD_ID" --objective 'Aplicar o máximo real permitido pela assinatura Codex Pro para Sol e Astra, usando o catálogo autenticado e mantendo rollback.' --state 'completed_validated: catálogo autenticado e runtime ativo resolvem Sol e Astra estendidos em 872000; override global 1050000 removido; finanças roteadas a gpt-6-astra-900k; Ares→Atena→Zeus reiniciados e conectados.' --next-step 'Monitorar normalmente; o alias histórico -900k permanece no nome, mas o valor efetivo é limitado pelo catálogo autenticado a 872000.' --source "discord:thread:$THREAD_ID;authorization:$AUTH_ID;result:$RESULT"
python3 "$ROOT/scripts/mgs-knowledge-control.py" validate

python3 - "$LOG" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path('/root/mgs-agent/data/infra-inventory.json');data=json.loads(path.read_text());items=data.setdefault('runtime_artifacts',[])
entry={'id':'zeus-hermes-codex-context872-20260919','agent':'zeus','type':'hermes_runtime_config','owner':'Rodolfo Mattei','source_thread_id':'1550646583367045221','authorization_message_id':'1550942971023593605','status':'completed_validated','runtime_repo':'/root/.hermes/hermes-agent-stage-main-005c746d-ctx872-mgs','runtime_head':'a92d09625933bb1859b7a615e8e9fc34a0045700','upstream_backport':'223aed6199bd19698f4854d9f0c0ec8ae33b0306','effective_context':{'gpt-5.6-sol-900k':872000,'gpt-6-astra-900k':872000},'catalog':{'context_window':272000,'max_context_window':872000},'finance_thread_id':'1545426987756298340','patch':'/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch','patch_sha256':'efb1367437cade5411cda5e82fcc67a12fe6cf95fe4cc7c9059d31f1b97f907c','validation':{'guard':'547 passed + 6 subtests','changed_surface':'1159 passed','real_smokes':'Sol 1/1; Astra 1/1','services':'3/3 active, new PID, Discord connected, code SHA exact'},'backup':'/root/.hermes/secure-backups/vps-maintenance/20260919T-context872','activation_log':sys.argv[1],'report_infra_pending':True,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
items[:]=[x for x in items if x.get('id')!=entry['id']];items.append(entry)
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
print('inventory=PASS')
PY

report_output="$($REPORT_HELPER --action modificada --type 'runtime/config/skill/data' --path '/root/.hermes/hermes-agent-stage-main-005c746d-ctx872-mgs; /root/.local/bin/hermes; /root/.hermes/profiles/zeus/config.yaml; /root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md; /root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-09-19-main-005c746d.patch; /root/mgs-agent/data/agent-checkpoints.json; /root/mgs-agent/data/infra-inventory.json' --reason 'Aplicar o máximo real da assinatura Codex Pro para Sol e Astra e corrigir o alias histórico de 900k pelo teto autenticado de 872k' --evidence 'runtime a92d096259; upstream backport 223aed6199; catálogo base 272k/max 872k; Sol e Astra 872k; guard 547+6; superfície 1159/0; smokes 2/2; serviços 3/3 com SHA e Discord')"
REPORT_ID="$(python3 - "$report_output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);
if not m:raise SystemExit(1)
print(m.group(1))
PY
)"
discord_readback 1498132022634483894 "$REPORT_ID" '' 1
python3 - "$REPORT_ID" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
path=pathlib.Path('/root/mgs-agent/data/infra-inventory.json');data=json.loads(path.read_text());e=next(x for x in data['runtime_artifacts'] if x.get('id')=='zeus-hermes-codex-context872-20260919');e['report_infra_pending']=False;e['report_infra']={'message_id':sys.argv[1],'channel_id':'1498132022634483894','readback':True,'content_empty':True,'embed_count':1,'mentions':0};e['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
write_result success 'Sol e Astra no máximo autenticado de 872000; serviços e smokes validados' "$REPORT_ID"
audit hermes_codex_context872_finished "head=$EXPECTED_HEAD services=3/3 context=872000 report=$REPORT_ID"
callback=$'**Concluído:** Sol e Astra estão no máximo permitido pela assinatura mensal.\n- **Sol:** 872.000 tokens efetivos.\n- **Astra financeiro:** 872.000 tokens efetivos.\n- O alias continua escrito como `-900k`, mas agora obedece ao teto real de 872k informado pelo catálogo da sua conta.\n- O override incorreto de 1.050.000 foi removido.\n- Ares, Atena e Zeus foram reiniciados; 3/3 ativos e conectados.\n- Validação: 1.159 testes, guard 547+6 e smokes reais dos dois modelos, tudo aprovado.\n- REPORT-INFRA: `'$REPORT_ID'`.'
post_callback "$callback"
log 'DONE context 872K activation'
