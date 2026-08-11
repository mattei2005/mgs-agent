#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/root/mgs-agent
REPO=/root/.hermes/hermes-agent-port-v2026-8-11-c0106e50
NEW_LAUNCHER=/root/.local/bin/hermes-v0200-main-c0106e50-mgs
OLD_LAUNCHER=/root/.local/bin/hermes-v0191-mgs
CANONICAL=/root/.local/bin/hermes
EXPECTED_HEAD=6fc69c9d705a41f7b31a200b12a75677857e9a8a
EXPECTED_UPSTREAM=c0106e50e7ecedb3ce34e785d949725dc4e0e457
PATCH=$ROOT/patches/hermes/mgs-runtime-customizations-2026-08-11-main-c0106e50.patch
LOCAL_GUARD=$ROOT/scripts/ensure-hermes-local-patches.sh
MGS_GUARD=$ROOT/scripts/ensure-hermes-mgs-patches.sh
UPDATER=$ROOT/scripts/run-hermes-update-controlled.sh
UV=/root/.local/bin/uv
HERMES=$CANONICAL
THREAD_ID=1536567182824308839
CHECKPOINT_ID=hermes-v0200-activation-20260811
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/hermes-v0200-main-activation-${STAMP}.log
RESULT=$ROOT/data/hermes-v0200-main-activation-result.json
CLEANUP_REPORT=$ROOT/reports/storage-audits/20260811-post-hermes-v0200-full-scan.json
LOCK=/run/lock/mgs-hermes-v0200-main-activation.lock
SWITCHED=0
ROLLBACK_DONE=0

mkdir -p "$ROOT/logs" "$ROOT/data" "$ROOT/reports/storage-audits" /run/lock
exec 9>"$LOCK"
flock -n 9 || exit 73
exec >>"$LOG" 2>&1

log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){
  python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
row={"ts":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":event,"actor":"hermes-v0200-main-activation-finalizer","detail":detail}
with pathlib.Path(p).open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
PY
}
post_thread(){
  local text="$1"
  python3 - "$text" <<'PY' | python3 /root/mgs-agent/scripts/discord-bot-post.py --channel-id 1536567182824308839 >/dev/null
import json,sys
print(json.dumps({"content":sys.argv[1]},ensure_ascii=False))
PY
}
report_infra(){
  local reason="$1" evidence="$2"
  "$ROOT/scripts/send-report-infra-embed.sh" \
    --action modificada \
    --type 'Hermes runtime/config/inventory' \
    --path '/root/.local/bin/hermes; Hermes 0.20 runtime; configs v34; MGS guards; infra inventory; cleanup audit' \
    --reason "$reason" \
    --evidence "$evidence"
}
atomic_launcher(){
  local target="$1" tmp="$CANONICAL.tmp.$$"
  ln -sfn "$target" "$tmp"
  mv -Tf "$tmp" "$CANONICAL"
  [[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$target")" ]]
}
prepare_and_run_restart(){
  local reason="$1" output finalizer resolved shebang python_path repo
  resolved="$(readlink -f "$CANONICAL")"
  shebang="$(head -n 1 "$resolved")"
  python_path="${shebang#\#!}"
  repo="$(dirname "$(dirname "$(dirname "$python_path")")")"
  [[ -x "$repo/venv/bin/python" ]]
  output="$(HERMES_BIN="$CANONICAL" HERMES_REPO="$repo" "$ROOT/scripts/mgs-gateway-restart-safe.sh" --agents 'ares atena zeus' --reason "$reason")"
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
update_inventory(){
  local status="$1" detail="$2"
  python3 - "$ROOT/data/infra-inventory.json" "$status" "$detail" "$LOG" "$CLEANUP_REPORT" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]); status,detail,log,cleanup=sys.argv[2:]; d=json.load(p.open()); now=datetime.datetime.now(datetime.timezone.utc).isoformat(); rid='hermes-port-main-c0106e50-20260811'; items=d.setdefault('runtime_artifacts',[]); item=next((x for x in items if x.get('id')==rid),None)
if item is None: raise SystemExit('inventory item missing')
item.update({'status':status,'active_launcher':'/root/.local/bin/hermes-v0200-main-c0106e50-mgs','canonical_launcher':'/root/.local/bin/hermes','active_repo':'/root/.hermes/hermes-agent-port-v2026-8-11-c0106e50','activation_log':log,'cleanup_audit':cleanup if os.path.exists(cleanup) else None,'activation_detail':detail,'updated_at':now})
raw=json.dumps(d,ensure_ascii=False,indent=2)+'\n'; fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp'); os.write(fd,raw.encode()); os.fsync(fd); os.close(fd); os.chmod(tmp,0o644); os.replace(tmp,p)
print(status)
PY
}
write_result(){
  local status="$1" detail="$2"
  python3 - "$RESULT" "$status" "$detail" "$LOG" "$CLEANUP_REPORT" <<'PY'
import datetime,json,os,pathlib,sys,tempfile
p=pathlib.Path(sys.argv[1]); status,detail,log,cleanup=sys.argv[2:]
d={'status':status,'detail':detail,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'upstream_sha':'c0106e50e7ecedb3ce34e785d949725dc4e0e457','port_commit':'5b1a61da87ef6961f9ee3bd65d9acbfb582ca0a8','version':'0.20.0','services':['ares','atena','zeus'],'restart_order':['ares','atena','zeus'],'log':log,'cleanup_audit':cleanup if os.path.exists(cleanup) else None}
fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp'); os.write(fd,(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()); os.fsync(fd); os.close(fd); os.chmod(tmp,0o644); os.replace(tmp,p)
PY
}

