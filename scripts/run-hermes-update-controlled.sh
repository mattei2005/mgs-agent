#!/usr/bin/env bash
set -euo pipefail

# MGS controlled Hermes update
# Rule: backup + pre diff + upstream patch dry-run + update + post compare + MGS guard + validation.
# Defaults are conservative: no gateway restart unless RESTART_GATEWAYS=1.

BASE="${BASE:-/root/mgs-agent}"
REPO="${REPO:-/root/.hermes/hermes-agent}"
HERMES_BIN="${HERMES_BIN:-/root/.hermes/profiles/zeus/home/.local/bin/hermes}"
PATCH_DIR="$BASE/patches/hermes"
ENSURE_SCRIPT="$BASE/scripts/ensure-hermes-mgs-patches.sh"
STAMP="${STAMP:-$(date +%Y%m%d-%H%M%S)}"
REPORT_ROOT="${REPORT_ROOT:-$BASE/reports/hermes-updates}"
REPORT_DIR="${REPORT_DIR:-$REPORT_ROOT/$STAMP}"
LOG="$REPORT_DIR/run.log"
PRECHECK_ONLY="${PRECHECK_ONLY:-0}"
NO_UPDATE="${NO_UPDATE:-0}"
RESTART_GATEWAYS="${RESTART_GATEWAYS:-0}"
ALLOW_PATCH_DRIFT="${ALLOW_PATCH_DRIFT:-0}"
GATEWAY_SERVICES="${GATEWAY_SERVICES:-zeus-gateway.service atena-gateway.service ares-gateway.service hera-gateway.service}"

mkdir -p "$REPORT_DIR" "$PATCH_DIR"
exec > >(tee -a "$LOG") 2>&1

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
run_capture() {
  local outfile="$1"; shift
  log "CAPTURE $outfile :: $*"
  { "$@"; } > "$REPORT_DIR/$outfile" 2>&1 || true
}
write_failure_summary() {
  local rc="$1"
  local pre_head post_head pre_behind post_behind backup_file tail_file
  pre_head="$(grep '^head_short=' "$REPORT_DIR/pre-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  post_head="$(grep '^head_short=' "$REPORT_DIR/post-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  pre_behind="$(grep '^behind=' "$REPORT_DIR/pre-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  post_behind="$(grep '^behind=' "$REPORT_DIR/post-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  backup_file="$(ls -1 "$REPORT_DIR"/hermes-profiles-backup-*.tar.gz 2>/dev/null | head -1 || true)"
  tail_file="$REPORT_DIR/failure-tail.txt"
  tail -120 "$LOG" > "$tail_file" 2>/dev/null || true
  cat > "$REPORT_DIR/final-report.md" <<EOF
# Hermes controlled update report — $STAMP

Status: FAILED

Report summary:

    Report dir        $REPORT_DIR
    Exit code         $rc
    Pre HEAD          ${pre_head:-unknown}
    Post HEAD         ${post_head:-not-run}
    Pre behind        ${pre_behind:-unknown}
    Post behind       ${post_behind:-not-run}
    Backup            ${backup_file:-missing}
    Patch guard       $REPORT_DIR/patch-guard.log
    Failure tail      $tail_file
    Restart gateways  $RESTART_GATEWAYS
    Allow patch drift $ALLOW_PATCH_DRIFT
    Precheck only      $PRECHECK_ONLY

This report is written even on failure so Zeus can recover after gateway restart
and report the true terminal state instead of going silent.
EOF
}
fail() {
  local rc=$?
  trap - ERR
  log "FAILED rc=$rc line=${BASH_LINENO[0]}"
  write_failure_summary "$rc" || true
  log "Artifacts preserved in $REPORT_DIR"
  exit "$rc"
}
trap fail ERR

require_path() {
  [[ -e "$1" ]] || { log "Missing required path: $1"; exit 1; }
}

profile_backup() {
  local out="$REPORT_DIR/hermes-profiles-backup-$STAMP.tar.gz"
  log "Creating profiles backup: $out"
  tar --warning=no-file-changed \
    --exclude='*/logs/*' \
    --exclude='*/image_cache/*' \
    --exclude='*/audio_cache/*' \
    --exclude='*/__pycache__/*' \
    -czf "$out" /root/.hermes/profiles/ || true
  if [[ ! -s "$out" ]]; then
    log "Profiles backup failed or empty: $out"
    exit 1
  fi
  ls -lh "$out" | tee "$REPORT_DIR/backup-size.txt"
}

