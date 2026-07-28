#!/usr/bin/env python3
"""Auditoria local de contexto e custo dos profiles MGS.

Usa o mesmo orçamento fixo exposto por `hermes prompt-size` e estima a
conversa ativa com a mesma regra aproximada de 4 caracteres por token usada
por `/context`. Não faz chamadas de modelo, não lê valores de credenciais e
não publica mensagens. O estado JSON é escrito atomicamente para consumo por
Zeus/monitores.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PROFILES = ("zeus", "atena", "ares")
DEFAULT_STATE = Path("/root/mgs-agent/data/hermes-context-cost-audit-state.json")
DEFAULT_LOG = Path("/root/mgs-agent/logs/hermes-context-cost-audit.log")
HERMES = Path("/root/.local/bin/hermes")
WARN_PERCENT = 70.0
CRITICAL_PERCENT = 85.0


def chars_to_tokens(value: str | None) -> int:
    return math.ceil(len(value or "") / 4)


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def prompt_size(profile: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["HERMES_HOME"] = f"/root/.hermes/profiles/{profile}"
    proc = subprocess.run(
        [str(HERMES), "prompt-size", "--platform", "discord", "--json"],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"prompt-size rc={proc.returncode}: {proc.stderr.strip()[:240]}")
    return json.loads(proc.stdout)


def context_limit(model: str, provider: str) -> tuple[int, str]:
    model = (model or "").lower()
    provider = (provider or "").lower()
    if provider == "openai-codex" and model in {
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "gpt-5.5",
        "gpt-5.4",
    }:
        return 272_000, "deployed_codex_oauth_fallback"
    if model.startswith("gpt-5.6") or model in {"gpt-5.5", "gpt-5.4"}:
        return 1_050_000, "deployed_model_family_fallback"
    return 256_000, "conservative_unknown_model_fallback"


def estimate_active_messages(con: sqlite3.Connection, session_id: str) -> tuple[int, int]:
    rows = con.execute(
        """
        SELECT role, content, tool_calls, reasoning, api_content
          FROM messages
         WHERE session_id = ?
           AND COALESCE(active, 1) = 1
           AND COALESCE(compacted, 0) = 0
         ORDER BY id
        """,
        (session_id,),
    ).fetchall()
    total = 0
    for role, content, tool_calls, reasoning, api_content in rows:
        total += 4
        total += chars_to_tokens(role)
        total += chars_to_tokens(content)
        total += chars_to_tokens(tool_calls)
        total += chars_to_tokens(reasoning)
        total += chars_to_tokens(api_content)
    return total, len(rows)


def audit_profile(profile: str, now_ts: float) -> dict[str, Any]:
    home = Path(f"/root/.hermes/profiles/{profile}")
    db = home / "state.db"
    fixed = prompt_size(profile)
    system_tokens = chars_to_tokens(str((fixed.get("system_prompt") or {}).get("chars") or ""))
    # system_prompt.chars is numeric; convert directly rather than tokenizing its digits.
    system_chars = int((fixed.get("system_prompt") or {}).get("chars") or 0)
    system_tokens = math.ceil(system_chars / 4)
    tool_tokens = math.ceil(int((fixed.get("tools") or {}).get("json_bytes") or 0) / 4)
    fixed_tokens = system_tokens + tool_tokens

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute(
            """
            SELECT s.id, s.model, s.billing_provider, s.source, s.thread_id,
                   s.input_tokens, s.output_tokens, s.cache_read_tokens,
                   s.cache_write_tokens, s.reasoning_tokens,
                   s.estimated_cost_usd, s.actual_cost_usd, s.cost_status,
                   MAX(m.timestamp) AS updated_at
              FROM sessions s
              LEFT JOIN messages m ON m.session_id = s.id
             WHERE COALESCE(s.archived, 0) = 0
             GROUP BY s.id
             ORDER BY updated_at DESC
             LIMIT 1
            """
        ).fetchone()
        latest: dict[str, Any] | None = None
        if row:
            conversation_tokens, active_messages = estimate_active_messages(con, str(row[0]))
            limit, limit_source = context_limit(str(row[1] or fixed.get("model") or ""), str(row[2] or ""))
            estimated_total = fixed_tokens + conversation_tokens
            percent = round(estimated_total / limit * 100, 2) if limit else 0.0
            severity = "critical" if percent >= CRITICAL_PERCENT else "warn" if percent >= WARN_PERCENT else "ok"
            latest = {
                "session_id": row[0],
                "model": row[1] or fixed.get("model") or "",
                "provider": row[2] or "",
                "source": row[3] or "",
                "thread_id": row[4] or None,
                "updated_at": datetime.fromtimestamp(float(row[13] or 0), timezone.utc).isoformat(),
                "active_messages": active_messages,
                "conversation_tokens_estimate": conversation_tokens,
                "fixed_tokens_estimate": fixed_tokens,
                "context_tokens_estimate": estimated_total,
                "context_limit": limit,
                "context_limit_source": limit_source,
                "context_percent_estimate": percent,
                "severity": severity,
                "cumulative_usage": {
                    "input_tokens": int(row[5] or 0),
                    "output_tokens": int(row[6] or 0),
                    "cache_read_tokens": int(row[7] or 0),
                    "cache_write_tokens": int(row[8] or 0),
                    "reasoning_tokens": int(row[9] or 0),
                    "estimated_cost_usd": float(row[10] or 0),
                    "actual_cost_usd": row[11],
                    "cost_status": row[12] or "",
                },
            }

        cutoff = now_ts - 86_400
        usage = con.execute(
            """
            SELECT COUNT(DISTINCT session_id),
                   COALESCE(SUM(input_tokens), 0),
                   COALESCE(SUM(output_tokens), 0),
                   COALESCE(SUM(cache_read_tokens), 0),
                   COALESCE(SUM(cache_write_tokens), 0),
                   COALESCE(SUM(reasoning_tokens), 0),
                   COALESCE(SUM(estimated_cost_usd), 0),
                   COALESCE(SUM(actual_cost_usd), 0)
              FROM session_model_usage
             WHERE last_seen >= ?
            """,
            (cutoff,),
        ).fetchone()
    finally:
        con.close()

    top_skills = [
        {
            "name": item.get("name"),
            "index_tokens": math.ceil(int(item.get("index_line_bytes") or 0) / 4),
            "loaded_skill_tokens": math.ceil(int(item.get("skill_md_bytes") or 0) / 4),
        }
        for item in (fixed.get("skills_breakdown") or [])[:10]
    ]
    top_toolsets = [
        {
            "name": item.get("toolset"),
            "tools": int(item.get("tool_count") or 0),
            "schema_tokens": math.ceil(int(item.get("json_bytes") or 0) / 4),
        }
        for item in (fixed.get("toolsets_breakdown") or [])[:10]
    ]

    return {
        "profile": profile,
        "fixed_prompt": {
            "model": fixed.get("model") or "",
            "system_tokens_estimate": system_tokens,
            "tool_schema_tokens_estimate": tool_tokens,
            "total_tokens_estimate": fixed_tokens,
            "tool_count": int((fixed.get("tools") or {}).get("count") or 0),
            "skills_index_tokens_estimate": math.ceil(int((fixed.get("skills_index") or {}).get("chars") or 0) / 4),
        },
        "latest_session": latest,
        "sessions_touched_24h": {
            "count": int(usage[0] or 0),
            "input_tokens": int(usage[1] or 0),
            "output_tokens": int(usage[2] or 0),
            "cache_read_tokens": int(usage[3] or 0),
            "cache_write_tokens": int(usage[4] or 0),
            "reasoning_tokens": int(usage[5] or 0),
            "estimated_cost_usd": float(usage[6] or 0),
            "actual_cost_usd": float(usage[7] or 0),
            "note": "Cumulative totals for sessions with model usage updated in the last 24h; not an exact time-sliced delta.",
        },
        "top_skills_by_loaded_size": top_skills,
        "top_toolsets_by_schema_size": top_toolsets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--profile", action="append", dest="profiles")
    parser.add_argument("--print", action="store_true", dest="print_json")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for profile in args.profiles or list(DEFAULT_PROFILES):
        try:
            results.append(audit_profile(profile, now.timestamp()))
        except Exception as exc:
            errors.append({"profile": profile, "error": str(exc)[:500]})

    max_percent = max(
        (float((item.get("latest_session") or {}).get("context_percent_estimate") or 0) for item in results),
        default=0.0,
    )
    status = "failed" if errors and not results else "partial" if errors else "ok"
    payload = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "method": "prompt-size fixed budget + /context-compatible char/4 active-message estimate",
        "thresholds": {"warn_percent": WARN_PERCENT, "critical_percent": CRITICAL_PERCENT},
        "status": status,
        "max_context_percent_estimate": round(max_percent, 2),
        "profiles": results,
        "errors": errors,
    }
    atomic_json_write(args.state, payload)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{now.isoformat()} status={status} profiles={len(results)} errors={len(errors)} "
            f"max_context_percent={max_percent:.2f} state={args.state}\n"
        )
    if args.print_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
