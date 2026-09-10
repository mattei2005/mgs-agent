"""Regression coverage for hidden tool-call argument truncation.

Routers may rewrite finish_reason="length" to "tool_calls".  The runtime must
retry/rebuild without executing partial arguments and must never expose the old
internal truncation placeholder as the user-visible answer.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


OLD_PLACEHOLDER = "Response truncated due to output length limit"
SAFE_FALLBACK = (
    "A execução foi pausada no último estado validado porque a próxima ação não "
    "pôde ser reconstruída com segurança. Nenhuma chamada incompleta foi executada."
)


def _tool_call(arguments: str):
    return SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="terminal", arguments=arguments),
    )


class _Agent:
    valid_tool_names = {"terminal"}
    log_prefix = ""
    max_tokens = 1024

    def __init__(self):
        self._invalid_tool_retries = 0
        self._invalid_json_retries = 0
        self._hidden_truncated_tool_retries = 0
        self._hidden_truncated_tool_recoveries = 0
        self._ephemeral_max_output_tokens = None
        self.status = []
        self.persisted = False
        self.cleaned = False

    def _uniquify_tool_call_ids(self, tool_calls):
        return None

    def _repair_tool_call(self, name):
        return None

    def _buffer_vprint(self, message):
        self.status.append(message)

    def _vprint(self, message, force=False):
        self.status.append(message)

    def _flush_status_buffer(self):
        return None

    def _cleanup_task_resources(self, task_id):
        self.cleaned = True

    def _persist_session(self, messages, conversation_history):
        self.persisted = True

    def _build_assistant_message(self, assistant_message, finish_reason):
        tc = assistant_message.tool_calls[0]
        return {
            "role": "assistant",
            "content": assistant_message.content or "",
            "finish_reason": finish_reason,
            "tool_calls": [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }],
        }


@pytest.mark.skipif(
    importlib.util.find_spec("agent.turn_tool_validation") is None,
    reason="modular tool validation exists only in Hermes v0.21.1+",
)
def test_hidden_truncated_tool_call_retries_then_rebuilds_without_execution():
    from agent.turn_tool_validation import validate_tool_calls

    agent = _Agent()
    messages = [{"role": "user", "content": "continue"}]

    for expected_retry in range(1, 5):
        msg = SimpleNamespace(content="", tool_calls=[_tool_call('{"command":"unterminated')])
        verdict = validate_tool_calls(
            agent,
            msg,
            "tool_calls",
            messages=messages,
            conversation_history=None,
            api_call_count=expected_retry,
            effective_task_id="task",
        )
        assert verdict.action == "continue"
        assert messages == [{"role": "user", "content": "continue"}]
        assert agent._hidden_truncated_tool_retries == expected_retry
        assert agent._ephemeral_max_output_tokens is not None
        assert agent._ephemeral_max_output_tokens <= 32768

    msg = SimpleNamespace(content="", tool_calls=[_tool_call('{"command":"unterminated')])
    verdict = validate_tool_calls(
        agent,
        msg,
        "tool_calls",
        messages=messages,
        conversation_history=None,
        api_call_count=5,
        effective_task_id="task",
    )
    assert verdict.action == "continue"
    assert [row["role"] for row in messages[-2:]] == ["assistant", "tool"]
    assert "were not executed" in messages[-1]["content"]
    assert OLD_PLACEHOLDER not in str(messages)
    assert agent._hidden_truncated_tool_recoveries == 1


@pytest.mark.skipif(
    importlib.util.find_spec("agent.turn_tool_validation") is None,
    reason="modular tool validation exists only in Hermes v0.21.1+",
)
def test_hidden_truncated_tool_call_terminal_fallback_is_safe_and_specific():
    from agent.turn_tool_validation import validate_tool_calls

    agent = _Agent()
    agent._hidden_truncated_tool_retries = 4
    agent._hidden_truncated_tool_recoveries = 2
    messages = [{"role": "user", "content": "continue"}]
    msg = SimpleNamespace(content="", tool_calls=[_tool_call('{"command":"unterminated')])

    verdict = validate_tool_calls(
        agent,
        msg,
        "tool_calls",
        messages=messages,
        conversation_history=None,
        api_call_count=9,
        effective_task_id="task",
    )

    assert verdict.action == "return"
    assert verdict.result is not None
    assert verdict.result["final_response"] == SAFE_FALLBACK
    assert OLD_PLACEHOLDER not in verdict.result["final_response"]
    assert agent.cleaned and agent.persisted


def test_runtime_source_never_exposes_old_truncation_placeholder():
    root = Path(__file__).resolve().parents[2]
    sources = [root / "agent" / "conversation_loop.py"]
    modular = root / "agent" / "turn_tool_validation.py"
    truncation = root / "agent" / "turn_truncation.py"
    if modular.exists():
        sources.extend([modular, truncation])
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    assert OLD_PLACEHOLDER not in combined
    assert "_hidden_truncated_tool_retries" in combined
    assert "were not executed" in combined
