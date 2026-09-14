#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/root/mgs-agent
HERMES=/root/.local/bin/hermes
REPO=/root/.hermes/hermes-agent-stage-main-14efb460-mgs
EXPECTED_HEAD=abbba7e0e8649759ab1fb4807b72b5ba4fc79de4
SAFE=$ROOT/scripts/mgs-gateway-restart-safe.sh
REPORT=$ROOT/scripts/send-report-infra-embed.sh
POST=$ROOT/scripts/discord-bot-post.py
THREAD=1549096295338221660
SNAPSHOT=/root/.hermes/secure-backups/vps-maintenance/20260914T180134Z-vps-hermes-main-14efb460/restart-three-agents-targets.sha256
RESULT=$ROOT/data/restart-three-agents-20260914-result.json
LOCK=/run/lock/mgs-restart-three-agents-20260914.lock
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$ROOT/logs/restart-three-agents-${STAMP}.log
mkdir -p "$ROOT/logs" "$ROOT/data" /run/lock
exec 9>"$LOCK"; flock -n 9 || exit 73
exec >>"$LOG" 2>&1
log(){ printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
audit(){ python3 - "$ROOT/logs/events-audit.jsonl" "$1" "$2" <<'PY'
import datetime,json,pathlib,sys
p,event,detail=sys.argv[1:]
with pathlib.Path(p).open('a',encoding='utf-8') as f:
 f.write(json.dumps({'ts':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,'actor':'restart-three-agents-finalizer','detail':detail},ensure_ascii=False)+'\n')
PY
}
write_result(){ python3 - "$RESULT" "$1" "$2" "$LOG" <<'PY'
import datetime,json,os,pathlib,subprocess,sys,tempfile
path=pathlib.Path(sys.argv[1]);status,detail,log=sys.argv[2:]
def show(a,k):return subprocess.run(['systemctl','show',a+'-gateway.service','-p',k,'--value'],text=True,capture_output=True).stdout.strip()
data={'status':status,'detail':detail,'validated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'restart_order':['ares','atena','zeus'],'services':{a:{k:show(a,k) for k in ('ActiveState','SubState','MainPID','NRestarts','ExecMainStatus','ExecMainStartTimestamp')} for a in ('ares','atena','zeus')},'version_line':subprocess.run(['/root/.local/bin/hermes','--version'],text=True,capture_output=True).stdout.splitlines()[0],'log':log}
fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
try:
 with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o644);os.replace(tmp,path)
finally:
 if os.path.exists(tmp):os.unlink(tmp)
PY
}
discord_readback(){ python3 - "$1" "$2" "$3" <<'PY'
import json,os,sys,urllib.request
channel,message_id,expected=sys.argv[1:]
for raw in open('/root/.hermes/profiles/zeus/.env',errors='ignore'):
 line=raw.strip()
 if line and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
token=os.environ.get('DISCORD_BOT_TOKEN');assert token
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{message_id}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
assert str(data.get('channel_id'))==channel and data.get('content','')==expected and not(data.get('mentions') or [])
print('discord_readback=PASS message_id='+message_id)
PY
}
post_callback(){ local content="$1" output mid; output="$(python3 - "$content" <<'PY' | "$POST" --channel-id "$THREAD"
import json,sys
print(json.dumps({'content':sys.argv[1],'allowed_mentions':{'parse':[]}},ensure_ascii=False))
PY
)"; mid="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);assert m;print(m.group(1))
PY
)"; discord_readback "$THREAD" "$mid" "$content"; }
on_error(){ local rc=$? line=${BASH_LINENO[0]:-unknown};trap - ERR;set +e;log "FAIL rc=$rc line=$line";write_result failed "rc=$rc line=$line";audit gateway_restart_three_agents_failed "rc=$rc line=$line result=$RESULT log=$LOG";post_callback "**Resultado:** falha no reinício dos três agentes.\n**Estado:** consulte \`$RESULT\`; nenhum sucesso foi presumido.\n**Evidência:** \`$LOG\`." || true;exit "$rc"; }
trap on_error ERR
log 'START restart Ares -> Atena -> Zeus'
audit gateway_restart_three_agents_started "order=ares,atena,zeus log=$LOG"
sha256sum -c "$SNAPSHOT"
[[ "$(readlink -f "$HERMES")" == "$REPO/.venv/bin/hermes" ]]
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ -z "$(git -C "$REPO" status --porcelain)" ]]
python3 - <<'PY' >"$ROOT/data/restart-three-agents-20260914-pre-pids.json"
import json,subprocess
print(json.dumps({a:subprocess.run(['systemctl','show',a+'-gateway.service','-p','MainPID','--value'],text=True,capture_output=True).stdout.strip() for a in ('ares','atena','zeus')}))
PY
output="$(HERMES_BIN="$HERMES" HERMES_REPO="$REPO" "$SAFE" --agents 'ares atena zeus' --reason 'rodolfo-restart-three-agents-1549135247210188984' --delay 90)"
finalizer="$(python3 - "$output" <<'PY'
import re,sys
m=re.search(r'Prepared detached finalizer only \(no restart executed\): (\S+)',sys.argv[1]);assert m;print(m.group(1))
PY
)"
[[ -x "$finalizer" ]];"$finalizer"
python3 - "$ROOT/data/restart-three-agents-20260914-pre-pids.json" <<'PY'
import json,subprocess,sys
pre=json.load(open(sys.argv[1]))
for a in ('ares','atena','zeus'):
 def show(k):return subprocess.run(['systemctl','show',a+'-gateway.service','-p',k,'--value'],text=True,capture_output=True,check=True).stdout.strip()
 assert show('ActiveState')=='active' and show('SubState')=='running' and show('ExecMainStatus')=='0'
 pid=show('MainPID');assert pid and pid!='0' and pid!=pre[a],(a,pre[a],pid)
 print(a,'pid_changed=PASS',pre[a],pid)
