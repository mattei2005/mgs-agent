#!/usr/bin/env bash
# ares-report-infra.sh — adaptador legado do Ares para o embed canônico.
# Uso:
#   /root/mgs-agent/scripts/ares-report-infra.sh --file /path/report.md
#   printf 'mensagem' | /root/mgs-agent/scripts/ares-report-infra.sh
#   /root/mgs-agent/scripts/ares-report-infra.sh --dry-run --file /path/report.md

set -euo pipefail

BASE_DIR="/root/mgs-agent"
CANONICAL_HELPER="${BASE_DIR}/scripts/send-report-infra-embed.sh"
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

FIELDS=$(python3 - "$CONTENT" <<'PY'
import json, re, sys
content = sys.argv[1]
values = {}
for raw in content.splitlines():
    line = raw.strip()
    match = re.match(r"^(Ação|Acao|Tipo|Path|Paths|Motivo|Evidência|Evidencia):\s*(.*)$", line, re.I)
    if match:
        key = match.group(1).lower()
        values[key] = match.group(2).strip()
def first(*keys, default=""):
    for key in keys:
        if values.get(key):
            return values[key]
    return default
print(json.dumps({
    "action": first("ação", "acao", default="modificada"),
    "type": first("tipo", default="infra"),
    "path": first("path", "paths", default="não informado"),
    "reason": first("motivo", default="REPORT-INFRA emitido pelo Ares"),
    "evidence": first("evidência", "evidencia", default="payload legado convertido para embed"),
}, ensure_ascii=False))
PY
)

ACTION=$(jq -r '.action' <<<"$FIELDS")
TYPE=$(jq -r '.type' <<<"$FIELDS")
PATHS=$(jq -r '.path' <<<"$FIELDS")
REASON=$(jq -r '.reason' <<<"$FIELDS")
EVIDENCE=$(jq -r '.evidence' <<<"$FIELDS")

ARGS=(--action "$ACTION" --type "$TYPE" --path "$PATHS" --reason "$REASON" --evidence "$EVIDENCE")
[[ "$DRY_RUN" == "1" ]] && ARGS+=(--dry-run)
exec "$CANONICAL_HELPER" "${ARGS[@]}"
