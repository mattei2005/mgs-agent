#!/usr/bin/env bash
set -euo pipefail

BASE="/root/mgs-agent"
REPO="/root/.hermes/hermes-agent"
HERMES_BIN="${HERMES_BIN:-/root/.hermes/profiles/zeus/home/.local/bin/hermes}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$BASE/logs/hermes-update-all-agents-${STAMP}.log"
PATCH_DIR="$BASE/patches/hermes"
BACKUP_PATH="/root/hermes-profiles-backup-${STAMP}.tar.gz"
LOCAL_PATCH="$PATCH_DIR/mgs-local-preupdate-${STAMP}.patch"
SERVICES=(zeus-gateway.service atena-gateway.service ares-gateway.service)
mkdir -p "$PATCH_DIR" "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }

send_report() {
  local status="$1" body="$2"
  set +u; set -a
  source /root/.hermes/profiles/zeus/.env 2>/dev/null || true
  set +a; set -u
  local target="${THREAD_ID:-1514278119945670887}"
  if [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then
    log "WARN: DISCORD_BOT_TOKEN missing; cannot send Discord report"
    return 0
  fi
  python3 - "$target" "$status" "$body" <<'PY'
import json, os, sys, urllib.request
channel, status, body = sys.argv[1:4]
token = os.environ.get('DISCORD_BOT_TOKEN','')
content = (status + "\n\n" + body)[:1900]
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{channel}/messages",
    method="POST",
    headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "Hermes-Agent"},
    data=json.dumps({"content": content}, ensure_ascii=False).encode(),
)
urllib.request.urlopen(req, timeout=20).read()
PY
}

fail() {
  local rc=$?
  log "FAILED rc=$rc line=${BASH_LINENO[0]}"
  local tail_summary
  tail_summary="$(tail -80 "$LOG" | sed 's/`/'"'"'/g' | tail -55)"
  send_report "❌ Hermes update MGS FALHOU" "Log: $LOG\nBackup: $BACKUP_PATH\n\n\`\`\`text\n$tail_summary\n\`\`\`" || true
  exit "$rc"
}
trap fail ERR

log "START Hermes update all agents"
log "repo=$REPO"
log "backup=$BACKUP_PATH"

log "Pre-state"
"$HERMES_BIN" --version 2>&1 | sed -n '1,12p' || true
git -C "$REPO" fetch --quiet origin main
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main) ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)"
git -C "$REPO" status --short | sed -n '1,80p'
log "Services pre"
systemctl is-active "${SERVICES[@]}" || true

log "Creating profiles backup"
tar --warning=no-file-changed --ignore-failed-read -czf "$BACKUP_PATH" /root/.hermes/profiles/
ls -lh "$BACKUP_PATH"

log "Saving local diff"
git -C "$REPO" diff > "$LOCAL_PATCH" || true
log "local_patch=$LOCAL_PATCH bytes=$(wc -c < "$LOCAL_PATCH")"

log "Resetting tracked local changes before update"
git -C "$REPO" reset --hard HEAD

if [[ "$(git -C "$REPO" rev-list --count HEAD..origin/main)" != "0" ]]; then
  log "Fast-forwarding to origin/main"
  git -C "$REPO" pull --ff-only origin main
else
  log "Already at origin/main"
fi

