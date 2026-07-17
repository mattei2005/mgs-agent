#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --profile <zeus|atena|ares> --thread <thread_id> --user <user_id>" >&2
}

PROFILE=""
THREAD_ID=""
USER_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --thread) THREAD_ID="${2:-}"; shift 2 ;;
    --user) USER_ID="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$PROFILE" || -z "$THREAD_ID" || -z "$USER_ID" ]]; then
  usage
  exit 2
fi

if [[ ! "$PROFILE" =~ ^[a-z][a-z0-9_-]{1,31}$ ]]; then
  echo "ERROR: invalid profile" >&2
  exit 2
fi
if [[ ! "$THREAD_ID" =~ ^[0-9]{15,25}$ || ! "$USER_ID" =~ ^[0-9]{15,25}$ ]]; then
  echo "ERROR: thread/user must be Discord snowflake IDs" >&2
  exit 2
fi

ENV_FILE="/root/.hermes/profiles/${PROFILE}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: profile env not found: $ENV_FILE" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then
  echo "ERROR: DISCORD_BOT_TOKEN not set for profile ${PROFILE}" >&2
  exit 2
fi

TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

STATUS=$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
  --max-time 15 \
  -X PUT \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data '{}' \
  "https://discord.com/api/v10/channels/${THREAD_ID}/thread-members/${USER_ID}")

if [[ "$STATUS" == "204" ]]; then
  VERIFY_STATUS=$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
    --max-time 15 \
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
    "https://discord.com/api/v10/channels/${THREAD_ID}/thread-members/${USER_ID}")
  if [[ "$VERIFY_STATUS" == "200" ]]; then
    echo "OK: member_added profile=${PROFILE} thread=${THREAD_ID} user=${USER_ID} verified=200"
    exit 0
  fi
  echo "WARN: PUT returned 204 but GET verify returned ${VERIFY_STATUS} profile=${PROFILE} thread=${THREAD_ID} user=${USER_ID}" >&2
  exit 1
fi

BODY=$(python3 - <<'PY' "$TMP_BODY"
import json, sys
p=sys.argv[1]
try:
    data=json.load(open(p))
    print(data.get('message') or data.get('code') or 'unknown error')
except Exception:
    print(open(p, errors='replace').read()[:300])
PY
)

echo "ERROR: Discord API returned ${STATUS}: ${BODY}" >&2
if [[ "$STATUS" == "403" ]]; then
  echo "HINT: Missing Access. Confirm the bot has access to the thread and the user is in the parent channel." >&2
fi
exit 1
