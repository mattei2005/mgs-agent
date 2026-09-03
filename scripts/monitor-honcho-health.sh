#!/usr/bin/env bash
# monitor-honcho-health.sh — Monitor Honcho managed tenant/copilot health for MGS agents.
# Alerts #alerts-infra when Honcho becomes unavailable/cold_storage and resolves when healthy again.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
STATE_FILE="${BASE_DIR}/data/honcho-health-state.json"
LOG_PREFIX="monitor-honcho-health"
CHANNEL_ID="1498132022634483894" # alerts-infra
WINDOW_ANTI_SPAM_HOURS="${WINDOW_ANTI_SPAM_HOURS:-6}"
HONCHO_ALERT_THRESHOLD="${HONCHO_ALERT_THRESHOLD:-2}"
# Debounced Discord alerts: first critical failure only updates state/log;
# a push is sent only if the next 15-min cron still sees Honcho critically unavailable.
HONCHO_DISCORD_ALERTS="${HONCHO_DISCORD_ALERTS:-1}"
HONCHO_BILLING_RECHECK="${HONCHO_BILLING_RECHECK:-0}"
DRY_RUN="${DRY_RUN:-0}"
AGENTS=(zeus atena ares)

log() { echo "[$(date -Iseconds)] ${LOG_PREFIX}: $*"; }

if [[ -f "${BASE_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${BASE_DIR}/.env" >/dev/null 2>&1 || true
  set +a
fi

mkdir -p "$(dirname "$STATE_FILE")" "${BASE_DIR}/logs"
if [[ ! -f "$STATE_FILE" ]]; then
  cat > "$STATE_FILE" <<'JSON'
{
  "_meta": {
    "description": "Estado do monitor Honcho MGS. Monitora provider nativo + copilot para Zeus/Atena/Ares.",
    "threshold": "alert after 2 consecutive non-ok checks by default",
    "anti_spam_hours": 6
  },
  "last_check": null,
  "last_status": "unknown",
  "last_alert_sent": null,
  "last_failure_details": [],
  "consecutive_failures": 0,
  "alert_active": false,
  "last_ok_at": null
}
JSON
fi

# A billing/top-up block cannot be repaired by retries. Once every recorded
# failure is explicitly billing-blocked and the alert is active, cron stays
# fail-closed without reading 1Password or calling Honcho. After a manual
# top-up, an operator must run once with HONCHO_BILLING_RECHECK=1; a healthy
# result clears the state and restores normal scheduled checks.
BILLING_BLOCK_ACTIVE="$(python3 - <<'PY' "$STATE_FILE"
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    failures = d.get("last_failure_details") or []
    blocked = (
        d.get("alert_active") is True
        and bool(failures)
        and all(r.get("action_required") == "manual_billing_honcho" for r in failures)
    )
    print("true" if blocked else "false")
except Exception:
    print("false")
PY
)"
if [[ "$BILLING_BLOCK_ACTIVE" == "true" && "$HONCHO_BILLING_RECHECK" != "1" ]]; then
  log "BILLING_BLOCKED: external checks suppressed; manual top-up required; recheck with HONCHO_BILLING_RECHECK=1"
  exit 0
fi

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_EPOCH="$(date +%s)"
TMP_RESULTS="$(mktemp)"
trap 'rm -f "$TMP_RESULTS" "$TMP_RESULTS.payload"' EXIT

log "START agents=${AGENTS[*]} dry_run=${DRY_RUN} threshold=${HONCHO_ALERT_THRESHOLD}"

# Uma única leitura da chave compartilhada por ciclo; os três copilots reutilizam
# HONCHO_API_KEY e não voltam ao 1Password.
HONCHO_API_KEY="$(op item get 'Honcho API - MGS' \
  --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
  --fields 'api key' \
  --reveal 2>/dev/null || true)"
if [[ -z "$HONCHO_API_KEY" ]]; then
  log "ERROR: Honcho API key unavailable; aborting cycle without multiplicative retries"
  exit 1
fi
export HONCHO_API_KEY

# Run health checks with the single shared key loaded above.
for agent in "${AGENTS[@]}"; do
  set +e
  native_status="$(/root/.local/bin/hermes -p "$agent" memory status 2>&1)"
  native_rc=$?
  set -e
  if [[ $native_rc -ne 0 ]] \
    || ! grep -q 'Provider:  honcho' <<<"$native_status" \
    || ! grep -q 'Status:    available' <<<"$native_status"; then
    python3 - <<PY >> "$TMP_RESULTS"
import json
print(json.dumps({"agent":"$agent","status":"native_provider_unavailable","action_required":"repair_native_provider","session":"n/a","detail":"memory.provider honcho not available"}, ensure_ascii=False))
PY
    continue
  fi

  set +e
  output="$(MGS_MEMORY_COPILOT_TIMEOUT_SECONDS="${HONCHO_COPILOT_TIMEOUT_SECONDS:-90}" "${BASE_DIR}/scripts/mgs-memory-copilot" \
    --agent "$agent" \
    --json \
    --question "monitor health check: validate Honcho copilot reachability" \
    --context "sanitized automated health check, no secrets" 2>&1)"
  rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    python3 - <<PY >> "$TMP_RESULTS"
