#!/usr/bin/env bash
set -euo pipefail

# MGS gateway restart guardrail.
# Contract: do NOT run this in foreground from an active Discord/Hermes turn to
# wait for restarts. Default mode only schedules a detached finalizer via
# systemd-run --no-block (or cron fallback) and exits with a clean summary.

AGENTS_DEFAULT="ares atena zeus"
ROOT="/root/mgs-agent"
LOG_DIR="$ROOT/logs"
AUDIT="$LOG_DIR/events-audit.jsonl"
HERMES_BIN="${HERMES_BIN:-/root/.local/bin/hermes}"
MODE="schedule"
AGENTS="$AGENTS_DEFAULT"
REASON="manual-safe-gateway-restart"
DELAY_SECONDS=5

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

ACTIVE_LAUNCHER="$(readlink -f "$HERMES_BIN")"
HERMES_REPO="${HERMES_REPO:-$(resolve_active_hermes_repo)}"
HERMES_PY="$HERMES_REPO/venv/bin/python"

usage() {
  cat <<'USAGE'
Usage: mgs-gateway-restart-safe.sh [--agents "atena ares zeus"] [--reason TEXT] [--delay SECONDS] [--execute]

Default schedules a detached restart finalizer and exits. It does not poll,
sleep for validation, stream systemctl output, or restart the caller in the
active conversation.

Rules encoded:
- Never restart from an active foreground tool-call thread.
- User-facing reply must happen before scheduling/execution.
- Zeus is always restarted last when included.
- Logs/audit stay in files; Discord gets only clean summaries.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agents) AGENTS="${2:-}"; shift 2 ;;
    --reason) REASON="${2:-}"; shift 2 ;;
    --delay) DELAY_SECONDS="${2:-5}"; shift 2 ;;
    --execute) MODE="execute"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$LOG_DIR" "$ROOT/data"

ts_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])'; }
audit() {
  local event="$1" detail="$2"
  local detail_escaped
  detail_escaped="$(printf '%s' "$detail" | json_escape)"
  printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-safe","reason":"%s","detail":"%s"}\n' \
    "$(ts_utc)" "$event" "$(printf '%s' "$REASON" | json_escape)" "$detail_escaped" >> "$AUDIT"
}

normalize_agents() {
  local requested=( $AGENTS )
  local out=() a
  # Preserve the caller's order for non-Zeus agents, but always force Zeus
  # last so the active orchestrator is the final gateway restarted.
  for a in "${requested[@]}"; do
    case "$a" in
      atena|ares) out+=("$a") ;;
    esac
  done
  for a in "${requested[@]}"; do
    [[ "$a" == "zeus" ]] && { out+=("zeus"); break; }
  done
  printf '%s\n' "${out[@]}" | awk 'NF && !seen[$0]++'
}

