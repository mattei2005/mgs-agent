#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
REPO=/root/.hermes/hermes-agent
THREAD_ID=${THREAD_ID:-1514962661203382274}
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$BASE/logs/hermes-update-finalize-${STAMP}.log"
SERVICES=(zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service)
exec > >(tee -a "$LOG") 2>&1
log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
send_report(){
  local status="$1" body="$2"
  set +u; set -a
  source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
  set +a; set -u
  if [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then log "WARN no DISCORD_BOT_TOKEN"; return 0; fi
  python3 - "$THREAD_ID" "$status" "$body" <<'PY'
import json, os, sys, urllib.request
channel, status, body = sys.argv[1:4]
token=os.environ.get('DISCORD_BOT_TOKEN','')
content=(status+'\n\n'+body)[:1900]
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages', method='POST', headers={'Authorization':f'Bot {token}','Content-Type':'application/json','User-Agent':'Hermes-Agent'}, data=json.dumps({'content':content}, ensure_ascii=False).encode())
urllib.request.urlopen(req, timeout=20).read()
PY
}
fail(){
  rc=$?
  log "FAILED rc=$rc line=${BASH_LINENO[0]}"
  tail_summary=$(tail -80 "$LOG" | sed 's/`/'"'"'/g' | tail -55)
  send_report "❌ Hermes update finalização FALHOU" "Log: $LOG\n\n\`\`\`text\n$tail_summary\n\`\`\`" || true
  exit "$rc"
}
trap fail ERR
log "START finalize Hermes update"
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
log "Patch guard"
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
log "py_compile"
"$REPO/venv/bin/python" -m py_compile "$REPO/plugins/platforms/discord/adapter.py" "$REPO/gateway/run.py" "$REPO/gateway/config.py" "$REPO/tools/send_message_tool.py" "$REPO/tools/discord_tool.py"
log "Restarting gateways"
systemctl restart "${SERVICES[@]}"
sleep 25
log "Validating services"
systemctl is-active "${SERVICES[@]}"
systemctl show "${SERVICES[@]}" -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ActiveEnterTimestamp --no-pager
log "Codex auth sanitized"
python3 - <<'PY'
import json, pathlib
for name,path in [('root','/root/.hermes/auth.json'),('zeus','/root/.hermes/profiles/zeus/auth.json'),('atena','/root/.hermes/profiles/atena/auth.json'),('ares','/root/.hermes/profiles/ares/auth.json'),('hera','/root/.hermes/profiles/hera/auth.json')]:
    p=pathlib.Path(path)
    if not p.exists(): print(f'{name}: auth_missing'); continue
    d=json.loads(p.read_text()); prov=d.get('providers',{}).get('openai-codex',{}); toks=prov.get('tokens',{}) if isinstance(prov,dict) else {}
    print(f"{name}: active={d.get('active_provider')} auth_mode={prov.get('auth_mode') if isinstance(prov,dict) else None} access_len={len(toks.get('access_token',''))} refresh_present={bool(toks.get('refresh_token'))}")
PY
log "Post checks"
HERMES_VERSION=$(hermes --version 2>&1 | sed -n '1,5p')
HEAD=$(git -C "$REPO" rev-parse --short HEAD)
ORIGIN=$(git -C "$REPO" rev-parse --short origin/main)
BEHIND=$(git -C "$REPO" rev-list --count HEAD..origin/main)
STATUS=$(git -C "$REPO" status --short | sed -n '1,30p')
DISK=$(df -h / | awk 'NR==2{print $4 " livres / uso " $5}')
BACKUP=$(ls -t /root/hermes-profiles-backup-20260612-080355.tar.gz 2>/dev/null | head -1 || true)
log "DONE finalize Hermes update"
send_report "✅ Hermes update MGS concluído" "\`\`\`text\nHEAD:         $HEAD\norigin/main:  $ORIGIN\nbehind:       $BEHIND\nGateways:     Zeus/Atena/Ares/Hera active\nPatch guard:  OK\npy_compile:   OK\nBackup:       ${BACKUP:-ver log inicial}\nDisco:        $DISK\nLog:          $LOG\n\nHermes:\n$HERMES_VERSION\n\nGit status:\n${STATUS:-clean}\n\`\`\`\nAtualização finalizada e gateways reiniciados/validados no VPS." || true