import json
print(json.dumps({"agent":"$agent","status":"command_failed","action_required":"investigate_wrapper","session":"n/a","detail":"wrapper exit rc=$rc"}, ensure_ascii=False))
PY
    continue
  fi

  # Normalize output to one compact JSON line. If parsing fails, alert.
  RAW_FILE="$(mktemp)"
  printf '%s' "$output" > "$RAW_FILE"
  python3 - "$agent" "$RAW_FILE" >> "$TMP_RESULTS" <<'PY'
import json, sys
agent=sys.argv[1]
raw=open(sys.argv[2], errors="replace").read()
try:
    data=json.loads(raw)
    print(json.dumps({
        "agent": data.get("agent", agent),
        "status": data.get("status", "unknown"),
        "action_required": data.get("action_required", "none"),
        "session": data.get("session", "n/a"),
        "detail": (data.get("hypothesis") or "")[:280],
    }, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"agent":agent,"status":"invalid_json","action_required":"investigate_wrapper","session":"n/a","detail":f"{type(exc).__name__}: {str(exc)[:180]}"}, ensure_ascii=False))
PY
  rm -f "$RAW_FILE"
done

FAILURES_JSON="$(python3 - <<'PY' "$TMP_RESULTS"
import json, sys
rows=[]
for line in open(sys.argv[1]):
    line=line.strip()
    if line:
        rows.append(json.loads(line))
fail=[r for r in rows if r.get('status') != 'ok']
print(json.dumps(fail, ensure_ascii=False))
PY
)"
FAIL_COUNT="$(python3 - <<'PY' "$FAILURES_JSON"
import json, sys
print(len(json.loads(sys.argv[1])))
PY
)"
ACTUAL_FAIL_COUNT="$FAIL_COUNT"
FAIL_COUNT="$(python3 - <<'PY' "$FAILURES_JSON" "${#AGENTS[@]}"
import json, sys
fail=json.loads(sys.argv[1]); total=int(sys.argv[2])
critical = bool(fail) and (
    len(fail) >= total
    or any(r.get('status') == 'cold_storage' for r in fail)
    or any(r.get('action_required') == 'manual_resume_app_honcho_dev' for r in fail)
    or any(r.get('action_required') == 'manual_billing_honcho' for r in fail)
)
print(len(fail) if critical else 0)
PY
)"
if (( ACTUAL_FAIL_COUNT > 0 && FAIL_COUNT == 0 )); then
  log "PARTIAL_FAIL suppressed actual_failures=${ACTUAL_FAIL_COUNT}/${#AGENTS[@]} reason=not_full_outage_not_cold_storage"
fi
PREV_STATUS="$(python3 - <<'PY' "$STATE_FILE"
import json, sys
try: print(json.load(open(sys.argv[1])).get('last_status','unknown'))
except Exception: print('unknown')
PY
)"
LAST_ALERT="$(python3 - <<'PY' "$STATE_FILE"
import json, sys
try: print(json.load(open(sys.argv[1])).get('last_alert_sent') or 'null')
except Exception: print('null')
PY
)"
CONSECUTIVE_FAILURES="$(python3 - <<'PY' "$STATE_FILE"
import json, sys
try: print(int(json.load(open(sys.argv[1])).get('consecutive_failures') or 0))
except Exception: print(0)
PY
)"
ALERT_ACTIVE="$(python3 - <<'PY' "$STATE_FILE"
import json, sys
try: print('true' if json.load(open(sys.argv[1])).get('alert_active') else 'false')
except Exception: print('false')
PY
)"

send_discord_payload() {
  local payload_file="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    "${BASE_DIR}/scripts/discord-bot-post.py" --channel-id "$CHANNEL_ID" --dry-run < "$payload_file"
    return $?
  fi
  "${BASE_DIR}/scripts/discord-bot-post.py" --channel-id "$CHANNEL_ID" < "$payload_file"
}

if (( FAIL_COUNT > 0 )); then
  NEW_CONSECUTIVE_FAILURES=$(( CONSECUTIVE_FAILURES + 1 ))
  log "FAIL status_count=${FAIL_COUNT} prev=${PREV_STATUS} consecutive=${NEW_CONSECUTIVE_FAILURES}/${HONCHO_ALERT_THRESHOLD} alert_active=${ALERT_ACTIVE}"
  SEND_ALERT=0
  NEW_ALERT_ACTIVE="$ALERT_ACTIVE"
  if (( NEW_CONSECUTIVE_FAILURES >= HONCHO_ALERT_THRESHOLD )); then
    if [[ "$HONCHO_DISCORD_ALERTS" != "1" ]]; then
      NEW_ALERT_ACTIVE="false"
      SEND_ALERT=0
      log "discord alert disabled for Honcho monitor; keeping log/state only"
    else
      NEW_ALERT_ACTIVE="true"
      if [[ "$ALERT_ACTIVE" != "true" || "$LAST_ALERT" == "null" || -z "$LAST_ALERT" ]]; then
        SEND_ALERT=1
      else
        LAST_ALERT_EPOCH="$(date -d "$LAST_ALERT" +%s 2>/dev/null || echo 0)"
        if (( NOW_EPOCH - LAST_ALERT_EPOCH > WINDOW_ANTI_SPAM_HOURS * 3600 )); then
          SEND_ALERT=1
        fi
      fi
    fi
  else
    log "debounce: suppressing transient Honcho failure until threshold=${HONCHO_ALERT_THRESHOLD} consecutive checks"
  fi

  if [[ "$SEND_ALERT" == "1" ]]; then
    python3 - <<'PY' "$FAILURES_JSON" > "$TMP_RESULTS.payload"