on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  trap - ERR
  set +e
  log "FAIL rc=$rc line=$line switched=$SWITCHED"
  audit hermes_v0200_main_activation_failed "rc=$rc line=$line switched=$SWITCHED log=$LOG"
  if [[ "$SWITCHED" == 1 ]]; then
    log 'Starting automatic rollback to Hermes 0.19.1'
    if atomic_launcher "$OLD_LAUNCHER" && prepare_and_run_restart 'rollback-hermes-v0200-main-activation'; then
      ROLLBACK_DONE=1
      log 'Rollback completed and gateways passed readiness'
    else
      log 'Rollback attempt failed; manual intervention required'
    fi
  fi
  update_inventory activation_failed "rc=$rc line=$line rollback_done=$ROLLBACK_DONE" || true
  write_result failed "rc=$rc line=$line rollback_done=$ROLLBACK_DONE" || true
  "$ROOT/scripts/infra-discovery.sh" >/dev/null 2>&1 || true
  report_infra 'Falha fechada na ativação controlada do Hermes 0.20.0.' "rc=$rc; line=$line; rollback=$ROLLBACK_DONE; log=$LOG" || true
  post_thread "Atualização do Hermes falhou de forma fechada. Rollback automático: $([[ $ROLLBACK_DONE == 1 ]] && echo concluído || echo não concluído). Não vou ocultar a pendência; evidência: $LOG" || true
  exit "$rc"
}
trap on_error ERR

