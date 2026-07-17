#!/usr/bin/env python3
"""MGS Honcho memory copilot.

Safe auxiliary layer for Zeus/Atena/Ares. It sends only caller-provided,
sanitized context to Honcho and prints hypotheses/context reminders. It is not a
source of truth and never executes operational actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from honcho import Honcho

WORKSPACE = os.getenv("HONCHO_WORKSPACE", "mgs-agents")
API_KEY = os.getenv("HONCHO_API_KEY")
MAX_CONTEXT_CHARS = int(os.getenv("MGS_MEMORY_COPILOT_MAX_CONTEXT_CHARS", "6000"))
COPILOT_TIMEOUT_SECONDS = int(os.getenv("MGS_MEMORY_COPILOT_TIMEOUT_SECONDS", "75"))


class CopilotTimeout(TimeoutError):
    pass


def _alarm_handler(signum, frame):  # noqa: ARG001
    raise CopilotTimeout(f"Honcho copilot timed out after {COPILOT_TIMEOUT_SECONDS}s")

SECRET_PATTERNS = [
    r"hch-v3-[A-Za-z0-9]+",
    r"sk-[A-Za-z0-9_\-]{12,}",
    r"github_pat_[A-Za-z0-9_]+",
    r"ghp_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9_\-]+",
    r"AKIA[A-Za-z0-9]{16}",
    r"(?i)(authorization:\s*bearer\s+)\S+",
    r"(?i)(password|token|secret|api[_-]?key|application_password)\s*[=:]\s*\S+",
    r"https?://[^\s/@]+:[^\s/@]+@",
]

REDACTIONS = [
    (r"hch-v3-[A-Za-z0-9]+", "[REDACTED_HONCHO_KEY]"),
    (r"(sk-|xox[baprs]-|ghp_|github_pat_|AKIA)[A-Za-z0-9_\-]{8,}", "[REDACTED_TOKEN]"),
    (r"(?i)(authorization:\s*bearer\s+)\S+", r"\1[REDACTED]"),
    (r"(?i)(password|token|secret|api[_-]?key|application_password)\s*[=:]\s*\S+", "[REDACTED_CREDENTIAL_FIELD]"),
    (r"https?://[^\s/@]+:[^\s/@]+@", "https://[REDACTED_CREDS]@"),
    (r"<@[0-9]{12,25}>", "<@USER_ID>"),
]

AGENT_PROFILES = {
    "zeus": {
        "peer": "zeus",
        "target": "mgs-system",
        "session": "mgs-memory-copilot-zeus",
        "role": "General Manager / cross-agent operations",
    },
    "atena": {
        "peer": "atena",
        "target": "mgs-content",
        "session": "mgs-memory-copilot-atena",
        "role": "content/REC/P1 production analyst",
    },
    "ares": {
        "peer": "ares",
        "target": "mgs-growth",
        "session": "mgs-memory-copilot-ares",
        "role": "campaign/growth analysis assistant",
    },

}


def classify_honcho_exception(exc: Exception) -> tuple[str, str, str]:
    """Return (status, public_content, action_required) for Honcho failures.

    Keep this deliberately string-based so the wrapper remains resilient across
    honcho-ai SDK versions without importing provider-specific exception classes.
    """
    exc_type = type(exc).__name__
    msg = str(exc)
    if "cold storage" in msg.lower():
        return (
            "cold_storage",
            "Honcho tenant is in cold storage due to inactivity. Resume it from https://app.honcho.dev, then rerun the MGS health check.",
            "manual_resume_app_honcho_dev",
        )
    return (
        "unavailable",
        f"Honcho copilot unavailable ({exc_type}). Proceed without Honcho and rely on canonical MGS sources.",
        "none",
    )


def redact(text: str) -> str:
    out = text or ""
    for pattern, replacement in REDACTIONS:
        out = re.sub(pattern, replacement, out)
    if len(out) > MAX_CONTEXT_CHARS:
        out = out[:MAX_CONTEXT_CHARS] + "\n[TRUNCATED_BY_MGS_MEMORY_COPILOT]"
    return out


def secret_hits(text: str) -> list[str]:
    return [pattern for pattern in SECRET_PATTERNS if re.search(pattern, text or "", re.I)]


def read_context(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.context:
        chunks.append(args.context)
    if args.context_file:
        path = Path(args.context_file)
        chunks.append(path.read_text(errors="replace"))
    if not sys.stdin.isatty():
        stdin = sys.stdin.read()
        if stdin.strip():
            chunks.append(stdin)
    return "\n\n".join(chunks).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MGS Honcho memory/raciocínio copilot")
    p.add_argument("--agent", required=True, choices=sorted(AGENT_PROFILES), help="Agente chamador")
    p.add_argument("--question", required=True, help="Pergunta/análise que Honcho deve ajudar a responder")
    p.add_argument("--context", help="Contexto sanitizável inline")
    p.add_argument("--context-file", help="Arquivo com contexto a sanitizar antes de enviar")
    p.add_argument("--session", help="Override de sessão Honcho")
    p.add_argument("--json", action="store_true", help="Emitir JSON em vez de bloco textual")
    return p.parse_args()


def main() -> int:
    if not API_KEY:
        print("BLOCKED: HONCHO_API_KEY missing", file=sys.stderr)
        return 2

    args = parse_args()
    profile = AGENT_PROFILES[args.agent]
    raw_context = read_context(args)
    sanitized_context = redact(raw_context)
    question = redact(args.question.strip())

    payload = json.dumps(
        {
            "policy": "Honcho is a memory/reasoning copilot only. Output is hypothesis/context, not canonical truth. Agent must validate facts against MGS canonical sources before reporting or acting.",
            "agent": args.agent,
            "agent_role": profile["role"],
            "question": question,
            "context": sanitized_context or "[no extra context provided]",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
        indent=2,
    )

    hits = secret_hits(payload)
    if hits:
        print("BLOCKED: secret-like pattern detected after sanitization; nothing sent to Honcho", file=sys.stderr)
        return 3

    session_id = args.session or profile["session"]
    try:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(COPILOT_TIMEOUT_SECONDS)
        honcho = Honcho(workspace_id=WORKSPACE, api_key=API_KEY, environment="production")
        session = honcho.session(session_id)
        peers = {
            name: honcho.peer(name)
            for name in [
                "zeus",
                "atena",
                "ares",
                "mgs-system",
                "mgs-content",
                "mgs-growth",
                "mgs-creative",
            ]
        }

        caller = peers[profile["peer"]]
        system = peers["mgs-system"]
        target = peers[profile["target"]]

        session.add_messages(
            [
                system.message("MGS memory copilot event. Sanitized context only. Honcho must produce hypotheses; MGS agent validates canonical facts before use."),
                caller.message(payload),
            ]
        )

        prompt = (
            "Act as a memory/reasoning copilot for the MGS agent. "
            "Return concise operational context, patterns, caveats, and validation steps. "
            "Do not claim canonical truth. Mark uncertainty. "
            f"Question: {question}"
        )
        try:
            response = caller.chat(prompt, target=target, session=session.id)
        except TypeError:
            try:
                response = caller.chat(prompt, session=session.id)
            except TypeError:
                response = caller.chat(prompt)
        content = str(getattr(response, "content", response)).strip()
        status = "ok"
        action_required = "none"
    except Exception as exc:  # Honcho is auxiliary; agents must degrade gracefully.
        status, content, action_required = classify_honcho_exception(exc)
    finally:
        try:
            signal.alarm(0)
        except Exception:
            pass

    result = {
        "status": status,
        "workspace": WORKSPACE,
        "session": session_id,
        "agent": args.agent,
        "copilot_role": "hypothesis/context only",
        "question": question,
        "hypothesis": content,
        "validation_required": True,
        "action_required": action_required,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("HONCHO_MEMORY_COPILOT — hipótese/contexto auxiliar")
        print("Fonte de verdade: NÃO. Validar antes de reportar/agir.")
        print(f"Agente: {args.agent}")
        print(f"Sessão: {session_id}")
        print("\nHipótese/contexto:")
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