log "Installing/updating Python package"
PYBIN="$REPO/venv/bin/python"
if [[ -x "$PYBIN" ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PYBIN" -e "${REPO}[all]" || uv pip install --python "$PYBIN" -e "$REPO"
  else
    "$PYBIN" -m pip install -e "${REPO}[all]" || "$PYBIN" -m pip install -e "$REPO"
  fi
else
  log "WARN: repo venv python not found; using hermes update may repair on next maintenance"
  PYBIN="python3"
fi

log "Installing Node deps where applicable"
if [[ -f "$REPO/package.json" ]]; then
  (cd "$REPO" && npm install --no-fund --no-audit)
fi
if [[ -f "$REPO/ui-tui/package.json" ]]; then
  (cd "$REPO/ui-tui" && npm install --no-fund --no-audit)
fi

log "Applying canonical MGS Hermes patches"
if ! BASE="$BASE" REPO="$REPO" LOG="$LOG" "$BASE/scripts/ensure-hermes-mgs-patches.sh"; then
  log "Patch guard failed on canonical patches; trying saved pre-update local diff before failing"
  if [[ -s "$LOCAL_PATCH" ]] && git -C "$REPO" apply --check "$LOCAL_PATCH" >/dev/null 2>&1; then
    log "Applying saved local pre-update patch: $LOCAL_PATCH"
    git -C "$REPO" apply "$LOCAL_PATCH"
    BASE="$BASE" REPO="$REPO" LOG="$LOG" "$BASE/scripts/ensure-hermes-mgs-patches.sh"
  else
    log "Saved local patch not applicable: $LOCAL_PATCH"
    exit 1
  fi
fi

log "Compiling critical files"
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/config.py" \
  "$REPO/tools/send_message_tool.py" \
  "$REPO/tools/discord_tool.py"

log "Clearing update check sentinels"
find /root/.hermes /root/.hermes/profiles -maxdepth 3 -name '.update_check' -type f -delete 2>/dev/null || true

log "Post-update rev/status"
git -C "$REPO" fetch --quiet origin main
log "HEAD=$(git -C "$REPO" rev-parse --short HEAD) origin=$(git -C "$REPO" rev-parse --short origin/main) behind=$(git -C "$REPO" rev-list --count HEAD..origin/main) ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)"
git -C "$REPO" status --short | sed -n '1,120p'

log "Restarting all MGS gateways"
systemctl restart --no-block "${SERVICES[@]}"
sleep 20

log "Validating services"
systemctl is-active "${SERVICES[@]}"
systemctl show "${SERVICES[@]}" -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager

log "Recent gateway connection logs"
for p in zeus atena ares; do
  echo "--- $p agent.log ---"
  tail -120 "/root/.hermes/profiles/$p/logs/agent.log" 2>/dev/null | grep -E 'Connected as|Gateway running|discord connected|Logged in as|READY|resum' | tail -12 || true
  echo "--- $p errors.log ---"
  tail -80 "/root/.hermes/profiles/$p/logs/errors.log" 2>/dev/null | tail -12 || true
done

log "Codex auth sanitized"
python3 - <<'PY'
import json, pathlib
for name,path in [('root','/root/.hermes/auth.json'),('zeus','/root/.hermes/profiles/zeus/auth.json'),('atena','/root/.hermes/profiles/atena/auth.json'),('ares','/root/.hermes/profiles/ares/auth.json')]:
    p=pathlib.Path(path)
    if not p.exists():
        print(f'{name}: auth_missing')
        continue
    d=json.loads(p.read_text())
    prov=d.get('providers',{}).get('openai-codex',{})
    toks=prov.get('tokens',{}) if isinstance(prov,dict) else {}
    print(f"{name}: active={d.get('active_provider')} auth_mode={prov.get('auth_mode') if isinstance(prov,dict) else None} access_len={len(toks.get('access_token',''))} refresh_present={bool(toks.get('refresh_token'))}")
PY

FINAL_HEAD="$(git -C "$REPO" rev-parse --short HEAD)"
FINAL_ORIGIN="$(git -C "$REPO" rev-parse --short origin/main)"
FINAL_BEHIND="$(git -C "$REPO" rev-list --count HEAD..origin/main)"
STATUS_SHORT="$(git -C "$REPO" status --short | sed -n '1,30p')"
DISK="$(df -h / | awk 'NR==2{print $4 " livres / uso " $5}')"
log "DONE Hermes update all agents"
send_report "✅ Hermes update MGS concluído" "\`\`\`text\nHEAD:         $FINAL_HEAD\norigin/main:  $FINAL_ORIGIN\nbehind:       $FINAL_BEHIND\nGateways:     Zeus/Atena/Ares active\nPatch guard:  OK\npy_compile:   OK\nBackup:       $BACKUP_PATH\nDisco:        $DISK\nLog:          $LOG\n\nGit status:\n${STATUS_SHORT:-clean}\n\`\`\`\nValidação final feita no VPS; se esta mensagem chegou, Discord/gateway Zeus também voltou após restart." || true