snapshot_pre_state() {
  log "Collecting pre-update state"
  run_capture pre-hermes-version.txt "$HERMES_BIN" --version
  git -C "$REPO" fetch --quiet origin main
  {
    echo "repo=$REPO"
    echo "head=$(git -C "$REPO" rev-parse HEAD)"
    echo "head_short=$(git -C "$REPO" rev-parse --short HEAD)"
    echo "origin_main=$(git -C "$REPO" rev-parse origin/main)"
    echo "origin_main_short=$(git -C "$REPO" rev-parse --short origin/main)"
    echo "behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
    echo "ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)"
  } | tee "$REPORT_DIR/pre-revisions.txt"
  git -C "$REPO" status --short > "$REPORT_DIR/pre-git-status.txt"
  git -C "$REPO" diff > "$REPORT_DIR/pre-local-diff.patch"
  git -C "$REPO" diff --stat > "$REPORT_DIR/pre-local-diff-stat.txt"
  git -C "$REPO" ls-files --others --exclude-standard > "$REPORT_DIR/pre-untracked-files.txt"
  run_capture pre-systemd-active.txt systemctl is-active $GATEWAY_SERVICES
  run_capture pre-systemd-show.txt systemctl show $GATEWAY_SERVICES -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
  run_capture pre-crontab-root.txt crontab -l
  if command -v hermes >/dev/null 2>&1; then
    run_capture pre-hermes-cron-list.txt hermes cron list
  else
    run_capture pre-hermes-cron-list.txt "$HERMES_BIN" cron list
  fi
}

snapshot_profiles_sanitized() {
  log "Collecting sanitized profile config/auth presence"
  python3 - <<'PY' > "$REPORT_DIR/pre-profiles-sanitized.txt"
import json, pathlib, re

def yaml_value(text, key_path):
    # Minimal dependency-free extractor for the simple nested keys we report.
    lines = text.splitlines()
    if len(key_path) == 1:
        pat = re.compile(rf'^\s*{re.escape(key_path[0])}:\s*(.*)$')
        for line in lines:
            m = pat.match(line)
            if m:
                return m.group(1).strip().strip('"\'') or '<present>'
        return None
    parent, child = key_path
    in_parent = False
    parent_indent = 0
    for line in lines:
        if re.match(rf'^\s*{re.escape(parent)}:\s*$', line):
            in_parent = True
            parent_indent = len(line) - len(line.lstrip())
            continue
        if in_parent:
            indent = len(line) - len(line.lstrip())
            if line.strip() and indent <= parent_indent:
                in_parent = False
            m = re.match(rf'^\s*{re.escape(child)}:\s*(.*)$', line)
            if in_parent and m:
                return m.group(1).strip().strip('"\'') or '<present>'
    return None

for name in ['zeus','atena','ares','hera']:
    base = pathlib.Path('/root/.hermes/profiles')/name
    print(f'[{name}]')
    cfg = base/'config.yaml'
    if cfg.exists():
        text = cfg.read_text(errors='replace')
        print('  model.provider:', yaml_value(text, ['model','provider']))
        print('  model.default:', yaml_value(text, ['model','default']))
        print('  compression.threshold:', yaml_value(text, ['compression','threshold']))
        print('  config_present: true')
    else:
        print('  config: missing')
    auth = base/'auth.json'
    if auth.exists():
        try:
            a=json.loads(auth.read_text())
            providers=a.get('providers') or {}
            print('  active_provider:', a.get('active_provider'))
            print('  openai_codex_present:', 'openai-codex' in providers)
            p=providers.get('openai-codex') or {}
            toks=p.get('tokens') or {}
            print('  openai_codex_access_len:', len(toks.get('access_token') or ''))
            print('  openai_codex_refresh_present:', bool(toks.get('refresh_token')))
        except Exception as e:
            print('  auth_parse_error:', type(e).__name__)
    else:
        print('  auth: missing')
PY
}

