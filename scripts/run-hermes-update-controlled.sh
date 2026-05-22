#!/usr/bin/env bash
set -euo pipefail

THREAD_ID="${THREAD_ID:-1507517903791198248}"
BASE="/root/mgs-agent"
REPO="/root/.hermes/hermes-agent"
HERMES_BIN="${HERMES_BIN:-/root/.hermes/profiles/zeus/home/.local/bin/hermes}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$BASE/logs/hermes-update-controlled-${STAMP}.log"
PATCH_DIR="$BASE/patches/hermes"
LOCAL_PATCH="$PATCH_DIR/mgs-discord-local-preupdate-${STAMP}.patch"
PORT_PATCH="$PATCH_DIR/mgs-discord-plugin-port-${STAMP}.patch"
BACKUP_PATH="${BACKUP_PATH:-/root/hermes-profiles-backup-20260522-192610.tar.gz}"
mkdir -p "$PATCH_DIR" "$(dirname "$LOG")"

exec > >(tee -a "$LOG") 2>&1

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

send_discord_report() {
  local status="$1"
  local body="$2"
  set +u
  set -a
  source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
  set +a
  set -u
  if [[ -z "${DISCORD_BOT_TOKEN:-}" || -z "${THREAD_ID:-}" ]]; then
    log "WARN discord report skipped: missing token/thread"
    return 0
  fi
  python3 - "$THREAD_ID" "$status" "$body" <<'PY'
import json, os, sys, urllib.request
thread_id, status, body = sys.argv[1:4]
token = os.environ.get('DISCORD_BOT_TOKEN','')
content = f"{status}\n\n{body}"
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{thread_id}/messages",
    method="POST",
    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "Hermes-Agent"},
    data=json.dumps({"content": content[:1900]}, ensure_ascii=False).encode(),
)
urllib.request.urlopen(req, timeout=15).read()
PY
}

fail() {
  local rc=$?
  log "FAILED rc=$rc line=${BASH_LINENO[0]}"
  tail_summary="$(tail -60 "$LOG" | sed 's/`/'"'"'/g' | tail -40)"
  send_discord_report "❌ Hermes update controlado FALHOU" "Log: $LOG\nBackup: $BACKUP_PATH\n\n\`\`\`text\n${tail_summary}\n\`\`\`" || true
  exit "$rc"
}
trap fail ERR

log "START controlled Hermes update"
log "backup=$BACKUP_PATH"
log "repo=$REPO"

log "Pre-state"
"$HERMES_BIN" --version 2>&1 | sed -n '1,10p' || true
git -C "$REPO" fetch --quiet origin main
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
git -C "$REPO" status --short

log "Saving local Hermes patch"
git -C "$REPO" diff > "$LOCAL_PATCH"
if [[ ! -s "$LOCAL_PATCH" ]]; then
  PREV_PATCH="$(ls -t "$PATCH_DIR"/mgs-discord-local-preupdate-*.patch 2>/dev/null | head -1 || true)"
  if [[ -n "$PREV_PATCH" && -s "$PREV_PATCH" ]]; then
    log "No current git diff; reusing previous saved patch: $PREV_PATCH"
    cp "$PREV_PATCH" "$LOCAL_PATCH"
  fi
fi
# Port current MGS Discord patch from old built-in adapter path to new plugin adapter path.
sed 's#gateway/platforms/discord.py#plugins/platforms/discord/adapter.py#g' "$LOCAL_PATCH" > "$PORT_PATCH"
log "local_patch=$LOCAL_PATCH bytes=$(wc -c < "$LOCAL_PATCH")"
log "port_patch=$PORT_PATCH bytes=$(wc -c < "$PORT_PATCH")"

if [[ ! -s "$LOCAL_PATCH" ]]; then
  log "WARN no local patch captured"
fi

log "Resetting tracked local changes before update; untracked files preserved"
git -C "$REPO" reset --hard HEAD

log "Running hermes update"
"$HERMES_BIN" update --yes --no-backup

log "Post-update rev"
git -C "$REPO" fetch --quiet origin main
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"

log "Applying MGS Discord patch to plugin adapter"
if [[ -s "$PORT_PATCH" ]]; then
  git -C "$REPO" apply --check "$PORT_PATCH"
  git -C "$REPO" apply "$PORT_PATCH"
else
  log "WARN empty port patch; skipping apply"
fi

log "Compiling critical Hermes files"
PYBIN="$REPO/venv/bin/python"
[[ -x "$PYBIN" ]] || PYBIN="python3"
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/config.py" \
  "$REPO/tools/send_message_tool.py" \
  "$REPO/tools/discord_tool.py"

log "Status after patch"
git -C "$REPO" status --short

log "Restarting gateways"
systemctl restart zeus-gateway.service atena-gateway.service
sleep 15

log "Validating services"
systemctl is-active --quiet zeus-gateway.service
systemctl is-active --quiet atena-gateway.service
systemctl is-active --quiet mgs-autocommit.service
systemctl show zeus-gateway.service atena-gateway.service -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager

log "Validating gateway logs"
tail -80 /root/.hermes/profiles/zeus/logs/agent.log | grep -E 'Connected as|Gateway running|discord connected' | tail -10 || true
tail -80 /root/.hermes/profiles/atena/logs/agent.log | grep -E 'Connected as|Gateway running|discord connected' | tail -10 || true

FINAL_HEAD="$(git -C "$REPO" rev-parse --short HEAD)"
FINAL_ORIGIN="$(git -C "$REPO" rev-parse --short origin/main)"
FINAL_BEHIND="$(git -C "$REPO" rev-list --count HEAD..origin/main)"
STATUS_SHORT="$(git -C "$REPO" status --short | sed -n '1,20p')"

log "DONE controlled Hermes update"
send_discord_report "✅ Hermes update controlado concluído" "\`\`\`text\nHEAD: $FINAL_HEAD\norigin/main: $FINAL_ORIGIN\nbehind: $FINAL_BEHIND\nServiços: zeus active / atena active / autocommit active\nPatch MGS: aplicado em plugins/platforms/discord/adapter.py\npy_compile: OK\nBackup: $BACKUP_PATH\nLog: $LOG\n\nGit status:\n${STATUS_SHORT:-clean}\n\`\`\`\nPróximo passo pendente: testar na prática uma nova thread Zeus e uma nova thread Atena para confirmar auto-thread + auto-add." || true