import json, sys
fail=json.loads(sys.argv[1])
lines=[]
for r in fail:
    lines.append(f"{r.get('agent')}: {r.get('status')} / {r.get('action_required')} / {r.get('session')}")
detail="\n".join(lines)[:900]
if any(r.get('action_required') == 'manual_billing_honcho' for r in fail):
    action="Créditos insuficientes. Validar top-up/billing manualmente em app.honcho.dev/billing; não repetir até regularizar."
elif any(r.get('action_required') == 'manual_resume_app_honcho_dev' for r in fail):
    action="Tenant em cold storage. Retomar manualmente em app.honcho.dev e reexecutar o health check."
else:
    action="Investigar conectividade/API do Honcho e reexecutar o health check; fontes canônicas MGS permanecem disponíveis."
payload={
  "content":"<@344196393512075265> alerta: Honcho MGS indisponível",
  "allowed_mentions":{"users":["344196393512075265"]},
  "embeds":[{
    "title":"Honcho MGS indisponível",
    "color":15158332,
    "fields":[
      {"name":"Falhas", "value":str(len(fail)), "inline":True},
      {"name":"Ação", "value":action, "inline":False},
      {"name":"Detalhe técnico", "value":"```\n"+detail+"\n```", "inline":False}
    ]
  }]
}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
    send_discord_payload "$TMP_RESULTS.payload" >/dev/null || log "WARN: Discord alert failed"
    ALERT_TS="$NOW_ISO"
  else
    if (( NEW_CONSECUTIVE_FAILURES >= HONCHO_ALERT_THRESHOLD )); then
      log "anti-spam suppress alert last_alert=${LAST_ALERT}"
    fi
    ALERT_TS="$LAST_ALERT"
  fi

  if [[ "$DRY_RUN" != "1" ]]; then
    python3 - <<'PY' "$STATE_FILE" "$NOW_ISO" "$ALERT_TS" "$FAILURES_JSON" "$NEW_CONSECUTIVE_FAILURES" "$NEW_ALERT_ACTIVE"
import json, sys, pathlib
p=pathlib.Path(sys.argv[1]); now=sys.argv[2]; alert=sys.argv[3]; failures=json.loads(sys.argv[4]); consecutive=int(sys.argv[5]); active=(sys.argv[6]=='true')
d=json.loads(p.read_text())
d.update({"last_check":now,"last_status":"fail","last_alert_sent":None if alert in ('null','') else alert,"last_failure_details":failures,"consecutive_failures":consecutive,"alert_active":active})
p.write_text(json.dumps(d, indent=2, ensure_ascii=False)+"\n")
PY
  else
    log "dry-run: state unchanged"
  fi
else
  log "OK agents=${#AGENTS[@]} prev=${PREV_STATUS} consecutive=${CONSECUTIVE_FAILURES} alert_active=${ALERT_ACTIVE}"
  if [[ "$PREV_STATUS" == "fail" && "$ALERT_ACTIVE" == "true" ]]; then
    python3 - <<'PY' > "$TMP_RESULTS.payload"
import json, sys
payload={"content":"","embeds":[{"title":"Honcho MGS restabelecido","color":3066993,"fields":[{"name":"Status","value":"Zeus/Atena/Ares provider nativo + copilot OK","inline":False}]}]}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
    send_discord_payload "$TMP_RESULTS.payload" >/dev/null || log "WARN: Discord resolution failed"
  fi
  if [[ "$DRY_RUN" != "1" ]]; then
    python3 - <<'PY' "$STATE_FILE" "$NOW_ISO"
import json, sys, pathlib
p=pathlib.Path(sys.argv[1]); now=sys.argv[2]
d=json.loads(p.read_text())
d.update({"last_check":now,"last_status":"ok","last_alert_sent":None,"last_failure_details":[],"consecutive_failures":0,"alert_active":False,"last_ok_at":now})
p.write_text(json.dumps(d, indent=2, ensure_ascii=False)+"\n")
PY
  else
    log "dry-run: state unchanged"
  fi
fi

log "DONE status=$(python3 - <<'PY' "$STATE_FILE"
import json,sys
print(json.load(open(sys.argv[1])).get('last_status'))
PY
) failures=${FAIL_COUNT}"