readonly_invariant_check() {
  log "Running read-only MGS invariant check"
  local adapter="$REPO/plugins/platforms/discord/adapter.py"
  local runpy="$REPO/gateway/run.py"
  local rc=0
  {
    for spec in \
      "$adapter::def _auto_thread_name_from_message" \
      "$adapter::DISCORD_THREAD_AUTO_ADD_USERS" \
      "$adapter::Auto-thread member sync" \
      "$adapter::Auto-thread skipped for REPORT-INFRA control-plane message" \
      "$adapter::Ignoring gateway lifecycle notice from bot" \
      "$runpy::service-manager restarts while a chat task is active" \
      "$runpy::Internal restart recovery checkpoint" \
      "$runpy::Do not re-run" \
      "$runpy::_schedule_discord_thread_title_rename" \
      "$runpy::_discord_thread_safe_to_autorename" \
      "$runpy::_discord_title_message_from_gateway_text" \
      "$runpy::Shutdown notification suppressed for bot-originated Discord session"; do
      file="${spec%%::*}"
      needle="${spec#*::}"
      if [[ -f "$file" ]] && grep -q "$needle" "$file"; then
        echo "OK $needle"
      else
        echo "MISSING $needle in $file"
        rc=1
      fi
    done
  } | tee "$REPORT_DIR/pre-readonly-invariants.txt"
  local pybin="$REPO/venv/bin/python"
  [[ -x "$pybin" ]] || pybin="python3"
  "$pybin" -m py_compile "$adapter" "$runpy" > "$REPORT_DIR/pre-readonly-py-compile.log" 2>&1 || rc=1
  return "$rc"
}

check_patches_against_upstream() {
  log "Checking canonical MGS patches against origin/main in temporary worktree"
  local wt="$REPORT_DIR/upstream-worktree"
  git -C "$REPO" worktree add --detach "$wt" origin/main > "$REPORT_DIR/worktree-add.txt" 2>&1
  local rc=0
  {
    local canonical_patches=(
      "discord-deterministic-thread-rename-auto-add-users.patch"
      "planned-restart-auto-resume-active-sessions.patch"
      "restart-recovery-checkpoint-idempotent.patch"
      "discord-post-response-thread-title-rename.patch"
      "discord-new-thread-ai-title-once.patch"
      "discord-thread-title-deduplicate-safe-autorename.patch"
      "discord-bot-gateway-lifecycle-loop-guard.patch"
      "discord-report-infra-no-auto-thread.patch"
    )
    for name in "${canonical_patches[@]}"; do
      patch="$PATCH_DIR/$name"
      if [[ ! -s "$patch" ]]; then
        echo "MISSING $name"
        rc=1
        continue
      fi
      if git -C "$wt" apply --check "$patch" >/tmp/mgs-patch-check.out 2>&1; then
        echo "OK apply-clean $name"
      else
        echo "DRIFT $name"
        sed 's/^/  /' /tmp/mgs-patch-check.out
        rc=1
      fi
    done
  } | tee "$REPORT_DIR/pre-upstream-patch-check.txt"
  git -C "$REPO" worktree remove --force "$wt" >> "$REPORT_DIR/worktree-add.txt" 2>&1 || true
  if [[ "$rc" != 0 ]]; then
    log "Patch check found drift. This is not always fatal if invariants already exist, but update must be treated as controlled/manual. See pre-upstream-patch-check.txt"
  fi
  return "$rc"
}

run_update() {
  if [[ "$PRECHECK_ONLY" == "1" || "$NO_UPDATE" == "1" ]]; then
    log "Skipping mutation: PRECHECK_ONLY=$PRECHECK_ONLY NO_UPDATE=$NO_UPDATE"
    return 0
  fi
  log "Saving tracked local diff to canonical archive"
  cp "$REPORT_DIR/pre-local-diff.patch" "$PATCH_DIR/mgs-local-preupdate-$STAMP.patch"
  log "Resetting tracked local changes before update; untracked files preserved"
  git -C "$REPO" reset --hard HEAD
  log "Running Hermes update with built-in backup disabled because MGS backup already exists"
  "$HERMES_BIN" update --yes --no-backup
}

post_validate() {
  log "Collecting post-update state"
  git -C "$REPO" fetch --quiet origin main
  run_capture post-hermes-version.txt "$HERMES_BIN" --version
  {
    echo "head=$(git -C "$REPO" rev-parse HEAD)"
    echo "head_short=$(git -C "$REPO" rev-parse --short HEAD)"
    echo "origin_main=$(git -C "$REPO" rev-parse origin/main)"
    echo "origin_main_short=$(git -C "$REPO" rev-parse --short origin/main)"
    echo "behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)"
    echo "ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)"
  } | tee "$REPORT_DIR/post-revisions.txt"
  git -C "$REPO" status --short > "$REPORT_DIR/post-git-status.txt"
  git -C "$REPO" diff --stat > "$REPORT_DIR/post-local-diff-stat.txt"

  log "Running MGS patch guard"
  BASE="$BASE" REPO="$REPO" LOG="$REPORT_DIR/patch-guard.log" "$ENSURE_SCRIPT"

  log "Compiling critical files"
  local pybin="$REPO/venv/bin/python"
  [[ -x "$pybin" ]] || pybin="python3"
  "$pybin" -m py_compile \
    "$REPO/plugins/platforms/discord/adapter.py" \
    "$REPO/gateway/run.py" \
    "$REPO/gateway/config.py" \
    "$REPO/tools/terminal_tool.py" \
    "$REPO/tools/file_tools.py" \
    > "$REPORT_DIR/py-compile.log" 2>&1

  run_capture post-systemd-active.txt systemctl is-active $GATEWAY_SERVICES
  run_capture post-systemd-show.txt systemctl show $GATEWAY_SERVICES -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager
}

