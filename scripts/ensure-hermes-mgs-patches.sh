#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-/root/mgs-agent}"
HERMES_BIN="${HERMES_BIN:-/root/.local/bin/hermes}"
resolve_active_hermes_repo() {
  local launcher shebang python_path candidate
  launcher="$(readlink -f "$HERMES_BIN")"
  [[ -f "$launcher" ]] || return 1
  shebang="$(head -n 1 "$launcher")"
  python_path="${shebang#\#!}"
  candidate="$(dirname "$(dirname "$(dirname "$python_path")")")"
  [[ -f "$candidate/gateway/run.py" && -x "$candidate/venv/bin/python" ]] || return 1
  printf '%s\n' "$candidate"
}
REPO="${REPO:-$(resolve_active_hermes_repo)}"
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
      if { grep -q "Internal restart recovery checkpoint" "$REPO/gateway/run.py" \
          && grep -q "Do not re-run" "$REPO/gateway/run.py"; } \
        || grep -q "Internal continuation event" "$REPO/gateway/run.py"; then
        log "patch invariants already present or superseded: $name"
        return 0
      fi
      ;;
    restart-recovery-natural-continuation-*.patch)
      if grep -Fq '_internal_auto_resume = bool(getattr(event, "internal", False))' "$REPO/gateway/run.py"; then
        /usr/bin/python3 - "$REPO/gateway/run.py" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
broken = '_internal_auto_resume = bool(getattr(event, "internal", False))'
fixed = '''_internal_auto_resume = bool(
                    isinstance(message, str)
                    and message.startswith("[Internal continuation event:")
                )'''
if text.count(broken) != 1:
    raise SystemExit(f"unexpected broken auto-resume marker count: {text.count(broken)}")
