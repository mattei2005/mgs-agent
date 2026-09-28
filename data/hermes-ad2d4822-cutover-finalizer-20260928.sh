#!/usr/bin/env bash
set -Eeuo pipefail

CUTOVER_ID="hermes-ad2d4822-20260928"
ROOT="/root/mgs-agent"
LINK="/root/.local/bin/hermes"
OLD_LAUNCHER="/root/.hermes/hermes-agent-port-main-59004a62-mgs/.venv/bin/hermes"
NEW_REPO="/root/.hermes/hermes-agent-port-main-ad2d4822-mgs"
NEW_LAUNCHER="$NEW_REPO/.venv/bin/hermes"
EXPECTED_HEAD="c559e65bcf43f9f41cbc2fa1d6ef8d47643dbc6e"
BACKUP="/root/.hermes/secure-backups/hermes-update/20260928T213017Z-main-ad2d4822-controlled"
FINANCE_PROBE="$BACKUP/finance-fingerprint.py"
PRE="$BACKUP/manifests/finance-production-cutover-pre.json"
POST="$BACKUP/manifests/finance-production-cutover-post.json"
LOG="$ROOT/logs/${CUTOVER_ID}.log"
RESULT="$ROOT/data/${CUTOVER_ID}-result.json"
AUDIT="$ROOT/logs/events-audit.jsonl"
LOCK="/run/${CUTOVER_ID}.lock"
ORDER=(ares atena zeus)
ROLLING_BACK=0

mkdir -p "$ROOT/logs" "$ROOT/data"
exec >>"$LOG" 2>&1
exec 9>"$LOCK"
flock -n 9 || { echo "cutover lock busy"; exit 73; }

now(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
log(){ printf '[%s] %s\n' "$(now)" "$*"; }
audit(){
  python3 - "$1" "$2" >>"$AUDIT" <<'PY'
import json,sys
from datetime import datetime,timezone
print(json.dumps({"ts":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"event":sys.argv[1],"actor":"hermes-ad2d4822-cutover-finalizer","detail":sys.argv[2]},ensure_ascii=False,separators=(",",":")))
PY
}
write_result(){
  python3 - "$1" "$2" "$3" >"$RESULT" <<'PY'
import json,sys
from datetime import datetime,timezone
print(json.dumps({"schema_version":1,"cutover_id":"hermes-ad2d4822-20260928","status":sys.argv[1],"detail":sys.argv[2],"active_launcher":sys.argv[3],"updated_at":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},indent=2))
PY
}
ready(){
  local agent="$1" svc="${1}-gateway.service" agent_log="/root/.hermes/profiles/$1/logs/agent.log" offset=0 out pid cmdline
  [[ -f "$agent_log" ]] && offset="$(stat -c%s "$agent_log")"
  systemctl restart "$svc"
  out="$(/root/mgs-agent/scripts/check-gateway-ready.py --service "$svc" --log "$agent_log" --offset "$offset" --timeout 180 --poll 2)"
  pid="$(systemctl show "$svc" -p MainPID --value)"
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || return 1
  cmdline="$(tr '\0' ' ' <"/proc/$pid/cmdline")"
  [[ "$cmdline" == *"$NEW_REPO/.venv/bin/python"* ]] || {
    log "runtime path mismatch agent=$agent pid=$pid"
    return 1
  }
  python3 - "$out" "$agent" <<'PY'
import json,sys
d=json.loads(sys.argv[1])
assert d.get("ActiveState")=="active" and d.get("SubState")=="running" and d.get("discord_connected") is True,d
print("gateway_ready",sys.argv[2],"pid",d.get("MainPID"),"restarts",d.get("NRestarts"))
PY
}
rollback(){
  local reason="$1" agent
  ROLLING_BACK=1
  trap - ERR
  log "ROLLBACK start reason=$reason"
  ln -sfn "$OLD_LAUNCHER" "$LINK"
  for agent in "${ORDER[@]}"; do
    systemctl restart "${agent}-gateway.service" || true
    /root/mgs-agent/scripts/check-gateway-ready.py --service "${agent}-gateway.service" --log "/root/.hermes/profiles/$agent/logs/agent.log" --offset 0 --timeout 180 --poll 2 || true
  done
  audit "hermes_cutover_rolled_back" "reason=$reason launcher=$(readlink -f "$LINK") log=$LOG"
  write_result "rolled_back" "$reason" "$(readlink -f "$LINK")"
  log "ROLLBACK done launcher=$(readlink -f "$LINK")"
}
on_error(){
  local rc=$? line=${BASH_LINENO[0]:-unknown}
  [[ "$ROLLING_BACK" == 1 ]] || rollback "rc=$rc line=$line"
  exit "$rc"
}
trap on_error ERR

log "START cutover"
audit "hermes_cutover_started" "candidate=$EXPECTED_HEAD backup=$BACKUP log=$LOG"
[[ -x "$NEW_LAUNCHER" && -x "$OLD_LAUNCHER" && -x "$FINANCE_PROBE" ]]
[[ "$(git -C "$NEW_REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]]
[[ -z "$(git -C "$NEW_REPO" status --porcelain)" ]]
"$NEW_LAUNCHER" --version
(
  cd "$BACKUP"
  sha256sum -c BACKUP-SEAL.sha256
  sha256sum -c COMPONENT-SHA256SUMS
)
/usr/bin/python3 "$FINANCE_PROBE" >"$PRE"
log "prechecks PASS"

ln -sfn "$NEW_LAUNCHER" "$LINK"
[[ "$(readlink -f "$LINK")" == "$NEW_LAUNCHER" ]]
audit "hermes_launcher_switched" "from=$OLD_LAUNCHER to=$NEW_LAUNCHER"

for agent in "${ORDER[@]}"; do
  ready "$agent"
  audit "hermes_cutover_agent_ready" "agent=$agent launcher=$NEW_LAUNCHER"
done

/usr/bin/python3 "$FINANCE_PROBE" >"$POST"
python3 - "$PRE" "$POST" <<'PY'
import json,sys
before=json.load(open(sys.argv[1])); after=json.load(open(sys.argv[2]))
assert before==after,(before,after)
print("finance_fingerprint_post_cutover=PASS")
PY

[[ "$(readlink -f "$LINK")" == "$NEW_LAUNCHER" ]]
for agent in "${ORDER[@]}"; do
  [[ "$(systemctl is-active "${agent}-gateway.service")" == active ]]
done

write_result "success" "all gateways and finance fingerprint validated" "$NEW_LAUNCHER"
audit "hermes_cutover_finished" "status=success head=$EXPECTED_HEAD launcher=$NEW_LAUNCHER finance=PASS log=$LOG"
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type "runtime/script" \
  --path "/root/.local/bin/hermes; Ares/Atena/Zeus gateways; $RESULT" \
  --reason "Cutover controlado do Hermes para upstream congelado ad2d4822 com 9 commits MGS portados" \
  --evidence "Ares→Atena→Zeus ativos e conectados; launcher/readback c559e65b; fingerprint financeiro pré/pós idêntico; rollback não acionado" || log "REPORT-INFRA failed"
log "DONE cutover success"
