#!/usr/bin/env bash
set -Eeuo pipefail

BASE=/root/mgs-agent
REPO=/root/.hermes/hermes-agent
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$BASE/logs/hermes-update-execute-${STAMP}.log"
BACKUP_DIR="$BASE/backups/hermes-update-${STAMP}"
PATCH_DIR="$BASE/patches/hermes"
mkdir -p "$(dirname "$LOG")" "$BACKUP_DIR" "$PATCH_DIR"
exec > >(tee -a "$LOG") 2>&1

log(){ printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
run(){ log "+ $*"; "$@"; }

log "START Hermes controlled update execute"
log "repo=$REPO"
log "backup_dir=$BACKUP_DIR"

log "Pre-state"
hermes --version 2>&1 | sed -n '1,12p' || true
git -C "$REPO" fetch --quiet origin main
PRE_HEAD=$(git -C "$REPO" rev-parse --short HEAD)
PRE_ORIGIN=$(git -C "$REPO" rev-parse --short origin/main)
PRE_BEHIND=$(git -C "$REPO" rev-list --count HEAD..origin/main)
log "pre HEAD=$PRE_HEAD origin=$PRE_ORIGIN behind=$PRE_BEHIND"
git -C "$REPO" status --short | sed -n '1,80p'
df -h /

log "Backing up profiles/config/auth excluding volatile caches/logs"
tar --warning=no-file-changed --ignore-failed-read \
  --exclude='/root/.hermes/profiles/*/cache' \
  --exclude='/root/.hermes/profiles/*/logs' \
  --exclude='/root/.hermes/profiles/*/sessions' \
  -czf "$BACKUP_DIR/hermes-profiles-config-auth.tar.gz" \
  /root/.hermes/profiles/*/config.yaml \
  /root/.hermes/profiles/*/auth.json \
  /root/.hermes/profiles/*/SOUL.md \
  /root/.hermes/auth.json 2>/dev/null || true
ls -lh "$BACKUP_DIR/hermes-profiles-config-auth.tar.gz" || true

log "Saving local tracked diff and untracked files list"
git -C "$REPO" diff > "$BACKUP_DIR/hermes-local-tracked-diff.patch" || true
git -C "$REPO" status --porcelain=v1 > "$BACKUP_DIR/hermes-status-pre.txt" || true
git -C "$REPO" ls-files --others --exclude-standard > "$BACKUP_DIR/hermes-untracked-files.txt" || true
if [[ -s "$BACKUP_DIR/hermes-untracked-files.txt" ]]; then
  tar -C "$REPO" -czf "$BACKUP_DIR/hermes-untracked-files.tar.gz" -T "$BACKUP_DIR/hermes-untracked-files.txt" || true
fi

log "Validating current patch guard before mutation"
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh

log "Resetting tracked changes and cleaning untracked files after backup"
git -C "$REPO" reset --hard HEAD
git -C "$REPO" clean -fd

log "Pulling upstream fast-forward"
git -C "$REPO" pull --ff-only origin main

log "Reinstalling Python dependencies"
PYBIN="$REPO/venv/bin/python"
if [[ ! -x "$PYBIN" ]]; then PYBIN=python3; fi
if command -v uv >/dev/null 2>&1 && [[ -x "$REPO/venv/bin/python" ]]; then
  uv pip install --python "$REPO/venv/bin/python" -e "${REPO}[all]"
else
  "$PYBIN" -m pip install -e "${REPO}[all]"
fi

log "Installing/building npm workspaces where present"
if [[ -f "$REPO/package.json" ]]; then
  (cd "$REPO" && npm install --no-fund --no-audit)
fi
if [[ -f "$REPO/ui-tui/package.json" ]]; then
  (cd "$REPO/ui-tui" && npm install --no-fund --no-audit)
fi
if [[ -f "$REPO/web/package.json" ]]; then
  (cd "$REPO/web" && npm install --no-fund --no-audit)
fi

log "Applying/validating MGS Hermes patches"
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh

log "Clearing update_check caches"
find /root/.hermes -name '.update_check' -type f -print -delete 2>/dev/null | sed -n '1,40p' || true

log "Compiling critical files"
PYBIN="$REPO/venv/bin/python"; [[ -x "$PYBIN" ]] || PYBIN=python3
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/config.py" \
  "$REPO/tools/send_message_tool.py" \
  "$REPO/tools/discord_tool.py"

log "Running targeted tests"
(
  cd "$REPO"
  DISCORD_ALLOWED_CHANNELS='*' "$PYBIN" -m pytest -q \
    tests/gateway/test_gateway_shutdown.py \
    tests/gateway/test_restart_resume_pending.py \
    tests/gateway/test_discord_free_response.py
)

log "Post-update status before restart"
git -C "$REPO" fetch --quiet origin main
POST_HEAD=$(git -C "$REPO" rev-parse --short HEAD)
POST_ORIGIN=$(git -C "$REPO" rev-parse --short origin/main)
POST_BEHIND=$(git -C "$REPO" rev-list --count HEAD..origin/main)
log "post HEAD=$POST_HEAD origin=$POST_ORIGIN behind=$POST_BEHIND"
git -C "$REPO" status --short | sed -n '1,80p'
hermes --version 2>&1 | sed -n '1,12p' || true

log "Scheduling no-block restart for all MGS gateways via systemd-run"
FINALIZER="$BACKUP_DIR/restart-and-validate.sh"
cat > "$FINALIZER" <<'EOS'
#!/usr/bin/env bash
set -Eeuo pipefail
LOG="$1"
REPO=/root/.hermes/hermes-agent
{
  printf '[%s] FINALIZER start gateway restart\n' "$(date -Iseconds)"
  systemctl restart --no-block zeus-gateway.service atena-gateway.service ares-gateway.service
  sleep 25
  printf '[%s] FINALIZER services\n' "$(date -Iseconds)"
  systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service mgs-autocommit.service cron.service || true
  systemctl show zeus-gateway.service atena-gateway.service ares-gateway.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
  printf '[%s] FINALIZER patch guard\n' "$(date -Iseconds)"
  /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh || true
  printf '[%s] FINALIZER version\n' "$(date -Iseconds)"
  hermes --version 2>&1 | sed -n '1,8p' || true
  printf '[%s] FINALIZER done\n' "$(date -Iseconds)"
} >> "$LOG" 2>&1
EOS
chmod +x "$FINALIZER"
systemd-run --unit "mgs-hermes-update-finalizer-${STAMP}" --property=Type=oneshot "$FINALIZER" "$LOG"

log "DONE main update path; finalizer launched"
log "log=$LOG"
log "backup_dir=$BACKUP_DIR"
