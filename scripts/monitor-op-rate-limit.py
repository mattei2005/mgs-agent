#!/usr/bin/env python3
"""Monitor 1Password Service Account rate limits and alert Discord.

Normal mode is silent while healthy. It alerts on warning/critical transitions,
resolution, or two consecutive probe failures. Discord delivery uses the Zeus
bot token, so an exhausted 1Password limit cannot block the alert itself.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

BASE_DIR = Path("/root/mgs-agent")
PROJECT_ENV = BASE_DIR / ".env"
ZEUS_ENV = Path("/root/.hermes/profiles/zeus/.env")
STATE_FILE = BASE_DIR / "data/op-rate-limit-monitor.json"
CHANNEL_ID = "1525311777208926398"
WARN_PERCENT = 50.0
CRITICAL_PERCENT = 90.0
MENTION = "<@344196393512075265>"

LEVEL_RANK = {"normal": 0, "warning": 1, "critical": 2}
LEVEL_COLOR = {"normal": 3066993, "warning": 15844367, "critical": 15158332, "info": 3447003}


def now_local() -> datetime:
    return datetime.now().astimezone()


def load_env_file(path: Path, target: dict[str, str]) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in target:
            target[key] = value


def load_runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    load_env_file(PROJECT_ENV, env)
    load_env_file(ZEUS_ENV, env)
    return env


def default_state() -> dict[str, Any]:
    return {
        "_meta": {
            "description": "Estado do monitor de rate limit do 1Password Service Account.",
            "channel_id": CHANNEL_ID,
            "warning_percent": WARN_PERCENT,
            "critical_percent": CRITICAL_PERCENT,
        },
        "last_check": None,
        "overall_level": "normal",
        "last_metrics": [],
        "consecutive_probe_failures": 0,
        "probe_failure_alerted": False,
        "last_error": None,
        "last_alert_sent": None,
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        base = default_state()
        base.update(data)
        return base
    except Exception:
        return default_state()


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(STATE_FILE)


def probe(env: dict[str, str]) -> list[dict[str, Any]]:
    if not env.get("OP_SERVICE_ACCOUNT_TOKEN"):
        raise RuntimeError("OP_SERVICE_ACCOUNT_TOKEN ausente")
    proc = subprocess.run(
        ["op", "service-account", "ratelimit", "--format=json"],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().replace("\n", " ")[:240]
        raise RuntimeError(f"op ratelimit falhou: {detail or 'erro sem detalhe'}")
    data = json.loads(proc.stdout)
    if not isinstance(data, list) or not data:
        raise RuntimeError("resposta vazia ou inválida do op ratelimit")
    return data


def metric_level(percent: float) -> str:
    if percent >= CRITICAL_PERCENT:
        return "critical"
    if percent >= WARN_PERCENT:
        return "warning"
    return "normal"


def normalize_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    current = now_local()
    for row in rows:
        limit = int(row.get("limit") or 0)
        used = int(row.get("used") or 0)
        remaining = int(row.get("remaining") or max(0, limit - used))
        reset_seconds = max(0, int(row.get("reset") or 0))
        percent = (used / limit * 100.0) if limit else 0.0
        reset_at = current + timedelta(seconds=reset_seconds) if reset_seconds else None
        metrics.append(
            {
                "type": str(row.get("type") or "unknown"),
                "action": str(row.get("action") or "unknown"),
                "used": used,
                "remaining": remaining,
                "limit": limit,
                "percent": round(percent, 2),
                "level": metric_level(percent),
                "reset_at": reset_at.isoformat() if reset_at else None,
            }
        )
    return metrics


def overall_level(metrics: list[dict[str, Any]]) -> str:
    return max((m["level"] for m in metrics), key=lambda level: LEVEL_RANK[level], default="normal")


def metric_label(metric: dict[str, Any]) -> str:
    if metric["type"] == "account":
        return "Conta Business — 24h"
    if metric["action"] == "read":
        return "Service Account — leitura/hora"
    if metric["action"] == "write":
        return "Service Account — escrita/hora"
    return f"{metric['type']} — {metric['action']}"


def metric_value(metric: dict[str, Any]) -> str:
    reset = metric.get("reset_at")
    reset_text = datetime.fromisoformat(reset).strftime("%d/%m %H:%M %Z") if reset else "sem janela ativa"
    return (
        f"{metric['used']:,}/{metric['limit']:,} usados ({metric['percent']:.2f}%)\n"
        f"Restantes: {metric['remaining']:,} · Reset: {reset_text}"
    ).replace(",", ".")


def discord_post(env: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    token = env.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN do Zeus ausente")
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MGS-OP-RateLimit-Monitor/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Discord HTTP {exc.code}: {detail}") from exc
    if str(result.get("channel_id")) != CHANNEL_ID or not result.get("id"):
        raise RuntimeError("Discord respondeu sem message_id/channel_id esperado")
    return result


def rate_payload(metrics: list[dict[str, Any]], level: str, resolved: bool = False, test: bool = False) -> dict[str, Any]:
    if test:
        title = "Monitor 1Password ativado"
        color = LEVEL_COLOR["info"]
        content = ""
        action = "Monitoramento ativo: primeiro aviso em 50% e alerta crítico em 90%."
    elif resolved:
        title = "Rate limit do 1Password normalizado"
        color = LEVEL_COLOR["normal"]
        content = ""
        action = "Uso voltou abaixo de 50%."
    elif level == "critical":
        title = "Rate limit do 1Password crítico"
        color = LEVEL_COLOR["critical"]
        content = f"{MENTION} rate limit do 1Password acima de 90%"
        action = "Suspender leituras não essenciais e investigar o processo consumidor."
    else:
        title = "Rate limit do 1Password em atenção"
        color = LEVEL_COLOR["warning"]
        content = ""
        action = "Uso acima de 50%. Acompanhar antes do próximo ciclo."

    fields = [
        {"name": metric_label(metric), "value": metric_value(metric), "inline": False}
        for metric in metrics
    ]
    fields.append({"name": "Ação", "value": action, "inline": False})
    return {"content": content, "embeds": [{"title": title, "color": color, "fields": fields}]}


def error_payload(error: str, resolved: bool = False) -> dict[str, Any]:
    if resolved:
        return {
            "content": "",
            "embeds": [{
                "title": "Monitor 1Password restabelecido",
                "color": LEVEL_COLOR["normal"],
                "fields": [{"name": "Estado", "value": "Consulta de rate limit voltou a funcionar.", "inline": False}],
            }],
        }
    return {
        "content": f"{MENTION} monitor do rate limit do 1Password falhou",
        "embeds": [{
            "title": "Falha no monitor 1Password",
            "color": LEVEL_COLOR["critical"],
            "fields": [
                {"name": "Falhas consecutivas", "value": "2 ou mais", "inline": True},
                {"name": "Detalhe", "value": error[:900], "inline": False},
                {"name": "Ação", "value": "Validar token, CLI e conectividade com 1Password.", "inline": False},
            ],
        }],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="consulta e imprime resumo sem gravar state ou enviar Discord")
    parser.add_argument("--send-test", action="store_true", help="envia mensagem informativa real ao canal configurado")
    args = parser.parse_args()

    env = load_runtime_env()
    state = load_state()
    timestamp = now_local().isoformat()

    try:
        rows = probe(env)
        metrics = normalize_metrics(rows)
        level = overall_level(metrics)
    except Exception as exc:
        error = str(exc)
        if args.dry_run:
            print(f"DRY-RUN FAIL: {error}")
            return 1
        state["last_check"] = timestamp
        state["consecutive_probe_failures"] = int(state.get("consecutive_probe_failures") or 0) + 1
        state["last_error"] = error
        if state["consecutive_probe_failures"] >= 2 and not state.get("probe_failure_alerted"):
            discord_post(env, error_payload(error))
            state["probe_failure_alerted"] = True
            state["last_alert_sent"] = timestamp
        save_state(state)
        print(f"FAIL probe_failures={state['consecutive_probe_failures']} detail={error[:180]}")
        return 1

    if args.dry_run:
        summary = " | ".join(f"{metric_label(m)}={m['used']}/{m['limit']} ({m['percent']:.2f}%)" for m in metrics)
        print(f"DRY-RUN OK level={level} | {summary}")
        return 0

    if args.send_test:
        result = discord_post(env, rate_payload(metrics, level, test=True))
        state["last_alert_sent"] = timestamp
        print(f"TEST_SENT channel={result['channel_id']} message={result['id']}")

    previous_level = str(state.get("overall_level") or "normal")
    error_was_alerted = bool(state.get("probe_failure_alerted"))
    sent_transition = False

    if error_was_alerted:
        discord_post(env, error_payload("", resolved=True))

    if not args.send_test:
        if LEVEL_RANK[level] >= LEVEL_RANK["warning"] and level != previous_level:
            discord_post(env, rate_payload(metrics, level))
            state["last_alert_sent"] = timestamp
            sent_transition = True
        elif level == "normal" and LEVEL_RANK.get(previous_level, 0) >= LEVEL_RANK["warning"]:
            discord_post(env, rate_payload(metrics, level, resolved=True))
            state["last_alert_sent"] = timestamp
            sent_transition = True

    state.update(
        {
            "last_check": timestamp,
            "overall_level": level,
            "last_metrics": metrics,
            "consecutive_probe_failures": 0,
            "probe_failure_alerted": False,
            "last_error": None,
        }
    )
    save_state(state)
    summary = " ".join(f"{m['type']}:{m['action']}={m['percent']:.2f}%" for m in metrics)
    print(f"OK level={level} transition_sent={str(sent_transition).lower()} {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
