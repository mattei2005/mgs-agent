#!/usr/bin/env bash
set -euo pipefail

cd /root/mgs-agent
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source ./.env >/dev/null 2>&1 || true
  set +a
fi

export HONCHO_API_KEY="$(op item get 'Honcho API - MGS' --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields 'api key' --reveal)"
export HONCHO_WORKSPACE="${HONCHO_WORKSPACE:-mgs-agents}"

cd /root/mgs-agent/experiments/honcho-spike
exec uv run python honcho_smoke.py
