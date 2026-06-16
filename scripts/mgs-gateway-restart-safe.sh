#!/usr/bin/env bash
set -euo pipefail

# MGS gateway restart guardrail.
# Contract: do NOT run this in foreground from an active Discord/Hermes turn to
# wait for restarts. Default mode only schedules a detached finalizer via
# systemd-run --no-block (or cron fallback) and exits with a clean summary.

AGENTS_DEFAULT="atena ares hera zeus"
ROOT="/root/mgs-agent"
LOG_DIR="$ROOT/logs"
AUDIT="$LOG_DIR/events-audit.jsonl"
MODE="schedule"
AGENTS="$AGENTS_DEFAULT"
REASON="manual-safe-gateway-restart"
DELAY_SECONDS=5

usage() {
  cat <<'USAGE'
Usage: mgs-gateway-restart-safe.sh [--agents "atena ares hera zeus"] [--reason TEXT] [--delay SECONDS] [--execute]

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
  for wanted in atena ares hera zeus; do
    for a in "${requested[@]}"; do
      [[ "$a" == "$wanted" ]] && out+=("$wanted")
    done
  done
  printf '%s\n' "${out[@]}" | awk 'NF && !seen[$0]++'
}

mapfile -t ORDERED_AGENTS < <(normalize_agents)
if [[ ${#ORDERED_AGENTS[@]} -eq 0 ]]; then
  echo "No valid agents selected. Valid: atena ares hera zeus" >&2
  exit 2
fi

FINALIZER="$ROOT/data/mgs-gateway-restart-finalizer-$(date -u +%Y%m%dT%H%M%SZ)-$$.sh"
FINAL_LOG="$LOG_DIR/mgs-gateway-restart-finalizer-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
AGENT_LIST="${ORDERED_AGENTS[*]}"

cat > "$FINALIZER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
LOG="$FINAL_LOG"
AUDIT="$AUDIT"
REASON="$(printf '%s' "$REASON" | sed "s/'/'\\''/g")"
exec >>"\$LOG" 2>&1
log(){ printf '[%s] %s\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" "\$*"; }
audit(){ printf '{"ts":"%s","event":"%s","actor":"mgs-gateway-restart-finalizer","reason":"%s","detail":"%s"}\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" "\$1" "\$REASON" "\$2" >> "\$AUDIT"; }
log "START detached gateway restart finalizer agents=$AGENT_LIST reason=\$REASON"
audit "gateway_restart_finalizer_started" "agents=$AGENT_LIST log=\$LOG"
for agent in $AGENT_LIST; do
  svc="\${agent}-gateway.service"
  log "restart \$svc"
  systemctl restart --no-block "\$svc"
done
log "Validation is intentionally file-only; no foreground Discord/tool polling."
systemctl show $(printf '%s-gateway.service ' "${ORDERED_AGENTS[@]}") -p Id -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStatus -p ExecMainStartTimestamp --no-pager || true
for agent in $AGENT_LIST; do
  log "recent markers \$agent"
  grep -E 'Connected as|Gateway running|discord connected|Logged in as|Ready' "/root/.hermes/profiles/\$agent/logs/agent.log" 2>/dev/null | tail -8 || true
done
audit "gateway_restart_finalizer_finished" "agents=$AGENT_LIST log=\$LOG"
log "DONE detached gateway restart finalizer"
EOF
chmod 0750 "$FINALIZER"
audit "gateway_restart_finalizer_prepared" "agents=$AGENT_LIST finalizer=$FINALIZER log=$FINAL_LOG mode=$MODE"

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