log 'START Hermes v0.20.0 main-current activation'
audit hermes_v0200_main_activation_started "target=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD log=$LOG"
[[ -x "$UV" ]]
"$UV" --version
[[ "$(sha256sum "$PATCH" | cut -d' ' -f1)" == 4ad3c0c41fd66f46c8b4883a53f78da8ec5ff3820ae9fb83160a60864492016a ]]
[[ "$(sha256sum "$LOCAL_GUARD" | cut -d' ' -f1)" == a320f97b965da7f1200ee76b698ddcf22e913279e22ab8a7848a26b94fc986ac ]]
[[ "$(sha256sum "$MGS_GUARD" | cut -d' ' -f1)" == 29625ff98ed48dff6e4753f7a1f379f2f385078d890c4e5d26e9e583e6b7748a ]]
[[ "$(sha256sum "$UPDATER" | cut -d' ' -f1)" == b36569942c176136ee77539a42735010308bbcc7f69d1f21f263952dadd3b00e ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]

git -C "$REPO" fetch --quiet origin main:refs/remotes/origin/main --tags
[[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_UPSTREAM" ]]
[[ "$(git -C "$REPO" rev-list --count HEAD..origin/main)" == 0 ]]
[[ "$(git -C "$REPO" rev-list --count origin/main..HEAD)" == 1 ]]

a320=(
  '3568e1c41da1e4144eca9e7c3860a1be628926279d09440cf44a2904cd56b23a  /root/.hermes/config.yaml'
  '511e9f5f4e748dbf53bff83e009145ac4b0cf61de11ab36956f4f9b0f0d3d19b  /root/.hermes/profiles/zeus/config.yaml'
  '4ee20d1876fc65f13c904fffbf67d9fa60e13af2548d5c755458f892067aeb24  /root/.hermes/profiles/atena/config.yaml'
  'ff367e221cef75f6b2ca7fde8676c8349e93990f4dc323a464513177908752e7  /root/.hermes/profiles/ares/config.yaml'
  '511e9f5f4e748dbf53bff83e009145ac4b0cf61de11ab36956f4f9b0f0d3d19b  /root/mgs-agent/profiles/zeus-config.yaml'
  '4ee20d1876fc65f13c904fffbf67d9fa60e13af2548d5c755458f892067aeb24  /root/mgs-agent/profiles/atena-config.yaml'
  'ff367e221cef75f6b2ca7fde8676c8349e93990f4dc323a464513177908752e7  /root/mgs-agent/profiles/ares-config.yaml'
)
printf '%s\n' "${a320[@]}" | sha256sum -c -

REPO="$REPO" "$LOCAL_GUARD" --check
REPO="$REPO" "$MGS_GUARD"
"$UV" pip check --python "$REPO/.venv/bin/python"
mapfile -t py_paths < <(git -C "$REPO" diff --name-only "$EXPECTED_UPSTREAM..$EXPECTED_HEAD" -- '*.py')
[[ ${#py_paths[@]} -gt 0 ]]
py_abs=(); for p in "${py_paths[@]}"; do py_abs+=("$REPO/$p"); done
"$REPO/.venv/bin/python" -m py_compile "${py_abs[@]}"
[[ -z "$(git -C "$REPO" status --porcelain)" ]]

# Atomic cutover only after every immutable and executable preflight gate passed.
atomic_launcher "$NEW_LAUNCHER"
SWITCHED=1
[[ "$($HERMES --version | sed -n '1p')" == 'Hermes Agent v0.20.0 (2026.8.3)' ]]
prepare_and_run_restart 'hermes-v0200-main-current-activation-1536718896483278888'

# Runtime, config and OAuth validation after all three new gateway processes are ready.
for svc in ares-gateway.service atena-gateway.service zeus-gateway.service; do
  [[ "$(systemctl is-active "$svc")" == active ]]
  [[ "$(systemctl show "$svc" -p SubState --value)" == running ]]
  [[ "$(systemctl show "$svc" -p ExecMainStatus --value)" == 0 ]]
done
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
[[ "$(readlink -f "$CANONICAL")" == "$(readlink -f "$NEW_LAUNCHER")" ]]
[[ "$($HERMES --version | sed -n '1p')" == 'Hermes Agent v0.20.0 (2026.8.3)' ]]

python3 - "$HERMES" <<'PY'
import os,subprocess,sys
h=sys.argv[1]; env=os.environ.copy(); env.pop('HERMES_HOME',None); env.pop('HERMES_PROFILE',None); env['HOME']='/root'
for p in ['default','zeus','atena','ares']:
 args=[h]+([] if p=='default' else ['-p',p])+['config','check']; r=subprocess.run(args,env=env,text=True,capture_output=True,timeout=60); t=r.stdout+r.stderr
 version_line=next((line for line in t.splitlines() if 'Config version:' in line),'')
 assert r.returncode==0 and 'Config version: 34' in version_line and '→' not in version_line,(p,r.returncode,version_line)
 args=[h]+([] if p=='default' else ['-p',p])+['auth','status','openai-codex']; r=subprocess.run(args,env=env,text=True,capture_output=True,timeout=60)
 assert r.returncode==0 and 'logged in' in (r.stdout+r.stderr).lower(),(p,r.returncode)
for p in ['zeus','atena','ares']:
 marker='MGS_V0200_MAIN_POST_OK'; args=[h,'-p',p,'-z',f'Return exactly {marker}']; r=subprocess.run(args,env=env,text=True,capture_output=True,timeout=240)
 assert r.returncode==0 and r.stdout.strip()==marker,(p,r.returncode,r.stdout[-80:])
 print(p,'post_smoke=PASS')
PY

REPO="$REPO" "$LOCAL_GUARD" --check
"$UV" pip check --python "$REPO/.venv/bin/python"
git -C "$REPO" fetch --quiet origin main:refs/remotes/origin/main
[[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_UPSTREAM" ]]
[[ "$(git -C "$REPO" rev-list --count HEAD..origin/main)" == 0 ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]

# Read-only whole-VPS cleanup inventory; deletion remains a separately confirmed step.
python3 "$ROOT/data/vps-post-hermes-cleanup-audit-20260811.py" "$CLEANUP_REPORT"
python3 - "$CLEANUP_REPORT" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); assert x['mutation_performed'] is False; assert x['active_runtime']=='/root/.hermes/hermes-agent-port-v2026-8-11-c0106e50'; print('cleanup_audit_readback=PASS')
PY

update_inventory activated_validated 'version=0.20.0 upstream=c0106e50 port=6fc69c9d services=3/3 configs=4/4 smokes=3/3 behind=0 cleanup_audit=ready'
"$ROOT/scripts/infra-discovery.sh" >/dev/null
"$ROOT/scripts/mgs-knowledge-control.py" checkpoint-upsert \
  --id "$CHECKPOINT_ID" --agent zeus --thread-id "$THREAD_ID" \
  --objective 'Atualizar Hermes integralmente e revisar limpeza conservadora da VPS' \
  --state completed \
  --next-step 'Revisar com Rodolfo o manifesto de limpeza pós-Hermes; nenhuma exclusão foi feita' \
  --source "discord:$THREAD_ID"
"$ROOT/scripts/mgs-knowledge-control.py" validate >/dev/null
write_result success 'Hermes 0.20.0 active; main current c0106e50; MGS port 6fc69c9d; zero upstream commits pending; configs v34; services and smokes PASS; cleanup inventory ready'
audit hermes_v0200_main_activation_finished "version=0.20.0 upstream=$EXPECTED_UPSTREAM port=$EXPECTED_HEAD services=3/3 configs=4/4 smokes=3/3 behind=0 cleanup=$CLEANUP_REPORT log=$LOG"
report_infra 'Hermes atualizado integralmente para o main atual, configurações migradas e inventário de limpeza pós-update gerado.' "version=0.20.0; upstream=$EXPECTED_UPSTREAM; port=$EXPECTED_HEAD; pending=0; tests=532+6,220(+2 skipped),193,454+6; configs=4/4 v34; services=3/3; smokes=3/3; cleanup=$CLEANUP_REPORT; log=$LOG"
post_thread "Atualização concluída e validada: Hermes 0.20.0, upstream c0106e50, port MGS 6fc69c9d, zero commits upstream pendentes. Ares, Atena e Zeus carregaram o runtime corrigido e passaram prontidão, configs v34 e smokes reais. A auditoria completa de limpeza ficou pronta em $CLEANUP_REPORT; nenhuma exclusão foi feita."
log 'DONE Hermes v0.20.0 main-current activation'
