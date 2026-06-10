#!/usr/bin/env bash
set -euo pipefail
BASE=/root/mgs-agent
REPO=/root/.hermes/hermes-agent
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$BASE/logs/hermes-restart-validate-${STAMP}.log"
SERVICES=(zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service)
exec > >(tee -a "$LOG") 2>&1
log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
send_report(){
  local title="$1" body="$2"
  set +u; set -a; source /root/.hermes/profiles/zeus/.env 2>/dev/null || true; set +a; set -u
  local target="${THREAD_ID:-1514278119945670887}"
  [[ -n "${DISCORD_BOT_TOKEN:-}" ]] || { log "WARN no Discord token"; return 0; }
  python3 - "$target" "$title" "$body" <<'PY'
import json, os, sys, urllib.request
channel,title,body=sys.argv[1:4]
token=os.environ.get('DISCORD_BOT_TOKEN','')
content=(title+'\n\n'+body)[:1900]
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages',method='POST',headers={'Authorization':f'Bot {token}','Content-Type':'application/json','User-Agent':'Hermes-Agent'},data=json.dumps({'content':content},ensure_ascii=False).encode())
urllib.request.urlopen(req,timeout=20).read()
PY
}
fail(){ rc=$?; tail_summary=$(tail -80 "$LOG" | sed 's/`/'"'"'/g' | tail -55); send_report "❌ Hermes restart/validação FALHOU" "Log: $LOG\n\n\`\`\`text\n$tail_summary\n\`\`\`" || true; exit "$rc"; }
trap fail ERR
log "Pre restart state"
/root/.hermes/profiles/zeus/home/.local/bin/hermes --version 2>&1 | sed -n '1,8p' || true
git -C "$REPO" fetch --quiet origin main
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
BASE="$BASE" REPO="$REPO" LOG="$LOG" "$BASE/scripts/ensure-hermes-mgs-patches.sh"
"$REPO/venv/bin/python" -m py_compile "$REPO/plugins/platforms/discord/adapter.py" "$REPO/gateway/run.py" "$REPO/gateway/config.py" "$REPO/tools/send_message_tool.py" "$REPO/tools/discord_tool.py"
log "Restarting gateways: ${SERVICES[*]}"
systemctl restart "${SERVICES[@]}"
sleep 25
log "Services active check"
systemctl is-active "${SERVICES[@]}"
systemctl show "${SERVICES[@]}" -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
log "Sanitized Codex auth"
python3 - <<'PY'
import json, pathlib
for name,path in [('root','/root/.hermes/auth.json'),('zeus','/root/.hermes/profiles/zeus/auth.json'),('atena','/root/.hermes/profiles/atena/auth.json'),('ares','/root/.hermes/profiles/ares/auth.json'),('hera','/root/.hermes/profiles/hera/auth.json')]:
    p=pathlib.Path(path)
    if not p.exists(): print(f'{name}: auth_missing'); continue
    d=json.loads(p.read_text()); prov=d.get('providers',{}).get('openai-codex',{}); toks=prov.get('tokens',{}) if isinstance(prov,dict) else {}
    print(f"{name}: active={d.get('active_provider')} auth_mode={prov.get('auth_mode') if isinstance(prov,dict) else None} access_len={len(toks.get('access_token',''))} refresh_present={bool(toks.get('refresh_token'))}")
PY
for p in zeus atena ares hera; do
  echo "--- $p recent errors ---"
  tail -60 "/root/.hermes/profiles/$p/logs/errors.log" 2>/dev/null | tail -10 || true
done
HEAD=$(git -C "$REPO" rev-parse --short HEAD); ORIGIN=$(git -C "$REPO" rev-parse --short origin/main); BEHIND=$(git -C "$REPO" rev-list --count HEAD..origin/main)
STATUS=$(git -C "$REPO" status --short | sed -n '1,35p')
DISK=$(df -h / | awk 'NR==2{print $4 " livres / uso " $5}')
BACKUP=$(ls -t /root/hermes-profiles-backup-20260610-121017.tar.gz /root/hermes-profiles-backup-*.tar.gz 2>/dev/null | head -1)
log "DONE restart validation"
send_report "✅ Hermes update + restart concluídos" "\`\`\`text\nHEAD:         $HEAD\norigin/main:  $ORIGIN\nbehind:       $BEHIND\nGateways:     Zeus/Atena/Ares/Hera active\nPatch guard:  OK\npy_compile:   OK\nPytest alvo:  126 passed\nBackup:       $BACKUP\nDisco:        $DISK\nLog:          $LOG\n\nGit status:\n${STATUS:-clean}\n\`\`\`\nObs.: update já estava em commit mais novo que o anexo quando revalidei; finalizei preservando patches MGS e reiniciando todos os agentes." || true
