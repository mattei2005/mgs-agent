#!/usr/bin/env python3
"""Monitor the SMS Funnel credit balance and alert a dedicated Discord channel.

Normal runs are silent while the balance is healthy. Alerts are sent on level
transitions, periodic reminders below a threshold, detected recharges, two
consecutive probe failures, and recovery from an alerted probe failure.
Credentials stay in 1Password; Discord delivery uses the Zeus bot token.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path("/root/mgs-agent")
PROJECT_ENV = BASE_DIR / ".env"
ZEUS_ENV = Path("/root/.hermes/profiles/zeus/.env")
DEFAULT_STATE_FILE = BASE_DIR / "data/sms-funnel-balance-state.json"
DEFAULT_CHANNEL_ID = "1527433742233374893"
ITEM_ID = "dtozo3kfqwoglwkmblfsvautyq"
VAULT = "MGS Conteúdo"
LOGIN_URL = "https://web2.smsfunnel.com.br/api/login"
CREDITS_URL = "https://web2.smsfunnel.com.br/api/user-credits-info"
DISCORD_API_BASE = "https://discord.com/api/v10"
MENTION_USER_ID = "344196393512075265"

THRESHOLDS = {
    "warning": 20_000,
    "critical": 10_000,
    "emergency": 5_000,
}
LEVEL_RANK = {"normal": 0, "warning": 1, "critical": 2, "emergency": 3}
LEVEL_COLOR = {
    "normal": 3_066_993,
    "warning": 15_844_367,
    "critical": 15_158_332,
    "emergency": 15_158_332,
    "info": 3_447_003,
}
REMINDER_SECONDS = {
    "warning": 24 * 3600,
    "critical": 12 * 3600,
    "emergency": 4 * 3600,
}


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


def runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    load_env_file(PROJECT_ENV, env)
    load_env_file(ZEUS_ENV, env)
    return env


def default_state(channel_id: str) -> dict[str, Any]:
    return {
        "_meta": {
            "description": "Estado do monitor de saldo SMS Funnel.",
            "channel_id": channel_id,
            "warning_credits": THRESHOLDS["warning"],
            "critical_credits": THRESHOLDS["critical"],
            "emergency_credits": THRESHOLDS["emergency"],
            "schedule": "24 * * * *",
        },
        "last_check": None,
        "level": "normal",
        "last_metrics": {},
        "samples": [],
        "last_alert_sent": None,
        "last_alert_level": None,
        "last_reminder_sent": None,
        "last_discord_message_id": None,
        "consecutive_probe_failures": 0,
        "probe_failure_alerted": False,
        "last_error": None,
    }


def load_state(path: Path, channel_id: str) -> dict[str, Any]:
    base = default_state(channel_id)
    if not path.exists():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        base.update(data)
        base["_meta"] = default_state(channel_id)["_meta"]
        return base
    except Exception:
        return base


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
              headers: dict[str, str] | None = None, timeout: int = 20) -> tuple[int, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "MGS-SMSFunnel-Balance-Monitor/1.0",
    }
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:240].replace("\n", " ")
        raise RuntimeError(f"HTTP {exc.code} em {url.split('?')[0]}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"falha de rede em {url.split('?')[0]}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON inválido em {url.split('?')[0]}") from exc


def read_credential(env: dict[str, str]) -> tuple[str, str]:
    if not env.get("OP_SERVICE_ACCOUNT_TOKEN"):
        raise RuntimeError("OP_SERVICE_ACCOUNT_TOKEN ausente")
    proc = subprocess.run(
        ["op", "item", "get", ITEM_ID, "--vault", VAULT, "--format", "json"],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().replace("\n", " ")[:180]
        raise RuntimeError(f"1Password indisponível: {detail or 'erro sem detalhe'}")
    try:
        item = json.loads(proc.stdout)
        fields = {field.get("id"): field.get("value", "") for field in item.get("fields", [])}
        username = str(fields.get("username") or "")
        password = str(fields.get("password") or "")
    except Exception as exc:
        raise RuntimeError("resposta inválida do 1Password") from exc
    if not username or not password:
        raise RuntimeError("campos de login ausentes no item do 1Password")
    return username, password


def validate_metrics(data: Any) -> dict[str, int]:
    if not isinstance(data, dict):
        raise RuntimeError("resposta de créditos não é um objeto")
    keys = ["total_contracted", "total_sent", "total_reserved", "credits", "total_calculated_broadcasts"]
    metrics: dict[str, int] = {}
    for key in keys:
        value = data.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"campo numérico inválido: {key}")
        metrics[key] = int(value)
    if any(metrics[key] < 0 for key in ["total_contracted", "total_sent", "total_reserved", "credits"]):
        raise RuntimeError("métrica de créditos negativa")
    metrics["accounting_gap"] = (
        metrics["total_contracted"]
        - metrics["total_sent"]
        - metrics["total_reserved"]
        - metrics["credits"]
    )
    return metrics


def probe_live(env: dict[str, str]) -> dict[str, int]:
    username, password = read_credential(env)
    status, login = http_json(LOGIN_URL, method="POST", payload={"email": username, "password": password})
    if status != 200 or not isinstance(login, dict):
        raise RuntimeError(f"login SMS Funnel falhou com HTTP {status}")
    token = str(login.get("access_token") or "")
    if not token:
        raise RuntimeError("login SMS Funnel sem access_token")
    status, credits = http_json(CREDITS_URL, headers={"Authorization": f"Bearer {token}"})
    if status != 200:
        raise RuntimeError(f"consulta de créditos falhou com HTTP {status}")
    return validate_metrics(credits)


def probe_fixture(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(str(data["error"]))
    return validate_metrics(data)


def balance_level(credits: int) -> str:
    if credits <= THRESHOLDS["emergency"]:
        return "emergency"
    if credits <= THRESHOLDS["critical"]:
        return "critical"
    if credits <= THRESHOLDS["warning"]:
        return "warning"
    return "normal"


def fmt_int(value: int | float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def append_sample(state: dict[str, Any], metrics: dict[str, int], now_epoch: int) -> None:
    samples = [sample for sample in state.get("samples", []) if isinstance(sample, dict)]
    samples.append({
        "ts": now_epoch,
        "credits": metrics["credits"],
        "total_sent": metrics["total_sent"],
        "total_contracted": metrics["total_contracted"],
    })
    cutoff = now_epoch - 7 * 86400
    state["samples"] = [sample for sample in samples if int(sample.get("ts", 0)) >= cutoff][-200:]


def burn_projection(state: dict[str, Any], metrics: dict[str, int], now_epoch: int) -> dict[str, Any]:
    samples = [sample for sample in state.get("samples", []) if isinstance(sample, dict)]
    candidates = [sample for sample in samples if now_epoch - int(sample.get("ts", 0)) <= 30 * 3600]
    if len(candidates) < 2:
        return {"daily_sent": None, "hours_left": None, "window_hours": 0.0}
    oldest = min(candidates, key=lambda sample: int(sample.get("ts", 0)))
    elapsed = now_epoch - int(oldest.get("ts", now_epoch))
    delta = metrics["total_sent"] - int(oldest.get("total_sent", metrics["total_sent"]))
    if elapsed < 3600 or delta <= 0:
        return {"daily_sent": None, "hours_left": None, "window_hours": round(elapsed / 3600, 1)}
    per_hour = delta / (elapsed / 3600)
    return {
        "daily_sent": round(per_hour * 24),
        "hours_left": round(metrics["credits"] / per_hour, 1) if per_hour > 0 else None,
        "window_hours": round(elapsed / 3600, 1),
    }


def projection_text(projection: dict[str, Any]) -> str:
    daily = projection.get("daily_sent")
    hours = projection.get("hours_left")
    if daily is None or hours is None:
        return "Calculando após acumular pelo menos 1 hora de histórico."
    if hours >= 48:
        remaining = f"aprox. {hours / 24:.1f} dias"
    else:
        remaining = f"aprox. {hours:.1f} horas"
    return f"Ritmo projetado: {fmt_int(daily)} SMS/dia · duração estimada do saldo: {remaining}."


def metric_fields(metrics: dict[str, int], projection: dict[str, Any]) -> list[dict[str, Any]]:
    usage_pct = (metrics["total_sent"] / metrics["total_contracted"] * 100.0) if metrics["total_contracted"] else 0.0
    fields = [
        {"name": "Saldo disponível", "value": f"**{fmt_int(metrics['credits'])} SMS**", "inline": True},
        {"name": "Créditos contratados", "value": fmt_int(metrics["total_contracted"]), "inline": True},
        {"name": "Créditos utilizados", "value": f"{fmt_int(metrics['total_sent'])} ({usage_pct:.2f}%)", "inline": True},
        {"name": "Consumo e projeção", "value": projection_text(projection), "inline": False},
        {
            "name": "Faixas de alerta",
            "value": "Atenção ≤ 20.000 · Crítico ≤ 10.000 · Emergência ≤ 5.000",
            "inline": False,
        },
    ]
    if metrics.get("accounting_gap"):
        fields.append({
            "name": "Conciliação",
            "value": f"Diferença contábil observada: {fmt_int(metrics['accounting_gap'])} créditos.",
            "inline": False,
        })
    return fields


def alert_payload(level: str, metrics: dict[str, int], projection: dict[str, Any], *, reminder: bool = False) -> dict[str, Any]:
    titles = {
        "warning": "Saldo SMS Funnel em atenção",
        "critical": "Saldo SMS Funnel crítico",
        "emergency": "Saldo SMS Funnel em emergência",
    }
    actions = {
        "warning": "Programar a próxima recarga via PIX antes de o saldo entrar na faixa crítica.",
        "critical": "Solicitar a recarga via PIX agora para evitar interrupção dos SMS.",
        "emergency": "Recarga imediata necessária; há risco próximo de interrupção dos SMS.",
    }
    mention = level in {"critical", "emergency"}
    title = titles[level] + (" — lembrete" if reminder else "")
    fields = metric_fields(metrics, projection)
    fields.append({"name": "Ação", "value": actions[level], "inline": False})
    return {
        "content": f"<@{MENTION_USER_ID}> saldo SMS Funnel baixo" if mention else "",
        "allowed_mentions": {"users": [MENTION_USER_ID]} if mention else {"parse": []},
        "embeds": [{"title": title, "color": LEVEL_COLOR[level], "fields": fields}],
    }


def activation_payload(metrics: dict[str, int], projection: dict[str, Any]) -> dict[str, Any]:
    fields = metric_fields(metrics, projection)
    fields.append({
        "name": "Comportamento",
        "value": "Consulta a cada hora. Silêncio enquanto saudável; alerta por faixa, lembrete anti-spam, confirmação de recarga e aviso após duas falhas consecutivas.",
        "inline": False,
    })
    return {
        "content": "",
        "allowed_mentions": {"parse": []},
        "embeds": [{"title": "Monitor de saldo SMS Funnel ativado", "color": LEVEL_COLOR["info"], "fields": fields}],
    }


def recharge_payload(previous: dict[str, Any], metrics: dict[str, int], projection: dict[str, Any]) -> dict[str, Any]:
    before = int(previous.get("credits", 0) or 0)
    delta = metrics["credits"] - before
    fields = metric_fields(metrics, projection)
    fields.insert(1, {"name": "Variação detectada", "value": f"{fmt_int(before)} → {fmt_int(metrics['credits'])} (**+{fmt_int(delta)}**)", "inline": False})
    return {
        "content": "",
        "allowed_mentions": {"parse": []},
        "embeds": [{"title": "Recarga SMS Funnel detectada", "color": LEVEL_COLOR["normal"], "fields": fields}],
    }


def recovery_payload(metrics: dict[str, int], projection: dict[str, Any], previous_level: str) -> dict[str, Any]:
    fields = metric_fields(metrics, projection)
    fields.append({"name": "Estado", "value": f"Saldo saiu da faixa {previous_level}.", "inline": False})
    return {
        "content": "",
        "allowed_mentions": {"parse": []},
        "embeds": [{"title": "Saldo SMS Funnel normalizado", "color": LEVEL_COLOR["normal"], "fields": fields}],
    }


def probe_error_payload(error: str, *, resolved: bool = False) -> dict[str, Any]:
    if resolved:
        return {
            "content": "",
            "allowed_mentions": {"parse": []},
            "embeds": [{
                "title": "Monitor SMS Funnel restabelecido",
                "color": LEVEL_COLOR["normal"],
                "fields": [{"name": "Estado", "value": "A consulta do saldo voltou a funcionar.", "inline": False}],
            }],
        }
    return {
        "content": f"<@{MENTION_USER_ID}> monitor SMS Funnel sem leitura",
        "allowed_mentions": {"users": [MENTION_USER_ID]},
        "embeds": [{
            "title": "Falha no monitor SMS Funnel",
            "color": LEVEL_COLOR["critical"],
            "fields": [
                {"name": "Falhas consecutivas", "value": "2 ou mais", "inline": True},
                {"name": "Detalhe", "value": error[:900], "inline": False},
                {"name": "Ação", "value": "Validar acesso ao dashboard, 1Password e conectividade da API.", "inline": False},
            ],
        }],
    }


def discord_post(env: dict[str, str], channel_id: str, payload: dict[str, Any], api_base: str) -> dict[str, Any]:
    token = env.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN do Zeus ausente")
    status, result = http_json(
        f"{api_base.rstrip('/')}/channels/{channel_id}/messages",
        method="POST",
        payload=payload,
        headers={"Authorization": f"Bot {token}"},
        timeout=15,
    )
    if status < 200 or status >= 300 or not isinstance(result, dict):
        raise RuntimeError(f"Discord respondeu HTTP {status}")
    if str(result.get("channel_id")) != channel_id or not result.get("id"):
        raise RuntimeError("Discord respondeu sem message_id/channel_id esperado")
    return result


def iso_to_epoch(value: Any) -> int:
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(str(value)).timestamp())
    except Exception:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="consulta sem gravar state nem enviar Discord")
    parser.add_argument("--send-test", action="store_true", help="envia o embed informativo de ativação")
    parser.add_argument("--fixture", type=Path, help="usa métricas JSON locais em vez da API/1Password")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    parser.add_argument("--discord-api-base", default=DISCORD_API_BASE)
    args = parser.parse_args()

    env = runtime_env()
    state = load_state(args.state_file, args.channel_id)
    current = now_local()
    now_epoch = int(current.timestamp())
    timestamp = current.isoformat()

    try:
        metrics = probe_fixture(args.fixture) if args.fixture else probe_live(env)
        level = balance_level(metrics["credits"])
    except Exception as exc:
        error = str(exc)
        if args.dry_run:
            print(f"DRY-RUN FAIL: {error}")
            return 1
        state["last_check"] = timestamp
        state["consecutive_probe_failures"] = int(state.get("consecutive_probe_failures") or 0) + 1
        state["last_error"] = error
        if state["consecutive_probe_failures"] >= 2 and not state.get("probe_failure_alerted"):
            try:
                result = discord_post(env, args.channel_id, probe_error_payload(error), args.discord_api_base)
            except Exception as send_exc:
                state["last_discord_error"] = str(send_exc)[:300]
                save_state(args.state_file, state)
                print(f"FAIL probe_failures={state['consecutive_probe_failures']} alert_delivery=failed")
                return 1
            state["probe_failure_alerted"] = True
            state["last_alert_sent"] = timestamp
            state["last_discord_message_id"] = result["id"]
            state.pop("last_discord_error", None)
        save_state(args.state_file, state)
        print(f"FAIL probe_failures={state['consecutive_probe_failures']} detail={error[:160]}")
        return 1

    raw_previous_metrics = state.get("last_metrics")
    previous_metrics: dict[str, Any] = raw_previous_metrics if isinstance(raw_previous_metrics, dict) else {}
    previous_level = str(state.get("level") or "normal")
    error_was_alerted = bool(state.get("probe_failure_alerted"))
    append_sample(state, metrics, now_epoch)
    projection = burn_projection(state, metrics, now_epoch)

    if args.dry_run:
        print(
            "DRY-RUN OK "
            f"level={level} credits={metrics['credits']} sent={metrics['total_sent']} "
            f"contracted={metrics['total_contracted']} daily={projection.get('daily_sent')} "
            f"accounting_gap={metrics.get('accounting_gap')}"
        )
        return 0

    sent_kind = "none"
    result: dict[str, Any] | None = None
    try:
        if args.send_test:
            result = discord_post(env, args.channel_id, activation_payload(metrics, projection), args.discord_api_base)
            sent_kind = "activation"
        elif error_was_alerted:
            result = discord_post(env, args.channel_id, probe_error_payload("", resolved=True), args.discord_api_base)
            sent_kind = "probe_recovery"

        recharge_delta = metrics["credits"] - int(previous_metrics.get("credits", metrics["credits"]) or metrics["credits"])
        contracted_increased = metrics["total_contracted"] > int(previous_metrics.get("total_contracted", metrics["total_contracted"]) or metrics["total_contracted"])
        recharge_detected = bool(previous_metrics) and (contracted_increased or recharge_delta >= 100)

        if not args.send_test:
            if recharge_detected:
                result = discord_post(env, args.channel_id, recharge_payload(previous_metrics, metrics, projection), args.discord_api_base)
                sent_kind = "recharge"
            elif LEVEL_RANK[level] > LEVEL_RANK.get(previous_level, 0):
                result = discord_post(env, args.channel_id, alert_payload(level, metrics, projection), args.discord_api_base)
                sent_kind = "threshold"
            elif LEVEL_RANK[level] < LEVEL_RANK.get(previous_level, 0) and LEVEL_RANK.get(previous_level, 0) > 0:
                result = discord_post(env, args.channel_id, recovery_payload(metrics, projection, previous_level), args.discord_api_base)
                sent_kind = "balance_recovery"
            elif level != "normal":
                last_reminder_epoch = iso_to_epoch(state.get("last_reminder_sent"))
                if now_epoch - last_reminder_epoch >= REMINDER_SECONDS[level]:
                    result = discord_post(env, args.channel_id, alert_payload(level, metrics, projection, reminder=True), args.discord_api_base)
                    sent_kind = "reminder"
    except Exception as exc:
        state["last_check"] = timestamp
        state["last_discord_error"] = str(exc)[:300]
        save_state(args.state_file, state)
        print(f"FAIL discord_delivery={type(exc).__name__}")
        return 1

    state.update({
        "last_check": timestamp,
        "level": level,
        "last_metrics": metrics,
        "consecutive_probe_failures": 0,
        "probe_failure_alerted": False,
        "last_error": None,
    })
    state.pop("last_discord_error", None)
    if result is not None:
        state["last_alert_sent"] = timestamp
        state["last_alert_level"] = level
        state["last_discord_message_id"] = result["id"]
        if sent_kind in {"threshold", "reminder"}:
            state["last_reminder_sent"] = timestamp
    save_state(args.state_file, state)
    print(
        f"OK level={level} credits={metrics['credits']} sent={metrics['total_sent']} "
        f"notification={sent_kind} message_id={result.get('id') if result else 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
