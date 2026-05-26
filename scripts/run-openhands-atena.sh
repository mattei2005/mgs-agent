#!/usr/bin/env bash
set -euo pipefail

# MGS/Atena OpenHands wrapper.
# Policy: do NOT auto-resolve or use Anthropic/Claude API keys.
# Policy: do NOT silently use ambient OpenAI/LiteLLM credentials either.
#
# OpenHands requires a LiteLLM-compatible backend. Hermes ChatGPT/Codex OAuth is
# not treated here as an approved OpenHands backend because passing Hermes OAuth
# tokens directly into OpenHands/LiteLLM can create unvalidated behavior.
#
# Usage with an explicitly approved non-Anthropic backend:
#   MGS_OPENHANDS_BACKEND_APPROVED=1 \
#   LLM_MODEL="openrouter/openai/gpt-4o-mini" \
#   LLM_API_KEY="<approved-non-anthropic-key>" \
#   LLM_BASE_URL="https://openrouter.ai/api/v1" \
#   /root/mgs-agent/scripts/run-openhands-atena.sh -t 'task prompt'
#
# Anthropic/Claude exception requires explicit Rodolfo approval plus:
#   ALLOW_ANTHROPIC_OPENHANDS=1

if ! command -v openhands >/dev/null 2>&1; then
  echo "ERROR: OpenHands CLI not found" >&2
  exit 1
fi

export OPENHANDS_SUPPRESS_BANNER=1

MODEL="${LLM_MODEL:-}"
API_KEY="${LLM_API_KEY:-}"
BASE_URL="${LLM_BASE_URL:-}"

if [[ "${MGS_OPENHANDS_BACKEND_APPROVED:-0}" != "1" || -z "$MODEL" || -z "$API_KEY" ]]; then
  cat >&2 <<'EOF'
ERROR: OpenHands backend not configured/approved.

Atena is on GPT-5.5 via Hermes/openai-codex OAuth, but OpenHands CLI can also
see ambient LiteLLM/OpenAI env vars. To avoid accidental pay-per-token or
unsupported OAuth usage, this wrapper refuses to run unless
MGS_OPENHANDS_BACKEND_APPROVED=1 is set with LLM_MODEL + LLM_API_KEY
(+ LLM_BASE_URL when needed).

This wrapper does not fetch Anthropic from 1Password because MGS policy is zero
Anthropic/Claude pay-per-token by default. Use Hermes-native delegate_task when
no explicitly approved OpenHands backend is available.
EOF
  exit 2
fi

if [[ "${ALLOW_ANTHROPIC_OPENHANDS:-0}" != "1" ]]; then
  lower_model="$(printf '%s' "$MODEL" | tr '[:upper:]' '[:lower:]')"
  lower_base="$(printf '%s' "$BASE_URL" | tr '[:upper:]' '[:lower:]')"
  if [[ "$lower_model" == anthropic/* || "$lower_model" == *claude* || "$lower_base" == *api.anthropic.com* ]]; then
    echo "ERROR: Anthropic/Claude backend blocked by MGS policy. Set ALLOW_ANTHROPIC_OPENHANDS=1 only after explicit Rodolfo approval." >&2
    exit 3
  fi
fi

export LLM_MODEL="$MODEL"
export LLM_API_KEY="$API_KEY"
if [[ -n "$BASE_URL" ]]; then
  export LLM_BASE_URL="$BASE_URL"
else
  unset LLM_BASE_URL || true
fi

exec openhands --headless --json --override-with-envs --exit-without-confirmation "$@"
