#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-/root/mgs-agent}"
REPO="${REPO:-/root/.hermes/hermes-agent}"
PATCH_DIR="$BASE/patches/hermes"
LOG="${LOG:-$BASE/logs/ensure-hermes-mgs-patches.log}"
mkdir -p "$(dirname "$LOG")"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG"; }

fail() {
  log "FAIL: $*"
  exit 1
}

apply_patch_if_needed() {
  local name="$1"
  local patch="$PATCH_DIR/$name"
  [[ -s "$patch" ]] || fail "missing patch artifact: $patch"

  if git -C "$REPO" apply --reverse --check "$patch" >/dev/null 2>&1; then
    log "patch already applied: $name"
    return 0
  fi

  if git -C "$REPO" apply --check "$patch" >/dev/null 2>&1; then
    log "applying patch: $name"
    git -C "$REPO" apply "$patch"
    return 0
  fi

  # Some MGS patch bundles are supersets/composites after manual ports. In that
  # state `git apply --reverse --check` can fail because context drifted, even
  # though the required production invariants are already present. Treat those
  # known invariant-positive states as applied so the watchdog remains useful
  # instead of false-failing forever.
  case "$name" in
    discord-deterministic-thread-rename-auto-add-users.patch)
      if grep -q "def _auto_thread_name_from_message" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "DISCORD_THREAD_AUTO_ADD_USERS" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "Auto-thread member sync" "$REPO/plugins/platforms/discord/adapter.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    planned-restart-auto-resume-active-sessions.patch)
      if grep -q "service-manager restarts while a chat task is active" "$REPO/gateway/run.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    discord-post-response-thread-title-rename.patch)
      if grep -q "_schedule_discord_thread_title_rename" "$REPO/gateway/run.py" \
        && grep -Eq "Discord thread renamed from auto-generated title|Discord GPT-style thread title applied" "$REPO/gateway/run.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
  esac

  fail "patch does not apply cleanly and is not already applied: $name"
}

[[ -d "$REPO/.git" ]] || fail "Hermes repo not found: $REPO"
[[ -d "$PATCH_DIR" ]] || fail "patch dir not found: $PATCH_DIR"

log "START ensure Hermes MGS patches"
log "repo=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"

apply_patch_if_needed "discord-deterministic-thread-rename-auto-add-users.patch"
apply_patch_if_needed "planned-restart-auto-resume-active-sessions.patch"
apply_patch_if_needed "discord-post-response-thread-title-rename.patch"
apply_patch_if_needed "discord-report-infra-no-auto-thread.patch"

# Invariants that must survive every Hermes update. If any grep fails, the
# update is not production-safe for MGS gateways.
grep -q "def _auto_thread_name_from_message" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord deterministic thread naming helper"
grep -q "DISCORD_THREAD_AUTO_ADD_USERS" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord explicit thread auto-add support"
grep -q "Auto-thread member sync" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord auto-thread member sync log marker"
grep -q "semantic_fallback_title" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord semantic title fallback"
grep -q "Formatação de Tabelas" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord table-formatting title classifier"
grep -q "Erro Sistema Operacional" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord OS-error title classifier"
grep -q "service-manager restarts while a chat task is active" "$REPO/gateway/run.py" \
  || fail "missing restart/service-manager auto-resume marker"
grep -q "_schedule_discord_thread_title_rename" "$REPO/gateway/run.py" \
  || fail "missing Discord post-response thread rename callback"
grep -Eq "Discord thread renamed from auto-generated title|Discord GPT-style thread title applied" "$REPO/gateway/run.py" \
  || fail "missing Discord thread rename audit log marker"

PYBIN="$REPO/venv/bin/python"
[[ -x "$PYBIN" ]] || PYBIN="python3"
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py"

log "OK Hermes MGS patches present and py_compile passed"
