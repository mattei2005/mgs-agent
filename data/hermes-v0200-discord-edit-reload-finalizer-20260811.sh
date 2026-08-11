#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-port-v2026-8-11-c0106e50
HERMES=/root/.local/bin/hermes
EXPECTED_HEAD=6fc69c9d705a41f7b31a200b12a75677857e9a8a
EXPECTED_UPSTREAM=c0106e50e7ecedb3ce34e785d949725dc4e0e457
THREAD_ID=1536567182824308839
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-v0200-discord-edit-reload-${STAMP}.log
LOCK=/run/lock/mgs-hermes-v0200-discord-edit-reload.lock
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
post_thread(){
  local text="$1"
  python3 - "$text" <<'PY' | python3 /root/mgs-agent/scripts/discord-bot-post.py --channel-id 1536567182824308839
import json,sys
print(json.dumps({"content":sys.argv[1]},ensure_ascii=False))
PY
}
fail(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR
  set +e
  log "FAIL rc=$rc line=$line"
  "$ROOT/scripts/send-report-infra-embed.sh" --action modificada --type 'Hermes runtime' --path '/root/.local/bin/hermes; Discord adapter' --reason 'Falha fechada ao recarregar correção pós-update do Hermes.' --evidence "rc=$rc; line=$line; log=$LOG" || true
  post_thread "A recarga final da correção do Hermes falhou de forma fechada. Os serviços continuam sob verificação; evidência: $LOG" || true
  exit "$rc"
}
trap fail ERR

