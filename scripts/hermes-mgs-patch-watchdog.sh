#!/usr/bin/env bash
# hermes-mgs-patch-watchdog.sh — script-only watchdog for MGS Hermes local patches.
# Cron/Hermes delivery must stay local/silent; Discord alerts are sent as clean embeds to #alerts-infra.
set -euo pipefail

BASE=/root/mgs-agent
LOG="$BASE/logs/hermes-mgs-patch-watchdog.log"
STATE_FILE="$BASE/data/hermes-mgs-patch-watchdog-state.json"
WEBHOOK_ITEM="Discord Webhook - Alerts Infra Channel"
VAULT="${OP_DEFAULT_VAULT:-MGS Conteúdo}"
MENTION="<@344196393512075265>"
mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE_FILE")"

now_iso() { date -Iseconds; }
log_local() { printf '[%s] watchdog-wrapper: %s\n' "$(now_iso)" "$*" >> "$LOG"; }

ensure_state() {
  if [[ ! -s "$STATE_FILE" ]]; then
    printf '{"status":"ok","last_alert_sent":null,"last_failure_rc":null,"last_check":null}\n' > "$STATE_FILE"
  fi
}

state_get() {
  local key="$1" fallback="$2"
  jq -r --arg k "$key" --arg f "$fallback" '.[$k] // $f' "$STATE_FILE" 2>/dev/null || printf '%s\n' "$fallback"
}

state_write() {
  local status="$1" rc="$2" alert_ts="$3"
  jq -n \
    --arg status "$status" \
    --arg rc "$rc" \
    --arg alert_ts "$alert_ts" \
    --arg ts "$(now_iso)" \
    '{status:$status,last_failure_rc:($rc | tonumber? // null),last_alert_sent:(if $alert_ts == "null" then null else $alert_ts end),last_check:$ts}' \
    > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
}

get_webhook_url() {
  set -a
  # shellcheck disable=SC1091
  source "$BASE/.env" 2>/dev/null || true
  set +a
  op item get "$WEBHOOK_ITEM" --vault "$VAULT" --fields label=webhook_url --reveal 2>/dev/null || true
}

send_discord_payload() {
  local payload="$1"
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    log_local "DRY_RUN: would send alerts-infra payload"
    printf '%s\n' "$payload"
    return 0
  fi
  local webhook_url
  webhook_url="$(get_webhook_url)"
  if [[ -z "$webhook_url" ]]; then
    log_local "WARN: webhook URL unavailable; alert not sent"
    return 0
  fi
  curl -sS -X POST "$webhook_url" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    --max-time 10 >/dev/null || log_local "WARN: Discord webhook post failed"
}

send_failure_alert() {
  local rc="$1" detail="$2"
  local payload
  payload="$(jq -n \
    --arg content "$MENTION alerta de infra: Hermes patch watchdog falhou" \
    --arg rc "$rc" \
    --arg log "$LOG" \
    --arg detail "$detail" \
    '{content:$content, embeds:[{title:"Hermes patch watchdog falhou", color:15158332, fields:[
      {name:"Status", value:"Falha na validação dos patches MGS do Hermes", inline:false},
      {name:"Exit code", value:("`"+$rc+"`"), inline:true},
      {name:"Log completo", value:("`"+$log+"`"), inline:false},
      {name:"Resumo técnico", value:("```text\n"+($detail[:900])+"\n```"), inline:false},
      {name:"Ação", value:"Zeus deve revisar drift/invariantes do patch antes do próximo update/restart.", inline:false}
    ]}] }')"
  send_discord_payload "$payload"
}

send_resolved_alert() {
  local payload
  payload="$(jq -n \
    --arg log "$LOG" \
    '{content:"", embeds:[{title:"Hermes patch watchdog recuperado", color:3066993, fields:[
      {name:"Status", value:"Validação dos patches MGS voltou a passar", inline:false},
      {name:"Log completo", value:("`"+$log+"`"), inline:false}
    ]}] }')"
  send_discord_payload "$payload"
}

ensure_state
previous_status="$(state_get status ok)"
last_alert="$(state_get last_alert_sent null)"

set +e
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh >> "$LOG" 2>&1
rc=$?
set -e

if (( rc == 0 )); then
  log_local "OK: ensure-hermes-mgs-patches passed"
  if [[ "$previous_status" == "failed" ]]; then
    send_resolved_alert
  fi
  state_write ok 0 null
  exit 0
fi

log_local "FAIL: ensure-hermes-mgs-patches rc=$rc"
detail="$(tail -20 "$LOG" 2>/dev/null || true)"

# Anti-spam: one alert per failure episode. Resolution alert resets the state.
if [[ "$previous_status" != "failed" || "$last_alert" == "null" ]]; then
  alert_ts="$(now_iso)"
  state_write failed "$rc" "$alert_ts"
  send_failure_alert "$rc" "$detail"
else
  state_write failed "$rc" "$last_alert"
  log_local "alert suppressed: failure already active since $last_alert"
fi

# Keep non-zero exit for local scheduler observability, but stdout stays empty.
exit "$rc"
