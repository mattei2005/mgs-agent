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
    mgs-runtime-customizations-*.patch|discord-deterministic-thread-rename-auto-add-users.patch)
      if grep -q "def _auto_thread_name_from_message" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "DISCORD_THREAD_AUTO_ADD_USERS" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "Auto-thread member sync" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "_append_thread_author_suffix" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "_append_discord_thread_author_suffix" "$REPO/gateway/run.py" \
        && grep -q "AUTO_ATTACH_LOCAL_FILES_ENV" "$REPO/gateway/platforms/base.py"; then
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
    restart-recovery-checkpoint-idempotent.patch)
      if grep -q "Internal restart recovery checkpoint" "$REPO/gateway/run.py" \
        && grep -q "Do not re-run" "$REPO/gateway/run.py"; then
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
    discord-new-thread-ai-title-once.patch)
      if grep -q "_remember_auto_thread_initial_title" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "_discord_thread_safe_to_autorename" "$REPO/gateway/run.py" \
        && grep -q "_discord_title_message_from_gateway_text" "$REPO/gateway/run.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    discord-bot-gateway-lifecycle-loop-guard.patch)
      if grep -q "Shutdown notification suppressed for bot-originated Discord session" "$REPO/gateway/run.py" \
        && grep -q "Ignoring gateway lifecycle notice from bot" "$REPO/plugins/platforms/discord/adapter.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    discord-report-infra-no-auto-thread.patch)
      if grep -q "Auto-thread skipped for REPORT-INFRA control-plane message" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "is_report_infra_message" "$REPO/plugins/platforms/discord/adapter.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    discord-suppress-link-previews.patch)
      if grep -q "DISCORD_SUPPRESS_LINK_PREVIEWS" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "def _plain_message_send_kwargs" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "test_edit_preserves_suppressed_link_preview_flag" "$REPO/tests/gateway/test_discord_send.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-auto-reasoning-routing.patch)
      if grep -q "def _resolve_turn_reasoning_config" "$REPO/gateway/run.py" \
        && grep -q "def route_reasoning_config" "$REPO/gateway/reasoning_router.py" \
        && grep -q "Auto: ON (medium/high/xhigh; global = fallback)" "$REPO/gateway/slash_commands.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-universal-media-*.patch)
      if grep -q "async def _prepare_busy_steer_payload" "$REPO/gateway/run.py" \
        && grep -q "for_mid_turn_steer" "$REPO/gateway/run.py" \
        && grep -q "Image attached at:" "$REPO/gateway/run.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-startup-merge-*.patch)
      if grep -q "def _merge_startup_steer_into_message" "$REPO/gateway/run.py" \
        && grep -Eq "def _stash_startup_steer|def _reserve_startup_steer" "$REPO/gateway/run.py" \
        && grep -q "test_steer_mode_buffers_current_turn_when_agent_pending" "$REPO/tests/gateway/test_busy_session_ack.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-startup-race-hardening-*.patch)
      if grep -q "def _promote_agent_and_consume_startup_steers" "$REPO/gateway/run.py" \
        && grep -q "async def _try_busy_steer_event" "$REPO/gateway/run.py" \
        && grep -q "test_startup_barrier_waits_and_preserves_arrival_order" "$REPO/tests/gateway/test_busy_session_ack.py" \
        && grep -q "test_async_prepare_does_not_steer_into_replaced_agent" "$REPO/tests/gateway/test_busy_session_ack.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    skill-view-compact-linked-files.patch)
      if grep -q "def _linked_files_for_view" "$REPO/tools/skills_tool.py" \
        && grep -q '"linked_files_summary"' "$REPO/tools/skills_tool.py" \
        && grep -q "test_view_compacts_large_linked_file_inventory" "$REPO/tests/tools/test_skills_tool.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    discord-thread-title-author-suffix.patch)
      if grep -q "_append_thread_author_suffix" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "_append_discord_thread_author_suffix" "$REPO/gateway/run.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
  esac

  fail "patch does not apply cleanly and is not already applied: $name"
}

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || fail "Hermes repo not found: $REPO"
[[ -d "$PATCH_DIR" ]] || fail "patch dir not found: $PATCH_DIR"

log "START ensure Hermes MGS patches"
log "repo=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"

