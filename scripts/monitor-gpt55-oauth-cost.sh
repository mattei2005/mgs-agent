#!/usr/bin/env python3
"""Nightly real-volume report for GPT-5.6 OAuth usage across MGS agents.

Counts gateway-reported LLM API calls and completed responses in the trailing
24 hours. Hermes agent logs do not expose token counts, so this monitor never
invents token volume or hypothetical token cost. Actual incremental API cost is
reported as USD 0 because all monitored profiles use openai-codex OAuth.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROFILES = ("zeus", "atena", "ares", "hera")
PROFILES_ROOT = Path("/root/.hermes/profiles")
CHANNEL_ID_DEFAULT = "1498132022634483894"
RESPONSE_RE = re.compile(r"response ready:.*\bapi_calls=(\d+)")
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
EXPECTED_MODEL = "gpt-5.6-sol"
EXPECTED_PROVIDER = "openai-codex"


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
    model_match = re.search(r"^\s*default:\s*['\"]?([^'\"\s#]+)", text, re.MULTILINE)
    provider_match = re.search(r"^\s*provider:\s*['\"]?([^'\"\s#]+)", text, re.MULTILINE)
    return (
        model_match.group(1) if model_match else "unknown",
        provider_match.group(1) if provider_match else "unknown",
    )


def profile_usage(profile: str, cutoff: datetime, local_tz: Any) -> dict[str, Any]:
    path = PROFILES_ROOT / profile / "logs" / "agent.log"
    responses = 0
    api_calls = 0
    parse_errors = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = RESPONSE_RE.search(line)
            if not match:
                continue
            try:
                stamp = datetime.strptime(line[:23], TIMESTAMP_FORMAT).replace(tzinfo=local_tz)
            except ValueError:
                parse_errors += 1
                continue
            if stamp < cutoff:
                continue
            responses += 1
            api_calls += int(match.group(1))
    model, provider = profile_model(profile)
    return {
        "profile": profile,
        "responses": responses,
        "api_calls": api_calls,
        "average": round(api_calls / responses, 2) if responses else 0.0,
        "model": model,
        "provider": provider,
        "parse_errors": parse_errors,
    }


def build_report() -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now().astimezone()
    cutoff = now - timedelta(hours=24)
    rows = [profile_usage(profile, cutoff, now.tzinfo) for profile in PROFILES]
    total_responses = sum(row["responses"] for row in rows)
    total_calls = sum(row["api_calls"] for row in rows)
    total_parse_errors = sum(row["parse_errors"] for row in rows)
    average = round(total_calls / total_responses, 2) if total_responses else 0.0
    config_ok = all(
        row["model"] == EXPECTED_MODEL and row["provider"] == EXPECTED_PROVIDER
        for row in rows
    )
    content = "" if config_ok else "<@344196393512075265> divergência no modelo/provedor dos agentes"
    color = 3066993 if config_ok else 15844367
    status = "OK — todos em GPT-5.6 Sol via OAuth" if config_ok else "ATENÇÃO — configuração divergente"
    detail = "\n".join(
        f"**{row['profile'].title()}** — {row['api_calls']} chamadas | "
        f"{row['responses']} respostas | média {row['average']:.2f}"
        for row in rows
    )
    models = "\n".join(
        f"{row['profile'].title()}: `{row['model']}` / `{row['provider']}`"
        for row in rows
    )
    payload = {
        "content": content,
        "embeds": [{
            "title": "GPT-5.6 OAuth — volume real em 24h",
            "color": color,
            "fields": [
                {"name": "Status", "value": status, "inline": False},
                {"name": "Custo incremental real", "value": "US$ 0,00 — openai-codex OAuth", "inline": True},
                {"name": "Chamadas LLM", "value": str(total_calls), "inline": True},
                {"name": "Respostas concluídas", "value": str(total_responses), "inline": True},
                {"name": "Média por resposta", "value": f"{average:.2f} chamadas", "inline": True},
                {"name": "Por agente", "value": detail or "Sem atividade", "inline": False},
                {"name": "Modelo/provedor configurado", "value": models, "inline": False},
                {
                    "name": "Metodologia",
                    "value": (
                        "Soma `api_calls` das linhas `response ready` dos gateways nas últimas 24h. "
                        "Os logs não expõem tokens de entrada/saída; por isso o monitor não inventa "
                        "estimativa de tokens nem preço pay-per-token."
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Janela: {cutoff.strftime('%d/%m %H:%M %Z')} → {now.strftime('%d/%m %H:%M %Z')}"},
        }],
    }
    summary = {
        "total_calls": total_calls,
        "total_responses": total_responses,
        "average": average,
        "config_ok": config_ok,
        "parse_errors": total_parse_errors,
        "rows": rows,
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
            "User-Agent": "MGS-GPT56-OAuth-Monitor/1.0",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    env = dict(os.environ)
    load_env_file(Path("/root/.hermes/profiles/zeus/.env"), env)
    payload, summary = build_report()
    if args.dry_run:
        print(
            "DRY-RUN: GPT-5.6 OAuth 24h | "
            f"calls={summary['total_calls']} responses={summary['total_responses']} "
            f"avg={summary['average']:.2f} config_ok={summary['config_ok']} "
            f"parse_errors={summary['parse_errors']}"
        )
        for row in summary["rows"]:
            print(
                f"{row['profile']}: calls={row['api_calls']} responses={row['responses']} "
                f"avg={row['average']:.2f} model={row['model']} provider={row['provider']}"
            )
        return 0
    result = post_discord(payload, env)
    print(
        "Monitor GPT-5.6 OAuth enviado: "
        f"calls={summary['total_calls']} responses={summary['total_responses']} "
        f"config_ok={summary['config_ok']} message_id={result.get('id', 'mock')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