mapfile -t ORDERED_AGENTS < <(normalize_agents)
if [[ ${#ORDERED_AGENTS[@]} -eq 0 ]]; then
  echo "No valid agents selected. Valid: atena ares zeus" >&2
  exit 2
fi

FINALIZER="$ROOT/data/mgs-gateway-restart-finalizer-$(date -u +%Y%m%dT%H%M%SZ)-$$.sh"
FINAL_LOG="$LOG_DIR/mgs-gateway-restart-finalizer-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
SNAPSHOT="$ROOT/data/mgs-gateway-restart-snapshot-$(date -u +%Y%m%dT%H%M%SZ)-$$.sha256"
AGENT_LIST="${ORDERED_AGENTS[*]}"

SNAPSHOT_FILES=(
  "$ACTIVE_LAUNCHER"
  "$HERMES_REPO/gateway/run.py"
  "$HERMES_REPO/gateway/platforms/base.py"
  "$HERMES_REPO/plugins/platforms/discord/adapter.py"
  "$HERMES_REPO/plugins/memory/honcho/__init__.py"
  "$HERMES_REPO/plugins/memory/honcho/session.py"
  "$HERMES_REPO/gateway/slash_commands.py"
  "$HERMES_REPO/gateway/reasoning_router.py"
  "$HERMES_REPO/gateway/turn_context.py"
  "$HERMES_REPO/run_agent.py"
  "$HERMES_REPO/hermes_cli/config.py"
  "$HERMES_REPO/hermes_cli/oneshot.py"
  "$HERMES_REPO/agent/background_review.py"
  "$HERMES_REPO/tools/memory_tool.py"
  "$HERMES_REPO/tools/checkpoint_manager.py"
  "$HERMES_REPO/tools/write_approval.py"
  "$HERMES_REPO/tools/skill_manager_tool.py"
  "$HERMES_REPO/tools/skills_tool.py"
  "$HERMES_REPO/tools/write_trace.py"
  "/root/mgs-agent/scripts/check-gateway-ready.py"
)
for agent in "${ORDERED_AGENTS[@]}"; do
  SNAPSHOT_FILES+=("/root/.hermes/profiles/$agent/config.yaml")
done
if printf '%s\n' "${ORDERED_AGENTS[@]}" | grep -qx 'ares'; then
  SNAPSHOT_FILES+=(
    "/root/.hermes/profiles/ares/skills/growth/meta-ads-intraday-operations/SKILL.md"
    "/root/.hermes/profiles/ares/skills/growth/meta-ads-intraday-operations/references/current-pilot-contract.md"
    "/root/.hermes/profiles/ares/skills/growth/meta-ads-intraday-operations/references/current-reporting-contract.md"
    "/root/.hermes/profiles/ares/skills/growth/meta-ads-intraday-operations/references/reference-catalog.md"
    "/root/.hermes/profiles/ares/skills/growth/meta-ads-intraday-operations/references/current-operational-pitfalls.md"
    "/root/.hermes/profiles/ares/skills/creative/static-ascii-art-mgs/SKILL.md"
    "/root/.hermes/profiles/ares/skills/creative/static-ascii-art-mgs/references/original-ascii-art.md"
  )
fi
: > "$SNAPSHOT"
for file in "${SNAPSHOT_FILES[@]}"; do
  [[ -f "$file" ]] && sha256sum "$file" >> "$SNAPSHOT"
done

cat > "$FINALIZER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
LOG="$FINAL_LOG"
AUDIT="$AUDIT"
REASON="$(printf '%s' "$REASON" | sed "s/'/'\\''/g")"
SNAPSHOT="$SNAPSHOT"
HERMES_BIN="$HERMES_BIN"
EXPECTED_LAUNCHER="$ACTIVE_LAUNCHER"
HERMES_REPO="$HERMES_REPO"
HERMES_PY="$HERMES_PY"
RUNTIME="$HERMES_REPO/gateway/run.py"
exec >>"\$LOG" 2>&1
log(){ printf '[%s] %s\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" "\$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-finalizer","reason":"%s","detail":"%s"}\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" "\$1" "\$REASON" "\$2" >> "\$AUDIT"; }
log "START detached gateway restart finalizer agents=$AGENT_LIST reason=\$REASON"
audit "gateway_restart_finalizer_started" "agents=$AGENT_LIST log=\$LOG snapshot=\$SNAPSHOT"
if ! sha256sum -c "\$SNAPSHOT"; then
  log "ABORT target files changed after restart preparation"
  audit "gateway_restart_finalizer_aborted" "reason=target_drift snapshot=\$SNAPSHOT log=\$LOG"
  exit 75
fi
if [[ "\$(readlink -f "\$HERMES_BIN")" != "\$EXPECTED_LAUNCHER" ]]; then
  log "ABORT Hermes launcher target changed after restart preparation"
  audit "gateway_restart_finalizer_aborted" "reason=launcher_target_drift expected=\$EXPECTED_LAUNCHER actual=\$(readlink -f "\$HERMES_BIN") log=\$LOG"
  exit 74
fi
if ! "\$HERMES_PY" -m py_compile \
  "\$RUNTIME" \
  "\$HERMES_REPO/gateway/reasoning_router.py" \
  "\$HERMES_REPO/gateway/turn_context.py" \
  "\$HERMES_REPO/plugins/memory/honcho/__init__.py" \
  "\$HERMES_REPO/plugins/memory/honcho/session.py" \
  "\$HERMES_REPO/hermes_cli/config.py" \
  "\$HERMES_REPO/hermes_cli/oneshot.py" \
  "\$HERMES_REPO/agent/background_review.py" \
  "\$HERMES_REPO/tools/memory_tool.py" \
  "\$HERMES_REPO/tools/checkpoint_manager.py" \
  "\$HERMES_REPO/tools/write_approval.py" \
  "\$HERMES_REPO/tools/skill_manager_tool.py" \
  "\$HERMES_REPO/tools/skills_tool.py" \
  "\$HERMES_REPO/tools/write_trace.py" \
  /root/mgs-agent/scripts/check-gateway-ready.py; then
  log "ABORT runtime/dead-letter/trace py_compile failed"
  audit "gateway_restart_finalizer_aborted" "reason=runtime_pycompile_failed log=\$LOG"
  exit 76
fi
if ! "\$HERMES_PY" -c 'import gateway.reasoning_router, gateway.turn_context, plugins.memory.honcho.session, tools.checkpoint_manager, tools.skills_tool; from tools.memory_tool import _stage_capacity_overflow; from tools.write_approval import stage_failure_write; from tools.write_trace import emit_structural_write_receipt; assert hasattr(tools.checkpoint_manager, "_checkpoint_store_lock"); print("runtime_deadletter_trace_checkpoint_import=PASS")' >/dev/null; then
  log "ABORT dead-letter/trace import smoke failed"
  audit "gateway_restart_finalizer_aborted" "reason=deadletter_trace_import_failed log=\$LOG"
  exit 78
fi
if ! python3 -c 'import re,sys; s=open(sys.argv[1],encoding="utf-8").read(); defs=set(re.findall(r"^[ \\t]+def (_[A-Za-z0-9_]*startup_steer[A-Za-z0-9_]*)\\(",s,re.M))|set(re.findall(r"^[ \\t]+async def (_[A-Za-z0-9_]*startup_steer[A-Za-z0-9_]*)\\(",s,re.M)); calls=set(re.findall(r"self\\.(_[A-Za-z0-9_]*startup_steer[A-Za-z0-9_]*)\\(",s)); missing=sorted(calls-defs); print("startup_steer_missing="+",".join(missing)) if missing else None; raise SystemExit(bool(missing))' "\$RUNTIME"; then
  log "ABORT startup-steer method call has no class definition"
  audit "gateway_restart_finalizer_aborted" "reason=startup_steer_method_missing log=\$LOG"
  exit 77
fi
for agent in $AGENT_LIST; do
  svc="\${agent}-gateway.service"
  agent_log="/root/.hermes/profiles/\$agent/logs/agent.log"
  log_offset=0
  [[ -f "\$agent_log" ]] && log_offset="\$(stat -c%s "\$agent_log")"
  case "\$agent" in
    zeus) readiness_timeout=180 ;;
    atena|ares) readiness_timeout=90 ;;
    *) readiness_timeout=90 ;;
  esac
  log "restart \$svc timeout=\${readiness_timeout}s log_offset=\$log_offset"
  if ! systemctl restart "\$svc"; then
    log "FAILED systemctl restart \$svc"
    audit "gateway_restart_finalizer_failed" "agent=\$agent service=\$svc reason=restart_failed log=\$LOG"
    exit 79
  fi
  readiness_json=""
  if ! readiness_json="\$(/root/mgs-agent/scripts/check-gateway-ready.py --service "\$svc" --log "\$agent_log" --offset "\$log_offset" --timeout "\$readiness_timeout" --poll 2)"; then
    safe_reason="\$(printf '%s' "\$readiness_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("reason=%s active=%s sub=%s pid=%s connected=%s elapsed=%s" % (d.get("reason","unknown"),d.get("ActiveState","unknown"),d.get("SubState","unknown"),d.get("MainPID",0),d.get("discord_connected",False),d.get("elapsed_seconds",0)))' 2>/dev/null || printf 'reason=readiness_probe_failed')"
    log "FAILED \$agent readiness \$safe_reason"
    audit "gateway_restart_finalizer_failed" "agent=\$agent service=\$svc \$safe_reason log=\$LOG"
    exit 80
  fi
  safe_ready="\$(printf '%s' "\$readiness_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("agent=%s service=%s pid=%s nrestarts=%s connected=%s elapsed=%s" % (sys.argv[1],d.get("service",""),d.get("MainPID",0),d.get("NRestarts",0),d.get("discord_connected",False),d.get("elapsed_seconds",0)))' "\$agent")"
  log "READY \$safe_ready"
  audit "gateway_restart_agent_ready" "\$safe_ready log=\$LOG"
done
log "All requested gateways passed sequential systemd+Discord readiness."
systemctl show $(printf '%s-gateway.service ' "${ORDERED_AGENTS[@]}") -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
for agent in $AGENT_LIST; do
  log "recent markers \$agent"
  grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' "/root/.hermes/profiles/\$agent/logs/agent.log" 2>/dev/null | tail -8 || true
done
audit "gateway_restart_finalizer_finished" "agents=$AGENT_LIST log=\$LOG"
log "DONE detached gateway restart finalizer"
EOF
chmod 0750 "$FINALIZER"
audit "gateway_restart_finalizer_prepared" "agents=$AGENT_LIST finalizer=$FINALIZER log=$FINAL_LOG snapshot=$SNAPSHOT mode=$MODE"

if [[ "$MODE" != "execute" ]]; then
  echo "Prepared detached finalizer only (no restart executed): $FINALIZER"
  echo "Audit: $AUDIT"
  exit 0
fi

if command -v systemd-run >/dev/null 2>&1; then
  unit="mgs-gateway-restart-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  systemd-run --unit="$unit" --on-active="${DELAY_SECONDS}s" --collect --no-block "$FINALIZER" >/dev/null
  audit "gateway_restart_scheduled" "method=systemd-run unit=$unit delay=${DELAY_SECONDS}s agents=$AGENT_LIST finalizer=$FINALIZER log=$FINAL_LOG"
  echo "Restart scheduled detached via systemd-run unit=$unit log=$FINAL_LOG"
else
  at_file="/etc/cron.d/mgs-gateway-restart-$$"
  minute="$(date -u -d "+1 minute" +%M)"
  hour="$(date -u -d "+1 minute" +%H)"
  printf '%s %s * * * root %s && rm -f %s\n' "$minute" "$hour" "$FINALIZER" "$at_file" > "$at_file"
  audit "gateway_restart_scheduled" "method=cron file=$at_file agents=$AGENT_LIST finalizer=$FINALIZER log=$FINAL_LOG"
  echo "Restart scheduled detached via cron log=$FINAL_LOG"
fi