# Consolidated port for Hermes v0.18.0+ after the 2026-07-07 controlled update.
# This applies the complete MGS runtime customization surface to a clean
# upstream checkout first; legacy per-feature patches below then act as
# invariant checks/backward-compatible fallback.
apply_patch_if_needed "mgs-runtime-customizations-2026-07-07.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-05.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-30.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-26.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-20.patch"

apply_patch_if_needed "discord-deterministic-thread-rename-auto-add-users.patch"
apply_patch_if_needed "planned-restart-auto-resume-active-sessions.patch"
apply_patch_if_needed "restart-recovery-checkpoint-idempotent.patch"
apply_patch_if_needed "discord-post-response-thread-title-rename.patch"
apply_patch_if_needed "discord-new-thread-ai-title-once.patch"
apply_patch_if_needed "discord-thread-title-deduplicate-safe-autorename.patch"
apply_patch_if_needed "discord-bot-gateway-lifecycle-loop-guard.patch"
apply_patch_if_needed "discord-report-infra-no-auto-thread.patch"
apply_patch_if_needed "discord-thread-title-author-suffix.patch"
apply_patch_if_needed "discord-suppress-link-previews.patch"
apply_patch_if_needed "mgs-auto-reasoning-routing.patch"
apply_patch_if_needed "mgs-busy-steer-universal-media-2026-07-10.patch"
apply_patch_if_needed "mgs-busy-steer-startup-merge-2026-07-11.patch"
apply_patch_if_needed "mgs-busy-steer-startup-race-hardening-2026-07-11.patch"
apply_patch_if_needed "skill-view-compact-linked-files.patch"

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
grep -q "Internal restart recovery checkpoint" "$REPO/gateway/run.py" \
  || fail "missing idempotent restart recovery checkpoint"
grep -q "Do not re-run" "$REPO/gateway/run.py" \
  || fail "missing restart recovery anti-reexecution instruction"
grep -q "_schedule_discord_thread_title_rename" "$REPO/gateway/run.py" \
  || fail "missing Discord post-response thread rename callback"
grep -Eq "Discord thread renamed from auto-generated title|Discord GPT-style thread title applied" "$REPO/gateway/run.py" \
  || fail "missing Discord thread rename audit log marker"
grep -q "_remember_auto_thread_initial_title" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord exact provisional title memory"
grep -q "_discord_thread_safe_to_autorename" "$REPO/gateway/run.py" \
  || fail "missing Discord one-time AI title rename guard"
grep -q "_discord_title_message_from_gateway_text" "$REPO/gateway/run.py" \
  || fail "missing Discord title-generator text cleanup"

[[ $(grep -c "async def _rename_discord_thread_for_session_title" "$REPO/gateway/run.py") == "1" ]] \
  || fail "duplicate/absent Discord thread rename function"
[[ $(grep -c "def _schedule_discord_thread_title_rename" "$REPO/gateway/run.py") == "1" ]] \
  || fail "duplicate/absent Discord thread title scheduler"
[[ $(grep -c "async def _discord_thread_safe_to_autorename" "$REPO/gateway/run.py") == "1" ]] \
  || fail "duplicate/absent Discord safe autorename guard"
[[ $(grep -c "def _is_discord_thread_lane" "$REPO/gateway/run.py") == "1" ]] \
  || fail "duplicate/absent Discord thread-lane helper"
[[ $(grep -c "def _sanitize_discord_thread_title" "$REPO/gateway/run.py") == "1" ]] \
  || fail "duplicate/absent Discord title sanitizer"
[[ $(grep -c "MGS AI-generated session title" "$REPO/gateway/run.py") == "1" ]] \
  || fail "missing/duplicate MGS Discord rename reason"
[[ $(grep -c "Hermes auto-generated session title" "$REPO/gateway/run.py") == "0" ]] \
  || fail "unsafe legacy Discord rename reason still present"
grep -q "Auto-thread skipped for REPORT-INFRA control-plane message" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord REPORT-INFRA inline/no-thread guard"
grep -q "Ignoring gateway lifecycle notice from bot" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord bot lifecycle notice ignore guard"
grep -q "Shutdown notification suppressed for bot-originated Discord session" "$REPO/gateway/run.py" \
  || fail "missing Discord bot-originated shutdown notification suppressor"