path.write_text(text.replace(broken, fixed, 1))
PY
        log "repaired undefined event reference in nested restart-resume worker: $name"
      fi
      if grep -q "Internal continuation event" "$REPO/gateway/run.py" \
        && grep -q 'message.startswith("\[Internal continuation event:")' "$REPO/gateway/run.py" \
        && grep -q "finish every outstanding" "$REPO/gateway/run.py" \
        && grep -q "chronological order" "$REPO/gateway/run.py" \
        && ! grep -Fq '_internal_auto_resume = bool(getattr(event, "internal", False))' "$REPO/gateway/run.py"; then
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
    discord-thread-auto-add-by-channel-*.patch)
      if grep -q "def _discord_thread_auto_add_user_ids" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL" "$REPO/plugins/platforms/discord/adapter.py" \
        && grep -q "test_auto_add_is_scoped_to_parent_channel" "$REPO/tests/gateway/test_discord_thread_auto_add_by_channel.py"; then
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
    mgs-busy-steer-reentrant-followup-*.patch)
      if grep -q "direct_unclaimed_run = current_agent is None" "$REPO/gateway/run.py" \
        && grep -q "Skipping stale startup agent promotion" "$REPO/gateway/run.py" \
        && grep -q "test_reentrant_followup_promotion_reuses_current_agent" "$REPO/tests/gateway/test_busy_session_ack.py" \
        && grep -q "test_reentrant_followup_does_not_mask_replaced_agent" "$REPO/tests/gateway/test_busy_session_ack.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-reentrant-rebuild-*.patch)
      if grep -Eq 'allow_same_generation_replacement=(ctx\.)?_interrupt_depth > 0' "$REPO/gateway/run.py" \
        && grep -q "test_reentrant_followup_transfers_same_generation_rebuilt_agent" "$REPO/tests/gateway/test_busy_session_ack.py" \
        && grep -q "test_recursive_run_enables_same_generation_replacement" "$REPO/tests/gateway/test_busy_session_ack.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-pending-turn-fifo-*.patch)
      if grep -q "def _merge_leftover_steer_into_pending_turn" "$REPO/gateway/run.py" \
        && grep -q "Merging leftover /steer into earlier queued turn" "$REPO/gateway/run.py" \
        && grep -q "test_run_agent_merges_leftover_steer_into_earlier_queued_turn" "$REPO/tests/gateway/test_run_progress_topics.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    mgs-busy-steer-ack-ptbr-*.patch)
      if grep -q "Mensagem adicionada à execução atual" "$REPO/gateway/run.py" \
        && grep -q "Vou considerá-la no próximo passo" "$REPO/tests/gateway/test_busy_session_ack.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    memory-dead-letter-structural-trace-*.patch)
      if grep -q '"error_code": "capacity_overflow"' "$REPO/tools/memory_tool.py" \
        && grep -q "def stage_failure_write" "$REPO/tools/write_approval.py" \
        && grep -q "def emit_structural_write_receipt" "$REPO/tools/write_trace.py" \
        && grep -q 'result\["trace_receipt"\]' "$REPO/tools/skill_manager_tool.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    memory-dead-letter-state-fingerprint-*.patch)
      if grep -q "def _state_fingerprint" "$REPO/tools/memory_tool.py" \
        && grep -q '"state_fingerprint": context.get("state_fingerprint")' "$REPO/tools/write_approval.py" \
        && grep -q "def _valid_pending_id" "$REPO/tools/write_approval.py" \
        && grep -q "capacity overflow preserved" "$REPO/agent/background_review.py" \
        && grep -q "test_same_payload_against_different_state_gets_new_pending_id" "$REPO/tests/tools/test_memory_capacity_dead_letter.py" \
        && grep -q "test_surfaces_capacity_dead_letter_without_rejected_content_even_when_off" "$REPO/tests/run_agent/test_background_review_summary.py"; then
        log "patch invariants already present despite context drift: $name"
        return 0
      fi
      ;;
    honcho-provider-shutdown-drain-*.patch)
      if grep -q 'shutdown = getattr(manager, "shutdown", None)' "$REPO/plugins/memory/honcho/__init__.py" \
        && grep -q 'manager.stop_async_writer()' "$REPO/plugins/memory/honcho/__init__.py" \
        && grep -q "_context_prefetch_threads" "$REPO/plugins/memory/honcho/session.py" \
        && grep -q 'spawn_context_thread(_run, name="honcho-context-prefetch")' "$REPO/plugins/memory/honcho/session.py" \
        && grep -q "test_honcho_provider_shutdown_stops_manager_async_writer" "$REPO/tests/test_honcho_startup_fail_open.py" \
        && grep -q "test_honcho_manager_shutdown_joins_context_prefetch_thread" "$REPO/tests/test_honcho_startup_fail_open.py"; then
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

# Consolidated port for the current upstream main target 4323c67d
# (2026-08-17), preserving the complete reviewed MGS v0.20.0 surface.
# Apply the newest reviewed surface first; legacy composite/per-feature patches
# below remain invariant checks and backward-compatible fallback.
apply_patch_if_needed "mgs-runtime-customizations-2026-08-17-main-4323c67d.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-08-11-main-c0106e50.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-08-11-v0200.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-08-02-v0191.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-26.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-21.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-19.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-13.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-07.patch"
apply_patch_if_needed "memory-dead-letter-structural-trace-2026-07-13.patch"
apply_patch_if_needed "memory-dead-letter-state-fingerprint-2026-07-13.patch"
apply_patch_if_needed "honcho-provider-shutdown-drain-2026-07-17.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-07-05.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-30.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-26.patch"
apply_patch_if_needed "mgs-runtime-customizations-2026-06-20.patch"

apply_patch_if_needed "discord-deterministic-thread-rename-auto-add-users.patch"
apply_patch_if_needed "discord-thread-auto-add-by-channel-2026-07-13.patch"
apply_patch_if_needed "planned-restart-auto-resume-active-sessions.patch"
apply_patch_if_needed "restart-recovery-checkpoint-idempotent.patch"
apply_patch_if_needed "restart-recovery-natural-continuation-2026-07-11.patch"
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
apply_patch_if_needed "mgs-busy-steer-reentrant-followup-2026-07-12.patch"
apply_patch_if_needed "mgs-busy-steer-reentrant-rebuild-2026-07-12.patch"
apply_patch_if_needed "mgs-busy-steer-pending-turn-fifo-2026-07-30.patch"
apply_patch_if_needed "mgs-busy-steer-ack-ptbr-2026-07-11.patch"
apply_patch_if_needed "skill-view-compact-linked-files.patch"