log 'START final corrected-runtime reload'
[[ "$(readlink -f "$HERMES")" == "$REPO/.venv/bin/hermes" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
git -C "$REPO" fetch --quiet origin main:refs/remotes/origin/main
[[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_UPSTREAM" ]]
[[ "$(git -C "$REPO" rev-list --count HEAD..origin/main)" == 0 ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
REPO="$REPO" "$ROOT/scripts/ensure-hermes-local-patches.sh" --check
/root/.local/bin/uv pip check --python "$REPO/.venv/bin/python"

prepared="$(HERMES_BIN="$HERMES" HERMES_REPO="$REPO" "$ROOT/scripts/mgs-gateway-restart-safe.sh" --agents 'ares atena zeus' --reason 'reload-hermes-v0200-discord-partial-edit-fix-20260811')"
reload_script="$(python3 - "$prepared" <<'PY'
import re,sys
m=re.search(r'Prepared detached finalizer only \(no restart executed\): (\S+)',sys.argv[1])
if not m: raise SystemExit(1)
print(m.group(1))
PY
)"
[[ -x "$reload_script" ]]
"$reload_script"

python3 - "$HERMES" "$REPO" <<'PY'
import json,os,pathlib,subprocess,sys,time
h,repo=sys.argv[1:]; env=os.environ.copy(); env.pop('HERMES_HOME',None); env.pop('HERMES_PROFILE',None); env['HOME']='/root'; out={}
for p in ['ares','atena','zeus']:
 svc=f'{p}-gateway.service'; pid=subprocess.check_output(['systemctl','show',svc,'-p','MainPID','--value'],text=True).strip(); cmd=pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'); assert subprocess.check_output(['systemctl','is-active',svc],text=True).strip()=='active'; assert repo in cmd,(p,cmd)
 base=[h,'-p',p]; r=subprocess.run(base+['config','check'],env=env,text=True,capture_output=True,timeout=60); line=next((x for x in (r.stdout+r.stderr).splitlines() if 'Config version:' in x),''); assert r.returncode==0 and 'Config version: 34' in line and '→' not in line,(p,line)
 marker='MGS_V0200_DISCORD_EDIT_FINAL_OK'; r=subprocess.run(base+['-z',f'Return exactly {marker}'],env=env,text=True,capture_output=True,timeout=240); assert r.returncode==0 and r.stdout.strip()==marker,(p,r.returncode,r.stdout[-80:]); out[p]={'pid':int(pid),'runtime':'6fc69c9d','config':'v34','smoke':'PASS'}; print(p,'ready+smoke=PASS')
assert not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip()
path='/root/mgs-agent/data/hermes-v0200-main-activation-result.json'; d=json.load(open(path)); d.update({'status':'success','detail':'Hermes 0.20.0 active; validator false-positive and py-cord PartialMessage suppress incompatibility corrected; zero upstream commits pending','validated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'port_commit':'6fc69c9d705a41f7b31a200b12a75677857e9a8a','services':out,'gateway_order':['ares','atena','zeus'],'config_auth_smokes':'final 3/3 gateway profiles PASS; pre/post root 4/4 PASS','upstream_behind':0,'mgs_ahead':1,'repo_clean':True,'failed_units':0,'discord_partial_edit_fix':'py-cord 2.7 PartialMessage flags path validated and loaded'})
open(path,'w').write(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
PY

python3 - <<'PY'
import datetime,json,pathlib
now=datetime.datetime.now(datetime.timezone.utc).isoformat(); p=pathlib.Path('/root/mgs-agent/data/infra-inventory.json'); d=json.load(p.open()); x=next(i for i in d['runtime_artifacts'] if i.get('id')=='hermes-port-main-c0106e50-20260811'); x.update({'status':'activated_validated','candidate_commit':'6fc69c9d705a41f7b31a200b12a75677857e9a8a','patch_sha256':'4ad3c0c41fd66f46c8b4883a53f78da8ec5ff3820ae9fb83160a60864492016a','patch_scope_files':44,'updated_at':now,'validated_at':now}); x.setdefault('validation',{}).update({'mgs_guard':'454 passed + 6 subtests','discord_partial_edit_pycord27':'unit 10/10 + real flags payload=4 + corrected runtime loaded by 3/3 gateways','git':'behind=0 ahead=1 MGS clean'}); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
with pathlib.Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f: f.write(json.dumps({'ts':now,'event':'hermes_v0200_discord_partial_edit_fix_loaded','actor':'Zeus','target_upstream':'c0106e50e7ecedb3ce34e785d949725dc4e0e457','port_commit':'6fc69c9d705a41f7b31a200b12a75677857e9a8a','services':'3/3 ready','smokes':'3/3 PASS','behind':0,'secrets_exposed':False})+'\n')
PY
"$ROOT/scripts/infra-discovery.sh" >/dev/null
"$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert --id hermes-v0200-activation-20260811 --agent zeus --thread-id "$THREAD_ID" --objective 'Atualizar Hermes integralmente e revisar limpeza conservadora da VPS' --state completed --next-step 'Revisar com Rodolfo o manifesto de limpeza; nenhuma exclusão foi feita' --source "discord:$THREAD_ID" >/dev/null
"$ROOT/scripts/mgs-knowledge-control.py" validate >/dev/null
"$ROOT/scripts/send-report-infra-embed.sh" --action modificada --type 'Hermes runtime/config/inventory' --path '/root/.local/bin/hermes; Hermes 0.20 runtime; Discord adapter; infra inventory' --reason 'Hermes 0.20.0 concluído no main atual; validador e compatibilidade py-cord PartialMessage corrigidos.' --evidence "upstream=$EXPECTED_UPSTREAM; port=$EXPECTED_HEAD; pending=0; guard=454+6; services=3/3; smokes=3/3; failed_units=0; log=$LOG"
post_thread "Retorno final: Hermes 0.20.0 concluído no upstream c0106e50, port MGS 6fc69c9d e zero commits pendentes. Corrigi também o falso positivo do validador e a incompatibilidade de edição do py-cord encontrada após o corte. Ares, Atena e Zeus carregaram a correção e passaram prontidão e smokes. Auditoria de limpeza pronta; nenhuma exclusão foi feita."
log 'DONE final corrected-runtime reload'