grep -q "DISCORD_SUPPRESS_LINK_PREVIEWS" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord suppress-link-previews config bridge"
grep -q "def _plain_message_send_kwargs" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord plain-message link-preview suppression helper"
grep -q "test_edit_preserves_suppressed_link_preview_flag" "$REPO/tests/gateway/test_discord_send.py" \
  || fail "missing Discord link-preview suppression regression tests"

grep -q "AUTO_ATTACH_LOCAL_FILES_ENV" "$REPO/gateway/platforms/base.py" \
  || fail "missing Discord/local file auto-attach safety gate"
grep -q "_auto_attach_local_files_enabled" "$REPO/gateway/platforms/base.py" \
  || fail "missing local file auto-attach helper"
grep -q "codex response remained incomplete" "$REPO/gateway/run.py" \
  || fail "missing Discord Codex incomplete/no-content noise filter"
grep -q "_DISCORD_BOT_LOOP_NOISE_MARKERS" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord multi-agent loop-noise marker set"
grep -q "_is_discord_bot_loop_noise" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord multi-agent loop-noise filter"
grep -q "_append_thread_author_suffix" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord initial thread author suffix"
grep -q "_append_discord_thread_author_suffix" "$REPO/gateway/run.py" \
  || fail "missing Discord AI title author suffix"
grep -q "async def delete_message" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord delete_message cleanup_progress support"
grep -q "def _resolve_turn_reasoning_config" "$REPO/gateway/run.py" \
  || fail "missing MGS per-turn reasoning router integration"
grep -q "def route_reasoning_config" "$REPO/gateway/reasoning_router.py" \
  || fail "missing MGS deterministic reasoning router"
grep -q "async def _prepare_busy_steer_payload" "$REPO/gateway/run.py" \
  || fail "missing MGS universal busy-steer media normalizer"
grep -q "for_mid_turn_steer" "$REPO/gateway/run.py" \
  || fail "missing MGS mid-turn media enrichment mode"
grep -q "def _reserve_startup_steer" "$REPO/gateway/run.py" \
  || fail "missing MGS ordered startup steer reservation"
grep -q "def _promote_agent_and_consume_startup_steers" "$REPO/gateway/run.py" \
  || fail "missing MGS atomic startup steer barrier/promotion"
grep -q "async def _try_busy_steer_event" "$REPO/gateway/run.py" \
  || fail "missing MGS stale-agent revalidation for busy steer"
grep -q "def _merge_startup_steer_into_message" "$REPO/gateway/run.py" \
  || fail "missing MGS startup steer same-turn merge"
grep -q "test_steer_mode_buffers_current_turn_when_agent_pending" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing MGS startup steer regression test"
grep -q "test_startup_barrier_waits_and_preserves_arrival_order" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing MGS startup steer async FIFO/barrier test"
grep -q "test_async_prepare_does_not_steer_into_replaced_agent" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing MGS stale-agent busy steer regression test"
grep -q "Image attached at:" "$REPO/gateway/run.py" \
  || fail "missing MGS mid-turn image path marker"
grep -q "def _linked_files_for_view" "$REPO/tools/skills_tool.py" \
  || fail "missing compact linked-files skill_view helper"
grep -q '"linked_files_summary"' "$REPO/tools/skills_tool.py" \
  || fail "missing compact linked-files summary result"
grep -q "test_view_compacts_large_linked_file_inventory" "$REPO/tests/tools/test_skills_tool.py" \
  || fail "missing compact linked-files regression tests"

PYBIN="$REPO/venv/bin/python"
[[ -x "$PYBIN" ]] || PYBIN="python3"
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/slash_commands.py" \
  "$REPO/gateway/reasoning_router.py" \
  "$REPO/gateway/platforms/base.py" \
  "$REPO/tools/skills_tool.py"

"$PYBIN" -m pytest -q \
  "$REPO/tests/gateway/test_busy_session_ack.py" \
  "$REPO/tests/gateway/test_discord_send.py" \
  "$REPO/tests/gateway/test_telegram_photo_interrupts.py" \
  "$REPO/tests/tools/test_skills_tool.py"

log "OK Hermes MGS patches present, py_compile and busy-steer tests passed"
