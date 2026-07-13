#!/usr/bin/env bash
# send-report-infra-embed.sh — envia REPORT-INFRA em embed limpo para Discord
# Uso:
#   send-report-infra-embed.sh --action modificada --type script/data --path /x --reason "..." --evidence "..."
set -euo pipefail

BASE_DIR=/root/mgs-agent
ACTION=""
TYPE=""
PATHS=""
REASON=""
EVIDENCE=""
COLOR="3447003"
TITLE="REPORT-INFRA"
DRY_RUN=0
# REPORT-INFRA embeds no #alerts-infra devem ser silenciosos por padrão.
# Rodolfo pediu explicitamente para não mencionar Zeus, ele, nem ninguém nesses alertas.

usage() {
  cat <<'EOF'
Usage: send-report-infra-embed.sh --action <criada|modificada|removida> --type <tipo> --path <path(s)> --reason <motivo> --evidence <evidência> [--color <decimal>] [--dry-run]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --action) ACTION="${2:-}"; shift 2 ;;
    --type) TYPE="${2:-}"; shift 2 ;;
    --path|--paths) PATHS="${2:-}"; shift 2 ;;
    --reason) REASON="${2:-}"; shift 2 ;;
    --evidence) EVIDENCE="${2:-}"; shift 2 ;;
    --color) COLOR="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: argumento desconhecido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

missing=()
[[ -z "$ACTION" ]] && missing+=(--action)
[[ -z "$TYPE" ]] && missing+=(--type)
[[ -z "$PATHS" ]] && missing+=(--path)
[[ -z "$REASON" ]] && missing+=(--reason)
[[ -z "$EVIDENCE" ]] && missing+=(--evidence)
if (( ${#missing[@]} > 0 )); then
  echo "ERROR: campos obrigatórios ausentes: ${missing[*]}" >&2
  usage >&2
  exit 2
fi

DISCORD_CHANNEL_ID="1498132022634483894"
DISCORD_POSTER="${DISCORD_POSTER:-${BASE_DIR}/scripts/discord-bot-post.py}"

HOST=$(hostname)
NOW=$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z')
PENDING_SCANNER="${PENDING_SCANNER:-${BASE_DIR}/scripts/monitor_hermes_pending_writes.py}"
PENDING_FIELD="indisponível"
if PENDING_JSON=$("$PENDING_SCANNER" --summary-json 2>/dev/null); then
  if PENDING_FIELD_RESOLVED=$(printf '%s' "$PENDING_JSON" | jq -er '
      if ((.total | type) == "number") and ((.aged | type) == "number") and ((.oldest_hours | type) == "number") then
        "total=\(.total) | >=\(.threshold_hours)h=\(.aged) | mais antiga=\(.oldest_hours)h"
      else error("invalid pending summary types") end
    ' 2>/dev/null); then
    PENDING_FIELD="$PENDING_FIELD_RESOLVED"
  fi
fi
ACTION_FIELD="$(printf '%s' "$ACTION" | cut -c1-250)"
TYPE_FIELD="$(printf '%s' "$TYPE" | cut -c1-250)"
PATHS_FIELD="$(printf '%s' "$PATHS" | cut -c1-1000)"
REASON_FIELD="$(printf '%s' "$REASON" | cut -c1-1000)"
EVIDENCE_FIELD="$(printf '%s' "$EVIDENCE" | cut -c1-1000)"

PAYLOAD=$(jq -n \
  --arg content "" \
  --arg title "$TITLE — ${ACTION_FIELD}" \
  --arg action "$ACTION_FIELD" \
  --arg type "$TYPE_FIELD" \
  --arg paths "$PATHS_FIELD" \
  --arg reason "$REASON_FIELD" \
  --arg evidence "$EVIDENCE_FIELD" \
  --arg pending "$PENDING_FIELD" \
  --arg host "$HOST" \
  --arg now "$NOW" \
  --argjson color "$COLOR" \
  '{content:$content, embeds:[{title:$title, color:$color, fields:[
    {name:"Ação", value:$action, inline:true},
    {name:"Tipo", value:$type, inline:true},
    {name:"Host", value:$host, inline:true},
    {name:"Path", value:$paths, inline:false},
    {name:"Motivo", value:$reason, inline:false},
    {name:"Evidência", value:$evidence, inline:false},
    {name:"Pendências Hermes", value:$pending, inline:false},
    {name:"Horário", value:$now, inline:true}
  ]}]}')

POSTER_ARGS=(--channel-id "$DISCORD_CHANNEL_ID")
[[ "$DRY_RUN" == "1" ]] && POSTER_ARGS+=(--dry-run)
if ! POST_RESULT=$(printf '%s' "$PAYLOAD" | "$DISCORD_POSTER" "${POSTER_ARGS[@]}" 2>&1); then
  echo "ERROR: Discord bot Zeus falhou ao enviar REPORT-INFRA" >&2
  printf '%s\n' "$POST_RESULT" >&2
  exit 1
fi

if [[ "$DRY_RUN" == "1" ]]; then
  echo "OK: REPORT-INFRA embed dry-run (${POST_RESULT})"
else
  echo "OK: REPORT-INFRA embed enviado pelo bot Zeus (${POST_RESULT})"
fi