# A retired Discord bot must never be restored by an older composite patch.
# Keep this exact cleanup after every patch application so controlled updates
# converge to the current three-agent runtime.
python3 - "$REPO/gateway/run.py" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
retired_id = "1513006098133680290"
lines = [line for line in text.splitlines(keepends=True) if retired_id not in line]
cleaned = "".join(lines)
if cleaned != text:
    path.write_text(cleaned)
PY
! grep -q "1513006098133680290" "$REPO/gateway/run.py" \
  || fail "retired Discord bot ID restored by patch bundle"

# Invariants that must survive every Hermes update. If any grep fails, the
# update is not production-safe for MGS gateways.
grep -q "def _auto_thread_name_from_message" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord deterministic thread naming helper"
grep -q "DISCORD_THREAD_AUTO_ADD_USERS" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord explicit thread auto-add support"
grep -q "Auto-thread member sync" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord auto-thread member sync log marker"
grep -q "def _discord_thread_auto_add_user_ids" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord per-channel thread auto-add resolver"
grep -q "DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord per-channel thread auto-add config bridge"
grep -q "test_auto_add_is_scoped_to_parent_channel" "$REPO/tests/gateway/test_discord_thread_auto_add_by_channel.py" \
  || fail "missing Discord per-channel thread auto-add regression test"
grep -q "semantic_fallback_title" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord semantic title fallback"
grep -q "Formatação de Tabelas" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord table-formatting title classifier"
grep -q "Erro Sistema Operacional" "$REPO/plugins/platforms/discord/adapter.py" \
  || fail "missing Discord OS-error title classifier"
grep -q "service-manager restarts while a chat task is active" "$REPO/gateway/run.py" \
  || fail "missing restart/service-manager auto-resume marker"
grep -q "Internal continuation event" "$REPO/gateway/run.py" \
  || fail "missing silent restart continuation event"
grep -q "finish every outstanding" "$REPO/gateway/run.py" \
  || fail "missing chronological restart continuation instruction"
! grep -q '_internal_auto_resume = bool(getattr(event, "internal", False))' "$REPO/gateway/run.py" \
  || fail "undefined outer event reference remains in restart-resume worker"
! grep -q "Internal restart recovery checkpoint" "$REPO/gateway/run.py" \
  || fail "legacy recovery checkpoint still active"
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
grep -Eq 'allow_same_generation_replacement=(ctx\.)?_interrupt_depth > 0' "$REPO/gateway/run.py" \
  || fail "missing MGS recursive rebuilt-agent ownership transfer"
grep -q "test_reentrant_followup_transfers_same_generation_rebuilt_agent" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing MGS rebuilt-agent follow-up regression test"
grep -q "def _merge_leftover_steer_into_pending_turn" "$REPO/gateway/run.py" \
  || fail "missing MGS queued-turn + leftover-steer merge helper"
grep -q "Merging leftover /steer into earlier queued turn" "$REPO/gateway/run.py" \
  || fail "missing MGS queued-turn + leftover-steer production integration"
grep -q "test_run_agent_merges_leftover_steer_into_earlier_queued_turn" "$REPO/tests/gateway/test_run_progress_topics.py" \
  || fail "missing MGS queued-turn + leftover-steer regression test"
grep -q "Skipping stale startup agent promotion" "$REPO/gateway/run.py" \
  || fail "missing upstream-compatible stale-generation promotion guard"
grep -q "test_startup_promotion_skips_stale_generation_without_overwrite" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing stale-generation ownership regression test"
grep -q "Mensagem adicionada à execução atual" "$REPO/gateway/run.py" \
  || fail "missing MGS PT-BR busy-steer acknowledgment"
