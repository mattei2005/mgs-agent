#!/usr/bin/env bash
set -euo pipefail

# MGS/Atena OpenHands wrapper — GPT-5.5/OpenAI-Codex only.
# Rodolfo policy: use GPT-5.5 for everything by default. Do not use Anthropic,
# Claude, Haiku, OpenRouter, or any other provider unless Rodolfo explicitly
# approves an exception.
#
# Usage:
#   /root/mgs-agent/scripts/run-openhands-atena.sh -t 'task prompt'
#   /root/mgs-agent/scripts/run-openhands-atena.sh --resume <uuid> -t 'continue task'

AUTH_STORE="${HERMES_CODEX_AUTH_STORE:-/root/.hermes/profiles/atena/auth.json}"
CODEX_BASE_URL="https://chatgpt.com/backend-api/codex"
CODEX_MODEL="openai/gpt-5.5"
PERSIST_DIR="${OPENHANDS_PERSISTENCE_DIR:-/root/.hermes/profiles/atena/home/.openhands-gpt55}"

if ! command -v openhands >/dev/null 2>&1; then
  echo "ERROR: OpenHands CLI not found" >&2
  exit 1
fi

if [[ ! -f "$AUTH_STORE" ]]; then
  echo "ERROR: Hermes Codex auth store not found: $AUTH_STORE" >&2
  echo "Fix: re-authenticate OpenAI-Codex for the Atena profile, then retry." >&2
  exit 1
fi

mkdir -p "$PERSIST_DIR"
chmod 700 "$PERSIST_DIR"

# OpenHands/LiteLLM must stream against the Codex backend. Env overrides do not
# expose the stream flag, so create a local agent_settings.json with stream=true.
OPENHANDS_SUPPRESS_BANNER=1 /root/.local/share/uv/tools/openhands/bin/python - <<'PY'
from pathlib import Path
from openhands.sdk.llm import LLM
from openhands_cli.utils import get_default_cli_agent
import os
persist = Path(os.environ.get('OPENHANDS_PERSISTENCE_DIR', '/root/.hermes/profiles/atena/home/.openhands-gpt55'))
persist.mkdir(parents=True, exist_ok=True)
llm = LLM(
    model='openai/gpt-5.5',
    api_key='placeholder-overridden-at-runtime',
    base_url='https://chatgpt.com/backend-api/codex',
    usage_id='agent',
    stream=True,
)
agent = get_default_cli_agent(llm)
(persist / 'agent_settings.json').write_text(agent.model_dump_json(indent=2) + '\n')
PY

# Export the OpenAI-Codex OAuth access token without printing it.
eval "$(python3 - <<'PY'
import json, shlex, os
from pathlib import Path
p = Path(os.environ.get('HERMES_CODEX_AUTH_STORE', '/root/.hermes/profiles/atena/auth.json'))
data = json.loads(p.read_text())
provider = (data.get('providers') or {}).get('openai-codex') or {}
tokens = provider.get('tokens') or {}
access = (tokens.get('access_token') or '').strip()
if not access:
    print("echo 'ERROR: openai-codex access_token missing for Atena. Re-authenticate OpenAI-Codex, then retry.' >&2")
    print('exit 1')
else:
    print('export LLM_API_KEY=' + shlex.quote(access))
PY
)"

export OPENHANDS_SUPPRESS_BANNER=1
export OPENHANDS_PERSISTENCE_DIR="$PERSIST_DIR"
export OPENHANDS_CONVERSATIONS_DIR="$PERSIST_DIR/conversations"
export LLM_MODEL="$CODEX_MODEL"
export LLM_BASE_URL="$CODEX_BASE_URL"

# Guardrails: fail if any caller tried to steer this wrapper to Claude/Anthropic.
lower_model="$(printf '%s' "$LLM_MODEL" | tr '[:upper:]' '[:lower:]')"
lower_base="$(printf '%s' "$LLM_BASE_URL" | tr '[:upper:]' '[:lower:]')"
if [[ "$lower_model" == anthropic/* || "$lower_model" == *claude* || "$lower_base" == *api.anthropic.com* ]]; then
  echo "ERROR: Anthropic/Claude backend blocked. GPT-5.5/OpenAI-Codex only." >&2
  exit 3
fi

exec openhands --headless --json --override-with-envs --exit-without-confirmation "$@"
