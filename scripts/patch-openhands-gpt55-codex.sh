#!/usr/bin/env bash
set -euo pipefail

# Idempotent MGS compatibility patch for OpenHands CLI + GPT-5.5 Codex OAuth.
# Why: OpenHands 1.16 env override path cannot persist the private subscription
# flag and headless mode may call streaming paths without token callbacks. The
# ChatGPT Codex backend requires stream=true and rejects params such as
# max_output_tokens/temperature/reasoning. This patch keeps OpenHands on
# GPT-5.5/OpenAI-Codex instead of falling back to Anthropic/Claude.

LLM_PY="${OPENHANDS_LLM_PY:-/root/.local/share/uv/tools/openhands/lib/python3.12/site-packages/openhands/sdk/llm/llm.py}"

if [[ ! -f "$LLM_PY" ]]; then
  echo "ERROR: OpenHands llm.py not found: $LLM_PY" >&2
  exit 1
fi

python3 - "$LLM_PY" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
original = s

old1 = '''        if enable_streaming:\n            if on_token is None:\n                raise ValueError("Streaming requires an on_token callback")\n            kwargs["stream"] = True\n'''
new1 = '''        if enable_streaming:\n            if on_token is None:\n                # MGS patch: Codex backend requires stream=True, while OpenHands\n                # headless completion path may call without a token callback.\n                # Use a no-op callback so GPT-5.5/OpenAI-Codex can run without\n                # falling back to Anthropic/other providers.\n                on_token = lambda _token: None\n            kwargs["stream"] = True\n'''
if old1 in s:
    s = s.replace(old1, new1, 1)

old2 = '''        if user_enable_streaming:\n            if on_token is None and not self.is_subscription:\n                # We allow on_token to be None for subscription mode\n                raise ValueError("Streaming requires an on_token callback")\n            kwargs["stream"] = True\n'''
new2 = '''        if user_enable_streaming:\n            if on_token is None and not self.is_subscription:\n                # MGS patch: Codex backend requires stream=True, while OpenHands\n                # headless responses path may call without a token callback.\n                # Use a no-op callback so GPT-5.5/OpenAI-Codex can run without\n                # falling back to Anthropic/other providers.\n                on_token = lambda _token: None\n            kwargs["stream"] = True\n'''
if old2 in s:
    s = s.replace(old2, new2, 1)

old3 = '''        return self._is_subscription\n\n    def restore_metrics(self, metrics: Metrics) -> None:\n'''
new3 = '''        # MGS patch: OpenHands env override path cannot persist the private\n        # _is_subscription flag. Treat the ChatGPT Codex backend as subscription\n        # so unsupported params (max_output_tokens, temperature, reasoning, etc.)\n        # are omitted and GPT-5.5/OpenAI-Codex can be used everywhere.\n        return self._is_subscription or (\n            self.base_url is not None\n            and "chatgpt.com/backend-api/codex" in str(self.base_url)\n        )\n\n    def restore_metrics(self, metrics: Metrics) -> None:\n'''
if old3 in s:
    s = s.replace(old3, new3, 1)

missing = []
for marker in [
    'headless completion path may call without a token callback',
    'headless responses path may call without a token callback',
    'chatgpt.com/backend-api/codex" in str(self.base_url)',
]:
    if marker not in s:
        missing.append(marker)
if missing:
    raise SystemExit('ERROR: patch markers missing: ' + ', '.join(missing))

if s != original:
    p.write_text(s)
    print('patched')
else:
    print('already_patched')
PY

/root/.local/share/uv/tools/openhands/bin/python -m py_compile "$LLM_PY"