grep -q "Vou considerá-la no próximo passo" "$REPO/tests/gateway/test_busy_session_ack.py" \
  || fail "missing MGS PT-BR busy-steer acknowledgment regression test"
grep -q "Image attached at:" "$REPO/gateway/run.py" \
  || fail "missing MGS mid-turn image path marker"
grep -q "def _linked_files_for_view" "$REPO/tools/skills_tool.py" \
  || fail "missing compact linked-files skill_view helper"
grep -q '"linked_files_summary"' "$REPO/tools/skills_tool.py" \
  || fail "missing compact linked-files summary result"
grep -q "test_view_compacts_large_linked_file_inventory" "$REPO/tests/tools/test_skills_tool.py" \
  || fail "missing compact linked-files regression tests"
grep -q '"error_code": "capacity_overflow"' "$REPO/tools/memory_tool.py" \
  || fail "missing machine-readable memory capacity_overflow result"
grep -q "def _stage_capacity_overflow" "$REPO/tools/memory_tool.py" \
  || fail "missing failure-only memory dead-letter dispatcher"
grep -q "def stage_failure_write" "$REPO/tools/write_approval.py" \
  || fail "missing atomic capacity-overflow staging helper"
grep -q "def emit_structural_write_receipt" "$REPO/tools/write_trace.py" \
  || fail "missing structural autowrite receipt emitter"
grep -q 'result\["trace_receipt"\]' "$REPO/tools/skill_manager_tool.py" \
  || fail "missing background skill structural receipt integration"
grep -q "def _state_fingerprint" "$REPO/tools/memory_tool.py" \
  || fail "missing locked canonical memory-state fingerprint"
grep -q '"state_fingerprint": context.get("state_fingerprint")' "$REPO/tools/write_approval.py" \
  || fail "missing state-scoped dead-letter idempotency key"
grep -q "test_same_payload_against_different_state_gets_new_pending_id" "$REPO/tests/tools/test_memory_capacity_dead_letter.py" \
  || fail "missing cross-state dead-letter idempotency regression test"
grep -q "def _valid_pending_id" "$REPO/tools/write_approval.py" \
  || fail "missing pending-ID path traversal guard"
grep -q "capacity overflow preserved" "$REPO/agent/background_review.py" \
  || fail "missing mandatory background capacity-loss disclosure"
grep -q "test_surfaces_capacity_dead_letter_without_rejected_content_even_when_off" "$REPO/tests/run_agent/test_background_review_summary.py" \
  || fail "missing background capacity disclosure regression test"
if grep -q "def _close_oneshot_agent" "$REPO/hermes_cli/oneshot.py"; then
  grep -q "_close_oneshot_agent(agent)" "$REPO/hermes_cli/oneshot.py" \
    || fail "one-shot helper exists but is not used by the agent path"
  grep -q "test_close_oneshot_agent_drains_memory_before_close" "$REPO/tests/hermes_cli/test_oneshot_usage_file.py" \
    || fail "missing legacy one-shot Honcho shutdown regression test"
else
  # Upstream bfa7a794c/97fc8a4a3 absorbed and strengthened the MGS lifecycle
  # fix: memory drains before agent.close(), and the session DB is closed even
  # when construction or conversation fails. Accept only that complete shape.
  grep -q 'agent.shutdown_memory_provider(session_messages)' "$REPO/hermes_cli/oneshot.py" \
    || fail "missing upstream one-shot memory drain"
  grep -q 'agent.close()' "$REPO/hermes_cli/oneshot.py" \
    || fail "missing upstream one-shot agent close"
  grep -q 'session_db.close()' "$REPO/hermes_cli/oneshot.py" \
    || fail "missing upstream one-shot session DB close"
  grep -q 'test_oneshot_run_agent_closes_agent_after_chat' "$REPO/tests/hermes_cli/test_tui_resume_flow.py" \
    || fail "missing upstream one-shot agent-close regression test"
  grep -q 'test_oneshot_run_agent_closes_session_db_when_agent_init_raises' "$REPO/tests/hermes_cli/test_tui_resume_flow.py" \
    || fail "missing upstream one-shot init-failure session DB regression test"
