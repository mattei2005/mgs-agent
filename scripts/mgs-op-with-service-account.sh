#!/usr/bin/env bash
# Resolve 1Password through the canonical MGS service account.
set -euo pipefail

ENV_FILE="/root/mgs-agent/.env"
REAL_OP="/usr/bin/op"

if [[ ! -r "$ENV_FILE" ]]; then
  printf 'ERROR: canonical MGS environment is not readable: %s\n' "$ENV_FILE" >&2
  exit 1
fi
if [[ ! -x "$REAL_OP" ]]; then
  printf 'ERROR: 1Password CLI is unavailable: %s\n' "$REAL_OP" >&2
  exit 1
fi

set -a
# shellcheck source=/root/mgs-agent/.env
source "$ENV_FILE"
set +a

if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  printf 'ERROR: OP_SERVICE_ACCOUNT_TOKEN is absent from the canonical MGS environment\n' >&2
  exit 1
fi

exec "$REAL_OP" "$@"