restart_if_requested() {
  if [[ "$RESTART_GATEWAYS" != "1" ]]; then
    log "Gateway restart not requested. Set RESTART_GATEWAYS=1 to restart after validation."
    return 0
  fi
  log "Restarting gateways with --no-block: $GATEWAY_SERVICES"
  systemctl restart --no-block $GATEWAY_SERVICES
  sleep 20
  systemctl is-active $GATEWAY_SERVICES | tee "$REPORT_DIR/post-restart-active.txt"
  systemctl show $GATEWAY_SERVICES -p Id -p ActiveState -p MainPID -p NRestarts -p ExecMainStatus --no-pager | tee "$REPORT_DIR/post-restart-systemd-show.txt"
}

write_summary() {
  local pre_head post_head pre_behind post_behind backup_file
  pre_head="$(grep '^head_short=' "$REPORT_DIR/pre-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  post_head="$(grep '^head_short=' "$REPORT_DIR/post-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  pre_behind="$(grep '^behind=' "$REPORT_DIR/pre-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  post_behind="$(grep '^behind=' "$REPORT_DIR/post-revisions.txt" 2>/dev/null | cut -d= -f2 || true)"
  backup_file="$(ls -1 "$REPORT_DIR"/hermes-profiles-backup-*.tar.gz 2>/dev/null | head -1 || true)"
  cat > "$REPORT_DIR/final-report.md" <<EOF
# Hermes controlled update report — $STAMP

Report summary:

    Report dir        $REPORT_DIR
    Pre HEAD          ${pre_head:-unknown}
    Post HEAD         ${post_head:-not-run}
    Pre behind        ${pre_behind:-unknown}
    Post behind       ${post_behind:-not-run}
    Backup            ${backup_file:-missing}
    Patch guard       $REPORT_DIR/patch-guard.log
    Restart gateways  $RESTART_GATEWAYS
    Allow patch drift $ALLOW_PATCH_DRIFT
    Precheck only      $PRECHECK_ONLY

Required evidence files:

    pre-revisions.txt
    pre-git-status.txt
    pre-local-diff.patch
    pre-upstream-patch-check.txt
    pre-profiles-sanitized.txt
    post-revisions.txt
    post-git-status.txt
    post-local-diff-stat.txt
    patch-guard.log
    py-compile.log
    post-systemd-active.txt
EOF
  log "Summary written: $REPORT_DIR/final-report.md"
}

main() {
  require_path "$REPO/.git"
  require_path "$PATCH_DIR"
  require_path "$ENSURE_SCRIPT"
  log "START MGS controlled Hermes update"
  log "REPORT_DIR=$REPORT_DIR"
  log "PRECHECK_ONLY=$PRECHECK_ONLY NO_UPDATE=$NO_UPDATE RESTART_GATEWAYS=$RESTART_GATEWAYS ALLOW_PATCH_DRIFT=$ALLOW_PATCH_DRIFT"
  profile_backup
  snapshot_pre_state
  snapshot_profiles_sanitized
  patch_check_rc=0
  check_patches_against_upstream || patch_check_rc=$?
  if [[ "$patch_check_rc" != 0 && "$PRECHECK_ONLY" != "1" && "$ALLOW_PATCH_DRIFT" != "1" ]]; then
    log "FAIL-CLOSED: canonical patch drift detected before update. Set ALLOW_PATCH_DRIFT=1 only after manual port/review."
    false
  fi
  if [[ "$PRECHECK_ONLY" == "1" ]]; then
    readonly_invariant_check || log "WARN read-only invariant check found missing markers; inspect $REPORT_DIR/pre-readonly-invariants.txt"
    write_summary
    log "DONE precheck only"
    return 0
  fi
  run_update
  post_validate
  # Write a durable success report before gateway restart. Restarting Zeus can
  # terminate this process before it has a chance to speak in Discord; the
  # recovery turn must read this report and deliver it instead of going silent.
  write_summary
  restart_if_requested
  write_summary
  log "DONE MGS controlled Hermes update"
}

main "$@"