PY
[[ -z "$(systemctl --failed --no-legend --plain)" ]]
for profile in ares atena zeus; do
 marker="MGS_RESTART_${profile^^}_OK";out="$ROOT/logs/restart-three-agents-smoke-$profile-$STAMP.log"
 HERMES_HOME="/root/.hermes/profiles/$profile" HERMES_BACKGROUND_NOTIFICATIONS=off "$HERMES" -z "Respond exactly $marker and nothing else." >"$out" 2>&1
 python3 - "$out" "$marker" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace');m=sys.argv[2];last=next((x.strip() for x in reversed(s.splitlines()) if x.strip()),'');assert s.count(m)==1 and last==m
PY
done
write_result success 'Ares, Atena e Zeus reiniciados em ordem; PIDs novos; systemd/Discord readiness e smokes 3/3 PASS'
report_output="$($REPORT --action reiniciada --type service --path 'ares-gateway.service; atena-gateway.service; zeus-gateway.service' --reason 'Reinício explícito solicitado por Rodolfo na mensagem 1549135247210188984' --evidence 'ordem Ares→Atena→Zeus; PIDs novos; active/running; Discord readiness 3/3; smokes 3/3; failed units 0')"
report_id="$(python3 - "$report_output" <<'PY'
import re,sys
m=re.search(r'message_id=(\d+)',sys.argv[1]);assert m;print(m.group(1))
PY
)"
audit gateway_restart_three_agents_finished "result=$RESULT report_infra=$report_id log=$LOG"
post_callback "**Resultado:** sucesso — Ares, Atena e Zeus foram reiniciados agora, na ordem **Ares → Atena → Zeus**.\n**Validação:** PIDs novos, serviços active/running, Discord pronto, smokes 3/3 e zero unidades com falha.\n**Hermes:** main \`14efb460\`, port MGS \`abbba7e0\`, sem mudança de versão/configuração.\n**Evidência:** \`$RESULT\`; REPORT-INFRA \`$report_id\`."
log 'DONE restart Ares -> Atena -> Zeus'
