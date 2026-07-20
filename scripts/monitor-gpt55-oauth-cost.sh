#!/usr/bin/env python3
"""Daily real GPT-5.6 OAuth usage report across active MGS profiles.

The legacy filename is preserved for cron compatibility. Runtime telemetry comes
from Hermes' profile-local SQLite session_model_usage table, which includes
Discord, CLI/oneshot, cron, tool and subagent sessions. The report fails closed
if any active profile cannot be read; it never substitutes a gateway-log zero.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROFILES = ("zeus", "atena", "ares")
PROFILES_ROOT = Path("/root/.hermes/profiles")
CHANNEL_ID_DEFAULT = "1498132022634483894"
EXPECTED_MODEL = "gpt-5.6-sol"
EXPECTED_PROVIDER = "openai-codex"
EXPECTED_BILLING_MODE = "subscription_included"
HYPOTHETICAL_INPUT_USD_PER_MILLION = 7.00
HYPOTHETICAL_OUTPUT_USD_PER_MILLION = 21.00


def load_env_file(path: Path, env: dict[str, str]) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in env:
            env[key] = value


def profile_model(profile: str) -> tuple[str, str]:
    path = PROFILES_ROOT / profile / "config.yaml"
    if not path.exists():
        return "missing", "missing"
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        model = data.get("model", {}) if isinstance(data, dict) else {}
        if isinstance(model, dict):
            return str(model.get("default") or "unknown"), str(model.get("provider") or "unknown")
    except Exception:
        pass
    return "unknown", "unknown"


def profile_usage(profile: str, cutoff: datetime, now: datetime) -> dict[str, Any]:
    model, provider = profile_model(profile)
    path = PROFILES_ROOT / profile / "state.db"
    base: dict[str, Any] = {
        "profile": profile,
        "model": model,
        "provider": provider,
        "sessions": 0,
        "api_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "actual_cost_usd": 0.0,
        "sources": {},
        "billing_modes": [],
        "unexpected_usage": [],
        "boundary_sessions": 0,
        "telemetry_error": None,
    }
    if not path.exists():
        base["telemetry_error"] = f"state.db ausente para {profile}"
        return base

    query = """
        SELECT s.id, s.source, u.model, u.billing_provider, u.billing_mode,
               u.api_call_count, u.input_tokens, u.output_tokens,
               u.cache_read_tokens, u.cache_write_tokens, u.reasoning_tokens,
               u.actual_cost_usd, u.first_seen, u.last_seen
          FROM session_model_usage AS u
          JOIN sessions AS s ON s.id = u.session_id
         WHERE u.last_seen >= ? AND u.last_seen < ?
    """
    try:
        uri = f"file:{path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (cutoff.timestamp(), now.timestamp())).fetchall()
    except Exception as exc:
        base["telemetry_error"] = f"falha SQLite {profile}: {type(exc).__name__}: {exc}"
        return base

    sources: Counter[str] = Counter()
    billing_modes: set[str] = set()
    unexpected: set[str] = set()
    session_ids: set[str] = set()
    for row in rows:
        session_ids.add(str(row["id"]))
        sources[str(row["source"] or "unknown")] += int(row["api_call_count"] or 0)
        billing_mode = str(row["billing_mode"] or "unknown")
        billing_modes.add(billing_mode)
        row_model = str(row["model"] or "unknown")
        row_provider = str(row["billing_provider"] or "unknown")
        if (row_model, row_provider, billing_mode) != (
            EXPECTED_MODEL,
            EXPECTED_PROVIDER,
            EXPECTED_BILLING_MODE,
        ):
            unexpected.add(f"{row_provider}/{row_model}/{billing_mode}")
        first_seen = row["first_seen"]
        if first_seen is None or float(first_seen) < cutoff.timestamp():
            base["boundary_sessions"] += 1
        for field in (
            "api_call_count",
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_write_tokens",
            "reasoning_tokens",
        ):
            target = "api_calls" if field == "api_call_count" else field
            base[target] += int(row[field] or 0)
        base["actual_cost_usd"] += float(row["actual_cost_usd"] or 0.0)

    base["sessions"] = len(session_ids)
    base["sources"] = dict(sorted(sources.items()))
    base["billing_modes"] = sorted(billing_modes)
    base["unexpected_usage"] = sorted(unexpected)
    base["actual_cost_usd"] = round(base["actual_cost_usd"], 6)
    return base


def pt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def pt_usd(value: float) -> str:
    return f"US$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_report(now: datetime | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        now = now.astimezone()
    cutoff = now - timedelta(hours=24)
    rows = [profile_usage(profile, cutoff, now) for profile in PROFILES]
    telemetry_errors = [row["telemetry_error"] for row in rows if row["telemetry_error"]]
    total_sessions = sum(row["sessions"] for row in rows)
    total_calls = sum(row["api_calls"] for row in rows)
    input_tokens = sum(row["input_tokens"] for row in rows)
    output_tokens = sum(row["output_tokens"] for row in rows)
    cache_read_tokens = sum(row["cache_read_tokens"] for row in rows)
    cache_write_tokens = sum(row["cache_write_tokens"] for row in rows)
    reasoning_tokens = sum(row["reasoning_tokens"] for row in rows)
    actual_cost_usd = round(sum(row["actual_cost_usd"] for row in rows), 6)
    boundary_sessions = sum(row["boundary_sessions"] for row in rows)
    source_totals: Counter[str] = Counter()
    unexpected_usage: set[str] = set()
    for row in rows:
        source_totals.update(row["sources"])
        unexpected_usage.update(row["unexpected_usage"])

    hypothetical_usd = round(
        input_tokens / 1_000_000 * HYPOTHETICAL_INPUT_USD_PER_MILLION
        + output_tokens / 1_000_000 * HYPOTHETICAL_OUTPUT_USD_PER_MILLION,
        2,
    )
    config_ok = all(
        row["model"] == EXPECTED_MODEL and row["provider"] == EXPECTED_PROVIDER
        for row in rows
    )
    billing_ok = not unexpected_usage and all(
        not row["billing_modes"] or row["billing_modes"] == [EXPECTED_BILLING_MODE]
        for row in rows
    )
    coverage = "exata" if boundary_sessions == 0 else f"agregada; {boundary_sessions} sessão(ões) cruzam o início da janela"
    source_text = " · ".join(f"{source}: {pt_int(calls)}" for source, calls in sorted(source_totals.items())) or "sem uso"

    payload = {
        "content": "",
        "embeds": [{
            "title": "GPT-5.6 OAuth — uso real das últimas 24h",
            "color": 3066993 if not telemetry_errors and config_ok and billing_ok else 15105570,
            "fields": [
                {"name": "Chamadas LLM reais", "value": pt_int(total_calls), "inline": True},
                {"name": "Sessões com uso", "value": pt_int(total_sessions), "inline": True},
                {
                    "name": "Tokens reais",
                    "value": (
                        f"Entrada: {pt_int(input_tokens)} · saída: {pt_int(output_tokens)}\n"
                        f"Cache lido: {pt_int(cache_read_tokens)} · gravado: {pt_int(cache_write_tokens)}"
                    ),
                    "inline": False,
                },
                {"name": "Origem das chamadas", "value": source_text, "inline": False},
                {
                    "name": "Gasto real OAuth",
                    "value": f"{pt_usd(actual_cost_usd)} · assinatura incluída",
                    "inline": True,
                },
                {
                    "name": "Simulação pay-per-token",
                    "value": f"{pt_usd(hypothetical_usd)} · US$ 7/M entrada + US$ 21/M saída",
                    "inline": False,
                },
            ],
            "footer": {
                "text": (
                    f"Janela: {cutoff.strftime('%d/%m %H:%M %Z')} → {now.strftime('%d/%m %H:%M %Z')}"
                    f" · cobertura {coverage} · fonte: state.db/session_model_usage"
                )
            },
        }],
    }
    summary = {
        "total_calls": total_calls,
        "total_sessions": total_sessions,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "reasoning_tokens": reasoning_tokens,
        "actual_cost_usd": actual_cost_usd,
        "hypothetical_usd": hypothetical_usd,
        "config_ok": config_ok,
        "billing_ok": billing_ok,
        "telemetry_ok": not telemetry_errors,
        "telemetry_errors": telemetry_errors,
        "boundary_sessions": boundary_sessions,
        "coverage": coverage,
        "sources": dict(sorted(source_totals.items())),
        "unexpected_usage": sorted(unexpected_usage),
        "rows": rows,
        "cutoff": cutoff.isoformat(),
        "now": now.isoformat(),
    }
    return payload, summary


def post_discord(payload: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    channel_id = env.get("MGS_DISCORD_CHANNEL_ID_OVERRIDE", CHANNEL_ID_DEFAULT)
    token = env.get("MGS_DISCORD_BOT_TOKEN_OVERRIDE") or env.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN do Zeus ausente")
    url = env.get("MGS_DISCORD_API_URL_OVERRIDE") or f"https://discord.com/api/v10/channels/{channel_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MGS-GPT56-OAuth-Monitor/2.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            result = json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Discord HTTP {exc.code}: {detail}") from exc
    if not env.get("MGS_DISCORD_API_URL_OVERRIDE"):
        if str(result.get("channel_id")) != channel_id or not result.get("id"):
            raise RuntimeError("Discord respondeu sem message_id/channel_id esperado")
    return result


def parse_as_of(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--as-of", help="ISO timestamp usado para recuperação/auditoria da janela")
    args = parser.parse_args()
    env = dict(os.environ)
    load_env_file(Path("/root/.hermes/profiles/zeus/.env"), env)
    payload, summary = build_report(parse_as_of(args.as_of))
    if not summary["telemetry_ok"]:
        raise RuntimeError("telemetria incompleta: " + "; ".join(summary["telemetry_errors"]))
    if args.dry_run:
        print(
            "DRY-RUN: GPT-5.6 OAuth 24h | "
            f"calls={summary['total_calls']} sessions={summary['total_sessions']} "
            f"input={summary['input_tokens']} output={summary['output_tokens']} "
            f"cache_read={summary['cache_read_tokens']} actual_usd={summary['actual_cost_usd']:.2f} "
            f"hypothetical_usd={summary['hypothetical_usd']:.2f} "
            f"config_ok={summary['config_ok']} billing_ok={summary['billing_ok']} "
            f"coverage={summary['coverage']}"
        )
        for row in summary["rows"]:
            print(
                f"{row['profile']}: calls={row['api_calls']} sessions={row['sessions']} "
                f"input={row['input_tokens']} output={row['output_tokens']} "
                f"sources={json.dumps(row['sources'], sort_keys=True)} "
                f"model={row['model']} provider={row['provider']}"
            )
        return 0
    result = post_discord(payload, env)
    print(
        "Monitor GPT-5.6 OAuth enviado: "
        f"calls={summary['total_calls']} sessions={summary['total_sessions']} "
        f"input={summary['input_tokens']} output={summary['output_tokens']} "
        f"actual_usd={summary['actual_cost_usd']:.2f} "
        f"hypothetical_usd={summary['hypothetical_usd']:.2f} "
        f"config_ok={summary['config_ok']} billing_ok={summary['billing_ok']} "
        f"message_id={result.get('id', 'mock')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