fi
grep -q '"group_sessions_per_user"' "$REPO/hermes_cli/config.py" \
  || fail "group_sessions_per_user missing from known config roots"
grep -q '"known_plugin_toolsets"' "$REPO/hermes_cli/config.py" \
  || fail "known_plugin_toolsets missing from known config roots"
grep -q "test_runtime_persisted_mgs_roots_are_known" "$REPO/tests/hermes_cli/test_config_validation.py" \
  || fail "missing regression test for runtime-persisted config roots"

"$BASE/scripts/check-retired-host-references.py" \
  || fail "retired host reference reappeared on an operational surface"

PYBIN="${PYBIN:-$REPO/venv/bin/python}"
[[ -x "$PYBIN" ]] || PYBIN="python3"
"$PYBIN" -m py_compile \
  "$REPO/plugins/platforms/discord/adapter.py" \
  "$REPO/gateway/run.py" \
  "$REPO/gateway/slash_commands.py" \
  "$REPO/gateway/reasoning_router.py" \
  "$REPO/gateway/platforms/base.py" \
  "$REPO/agent/background_review.py" \
  "$REPO/hermes_cli/config.py" \
  "$REPO/hermes_cli/oneshot.py" \
  "$REPO/tools/skills_tool.py" \
  "$REPO/tools/memory_tool.py" \
  "$REPO/tools/write_approval.py" \
  "$REPO/tools/skill_manager_tool.py" \
  "$REPO/tools/write_trace.py"

"$PYBIN" -m pytest -q \
  "$REPO/tests/gateway/test_restart_resume_pending.py" \
  "$REPO/tests/gateway/test_busy_session_ack.py" \
  "$REPO/tests/gateway/test_discord_send.py" \
  "$REPO/tests/gateway/test_discord_bot_filter.py" \
  "$REPO/tests/gateway/test_discord_free_response.py" \
  "$REPO/tests/gateway/test_discord_channel_controls.py" \
  "$REPO/tests/gateway/test_discord_edit_message_overflow.py" \
  "$REPO/tests/gateway/test_discord_slash_commands.py" \
  "$REPO/tests/gateway/test_extract_local_files.py" \
  "$REPO/tests/gateway/test_fast_command.py" \
  "$REPO/tests/gateway/test_session.py" \
  "$REPO/tests/gateway/test_mirror.py" \
  "$REPO/tests/gateway/test_agent_cache.py::TestExtractCacheBustingConfig::test_honcho_cache_busting_config_memoized_by_mtime" \
  "$REPO/tests/gateway/test_discord_thread_auto_add_by_channel.py" \
  "$REPO/tests/gateway/test_reasoning_command.py" \
  "$REPO/tests/gateway/test_auto_reasoning_routing.py" \
  "$REPO/tests/gateway/test_telegram_photo_interrupts.py" \
  "$REPO/tests/tools/test_skills_tool.py" \
  "$REPO/tests/tools/test_memory_tool.py" \
  "$REPO/tests/tools/test_memory_capacity_dead_letter.py" \
  "$REPO/tests/tools/test_write_approval.py" \
  "$REPO/tests/run_agent/test_background_review_summary.py" \
  "$REPO/tests/hermes_cli/test_oneshot_usage_file.py" \
  "$REPO/tests/hermes_cli/test_tui_resume_flow.py::test_oneshot_run_agent_closes_agent_after_chat" \
  "$REPO/tests/hermes_cli/test_tui_resume_flow.py::test_oneshot_run_agent_closes_agent_when_chat_raises" \
  "$REPO/tests/hermes_cli/test_tui_resume_flow.py::test_oneshot_run_agent_closes_session_db" \
  "$REPO/tests/hermes_cli/test_tui_resume_flow.py::test_oneshot_run_agent_closes_session_db_when_agent_init_raises" \
  "$REPO/tests/hermes_cli/test_config_validation.py" \
  "$REPO/tests/tools/test_write_trace.py"

log "OK Hermes MGS patches present, py_compile, one-shot lifecycle, dead-letter/trace and busy-steer tests passed"
