#!/usr/bin/env bash
# ares-report-infra.sh — envia REPORT-INFRA do Ares para #alerts-infra via webhook 1Password.
# Uso:
#   /root/mgs-agent/scripts/ares-report-infra.sh --file /path/report.md
#   printf 'mensagem' | /root/mgs-agent/scripts/ares-report-infra.sh
#   /root/mgs-agent/scripts/ares-report-infra.sh --dry-run --file /path/report.md

set -euo pipefail

BASE_DIR="/root/mgs-agent"
WEBHOOK_ITEM="Discord Webhook - Alerts Infra Channel"
VAULT="${OP_DEFAULT_VAULT:-MGS Conteúdo}"
USER_AGENT="MGS-Ares-InfraReporter/1.0"
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

set -a
# shellcheck source=/dev/null
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

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

WEBHOOK_URL=$(op item get "$WEBHOOK_ITEM" --vault "$VAULT" --fields label=webhook_url --reveal 2>/dev/null || true)
if [[ "$WEBHOOK_URL" != https://* ]]; then
  echo "webhook ausente/inválido no 1Password: item='${WEBHOOK_ITEM}' field='webhook_url'" >&2
  exit 1
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

TMP_BODY=$(mktemp)
HTTP_CODE=$(curl -sS \
  -A "$USER_AGENT" \
  -o "$TMP_BODY" \
  -w '%{http_code}' \
  --max-time 15 \
  -H 'Content-Type: application/json' \
  -d "$PAYLOAD" \
  "$WEBHOOK_URL" || true)

if [[ "$HTTP_CODE" == "204" || "$HTTP_CODE" == "200" ]]; then
  echo "sent=ok http_status=${HTTP_CODE}"
  rm -f "$TMP_BODY"
  exit 0
fi

echo "sent=failed http_status=${HTTP_CODE}" >&2
sed -E 's/[A-Za-z0-9_\-]{24,}/[REDACTED]/g' "$TMP_BODY" >&2 || true
rm -f "$TMP_BODY"
exit 1
