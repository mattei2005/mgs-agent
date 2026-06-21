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
DRY_RUN="${DRY_RUN:-0}"
AGENTS=(zeus atena ares hera)

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
    "description": "Estado do monitor Honcho MGS. Monitora mgs-memory-copilot para Zeus/Atena/Ares/Hera.",
    "threshold": "alert on first non-ok status",
    "anti_spam_hours": 6
  },
  "last_check": null,
  "last_status": "unknown",
  "last_alert_sent": null,
  "last_failure_details": [],
  "last_ok_at": null
}
JSON
fi

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOW_EPOCH="$(date +%s)"
TMP_RESULTS="$(mktemp)"
trap 'rm -f "$TMP_RESULTS" "$TMP_RESULTS.payload" "$TMP_RESULTS.bot"' EXIT

log "START agents=${AGENTS[*]} dry_run=${DRY_RUN}"

# Run health checks. The wrapper itself pulls the Honcho key from 1Password and never prints it.
for agent in "${AGENTS[@]}"; do
  set +e
  output="$(MGS_MEMORY_COPILOT_TIMEOUT_SECONDS=45 "${BASE_DIR}/scripts/mgs-memory-copilot" \
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

get_bot_token() {
  op item get 'Discord Bot - Zeus' \
    --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
    --fields label=discord_bot_token \
    --reveal 2>/dev/null
}

send_discord_payload() {
  local payload_file="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN discord payload=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("embeds", [{}])[0].get("title", "payload"))' "$payload_file")"
    return 0
  fi
  local token
  token="$(get_bot_token)"
  if [[ -z "$token" ]]; then
    log "ERROR: Zeus bot token unavailable; cannot send Discord alert"
    return 1
  fi
  printf '%s' "$token" > "$TMP_RESULTS.bot"
  python3 - <<'PY' "$TMP_RESULTS.bot" "$CHANNEL_ID" "$payload_file"
import sys, json, urllib.request
bot=open(sys.argv[1]).read().strip(); channel=sys.argv[2]; payload=json.load(open(sys.argv[3]))
url=f"https://discord.com/api/v10/channels/{channel}/messages"
req=urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json","Authorization":f"Bot {bot}","User-Agent":"MGS-Zeus/1.0"}, method="POST")
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.status)
PY
}

if (( FAIL_COUNT > 0 )); then
  log "FAIL status_count=${FAIL_COUNT} prev=${PREV_STATUS}"
  SEND_ALERT=0
  if [[ "$LAST_ALERT" == "null" || -z "$LAST_ALERT" ]]; then
    SEND_ALERT=1
  else
    LAST_ALERT_EPOCH="$(date -d "$LAST_ALERT" +%s 2>/dev/null || echo 0)"
    if (( NOW_EPOCH - LAST_ALERT_EPOCH > WINDOW_ANTI_SPAM_HOURS * 3600 )); then
      SEND_ALERT=1
    fi
  fi

  if [[ "$SEND_ALERT" == "1" ]]; then
    python3 - <<'PY' "$FAILURES_JSON" > "$TMP_RESULTS.payload"
import json, sys
fail=json.loads(sys.argv[1])
lines=[]
for r in fail:
    lines.append(f"{r.get('agent')}: {r.get('status')} / {r.get('action_required')} / {r.get('session')}")
detail="\n".join(lines)[:900]
payload={
  "content":"<@344196393512075265> alerta: Honcho MGS indisponível",
  "allowed_mentions":{"users":["344196393512075265"]},
  "embeds":[{
    "title":"Honcho MGS indisponível",
    "color":15158332,
    "fields":[
      {"name":"Falhas", "value":str(len(fail)), "inline":True},
      {"name":"Ação", "value":"Verificar app.honcho.dev; se status=cold_storage, resumir tenant manualmente e reexecutar health check.", "inline":False},
      {"name":"Detalhe técnico", "value":"```\n"+detail+"\n```", "inline":False}
    ]
  }]
}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
    send_discord_payload "$TMP_RESULTS.payload" >/dev/null || log "WARN: Discord alert failed"
    ALERT_TS="$NOW_ISO"
  else
    log "anti-spam suppress alert last_alert=${LAST_ALERT}"
    ALERT_TS="$LAST_ALERT"
  fi

  python3 - <<'PY' "$STATE_FILE" "$NOW_ISO" "$ALERT_TS" "$FAILURES_JSON"
import json, sys, pathlib
p=pathlib.Path(sys.argv[1]); now=sys.argv[2]; alert=sys.argv[3]; failures=json.loads(sys.argv[4])
d=json.loads(p.read_text())
d.update({"last_check":now,"last_status":"fail","last_alert_sent":alert,"last_failure_details":failures})
p.write_text(json.dumps(d, indent=2, ensure_ascii=False)+"\n")
PY
else
  log "OK agents=${#AGENTS[@]} prev=${PREV_STATUS}"
  if [[ "$PREV_STATUS" == "fail" ]]; then
    python3 - <<'PY' > "$TMP_RESULTS.payload"
import json
payload={"content":"","embeds":[{"title":"Honcho MGS restabelecido","color":3066993,"fields":[{"name":"Status","value":"Zeus/Atena/Ares/Hera health checks OK","inline":False}]}]}
json.dump(payload, sys.stdout, ensure_ascii=False)
PY
    send_discord_payload "$TMP_RESULTS.payload" >/dev/null || log "WARN: Discord resolution failed"
  fi
  python3 - <<'PY' "$STATE_FILE" "$NOW_ISO"
import json, sys, pathlib
p=pathlib.Path(sys.argv[1]); now=sys.argv[2]
d=json.loads(p.read_text())
d.update({"last_check":now,"last_status":"ok","last_failure_details":[],"last_ok_at":now})
p.write_text(json.dumps(d, indent=2, ensure_ascii=False)+"\n")
PY
fi

log "DONE status=$(python3 - <<'PY' "$STATE_FILE"
import json,sys
print(json.load(open(sys.argv[1])).get('last_status'))
PY
) failures=${FAIL_COUNT}"
