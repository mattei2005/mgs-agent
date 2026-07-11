#!/usr/bin/env bash
# ares-report-infra.sh — envia REPORT-INFRA do Ares via bot Zeus direto.
# Uso:
#   /root/mgs-agent/scripts/ares-report-infra.sh --file /path/report.md
#   printf 'mensagem' | /root/mgs-agent/scripts/ares-report-infra.sh
#   /root/mgs-agent/scripts/ares-report-infra.sh --dry-run --file /path/report.md

set -euo pipefail

BASE_DIR="/root/mgs-agent"
DISCORD_CHANNEL_ID="1498132022634483894"
DISCORD_POSTER="${BASE_DIR}/scripts/discord-bot-post.py"
DRY_RUN=0
INPUT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --file)
      INPUT_FILE="${2:-}"
      shift 2
      ;;
    *)
      echo "Uso: $0 [--dry-run] [--file /path/report.md]" >&2
      exit 2
      ;;
  esac
done

if [[ -n "$INPUT_FILE" ]]; then
  [[ -f "$INPUT_FILE" ]] || { echo "arquivo não encontrado: $INPUT_FILE" >&2; exit 2; }
  CONTENT=$(cat "$INPUT_FILE")
else
  CONTENT=$(cat)
fi

if [[ -z "${CONTENT//[[:space:]]/}" ]]; then
  echo "conteúdo vazio" >&2
  exit 2
fi

PAYLOAD=$(python3 - "$CONTENT" <<'PY'
import json, sys
content = sys.argv[1]
print(json.dumps({"content": content[:1900]}))
PY
)

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'PY' "$PAYLOAD"
import json, sys
p=json.loads(sys.argv[1])
print(f"dry_run=ok content_len={len(p.get('content',''))}")
PY
  exit 0
fi

if POST_RESULT=$(printf '%s' "$PAYLOAD" | "$DISCORD_POSTER" --channel-id "$DISCORD_CHANNEL_ID" 2>&1); then
  echo "sent=ok transport=zeus_bot ${POST_RESULT}"
  exit 0
fi

echo "sent=failed transport=zeus_bot" >&2
printf '%s\n' "$POST_RESULT" >&2
exit 1
