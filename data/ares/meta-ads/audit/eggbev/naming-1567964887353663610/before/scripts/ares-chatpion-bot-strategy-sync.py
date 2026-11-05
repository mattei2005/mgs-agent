#!/usr/bin/env python3
"""Validate and project ChatPion BOT strategy changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAMILY_PATH = ROOT / "data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json"
CONSUMERS_PATH = ROOT / "data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json"
VERSIONED_CONFIG = ROOT / "profiles/ares-config.yaml"
PROFILE_ENV = Path("/root/.hermes/profiles/ares/.env")
API = "https://discord.com/api/v10"
ARES_BOT_ID = "1508864261504630925"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_token() -> str:
    for raw in PROFILE_ENV.read_text(errors="ignore").splitlines():
        if raw.startswith("DISCORD_BOT_TOKEN="):
            value = raw.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("Ares Discord token unavailable")


def request(token: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in range(4):
        req = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bot " + token,
                "Content-Type": "application/json",
                "User-Agent": "MGS-Ares-ChatPion-Strategy-Sync/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode(errors="ignore")
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="ignore")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {}
            if exc.code == 429 and attempt < 3:
                delay = max(0.5, min(float(parsed.get("retry_after", 1.0)), 30.0))
                time.sleep(delay + 0.25)
                continue
            return exc.code, {"code": parsed.get("code"), "message": parsed.get("message")}
    return 429, {"message": "rate_limit_retry_exhausted"}


def selected_consumers(registry: dict[str, Any], scope: str, operation: str | None) -> dict[str, dict[str, Any]]:
    active = {key: value for key, value in registry["consumers"].items() if value.get("status") == "active"}
    if scope == "family":
        return active
    if not operation or operation not in active:
        raise RuntimeError("--operation must identify one active consumer for operation scope")
    return {operation: active[operation]}


def route_set(requested: list[str]) -> list[str]:
    routes = list(dict.fromkeys(requested or ["rules"]))
    if any(route != "rules" for route in routes) and "rules" not in routes:
        routes.append("rules")
    return routes


def validate_consumer(family: dict[str, Any], registry: dict[str, Any], operation_id: str, consumer: dict[str, Any], routes: list[str]) -> dict[str, Any]:
    operation_path = ROOT / consumer["operation_contract"]
    route_registry_path = ROOT / consumer["route_registry"]
    operation = load_json(operation_path)
    route_registry = load_json(route_registry_path)
    binding = operation.get("strategy_binding") or {}
    checks: dict[str, bool] = {
        "family_active": family.get("status") == "active",
        "family_skill": family.get("skill") == registry.get("required_skill"),
        "operation_identity": operation.get("operation_id") == operation_id,
        "operation_family": operation.get("strategy_family") == family.get("family_id"),
        "binding_family": binding.get("family_id") == family.get("family_id"),
        "binding_contract": binding.get("family_contract") == str(FAMILY_PATH.relative_to(ROOT)),
        "operation_skill": operation.get("operation_skill") == registry.get("required_skill"),
    }
    route_checks: dict[str, Any] = {}
    operation_routes = operation.get("discord", {}).get("route_contracts", {})
    aliases = {"page_guardrails": "page_lead_guardrail"}
    for route in routes:
        op_route = aliases.get(route, route)
        expected_id = str(consumer["routes"][route])
        registered = route_registry["routes"][op_route]
        contract = operation_routes[op_route]
        prompt_path = ROOT / registered["prompt_file"]
        route_checks[route] = {
            "thread_match": str(registered["thread_id"]) == expected_id == str(contract["thread_id"]),
            "skill_match": registered.get("required_skill") == registry.get("required_skill") == contract.get("required_skill"),
            "prompt_exists": prompt_path.is_file() and bool(prompt_path.read_text(encoding="utf-8").strip()),
        }
    ok = all(checks.values()) and all(all(row.values()) for row in route_checks.values())
    return {"ok": ok, "checks": checks, "routes": route_checks}


def find_yaml_value(root: yaml.Node, path: list[str]) -> tuple[yaml.Node, yaml.Node]:
    node = root
    key_node: yaml.Node | None = None
    for segment in path:
        if not isinstance(node, yaml.MappingNode):
            raise KeyError(".".join(path))
        pair = next(((key, value) for key, value in node.value if key.value == segment), None)
        if pair is None:
            raise KeyError(".".join(path))
        key_node, node = pair
    assert key_node is not None
    return key_node, node


def serialize_scalar(value: str, key_column: int) -> str:
    dumped = yaml.safe_dump({"value": value}, allow_unicode=True, sort_keys=False, width=100)
    if not dumped.startswith("value: "):
        raise RuntimeError("unexpected YAML scalar serialization")
    scalar = dumped[len("value: "):].rstrip("\n")
    lines = scalar.splitlines()
    return lines[0] + ("\n" + "\n".join((" " * key_column) + line for line in lines[1:]) if len(lines) > 1 else "")


def set_versioned_prompt(thread_id: str, prompt: str) -> None:
    raw = VERSIONED_CONFIG.read_text(encoding="utf-8")
    document = yaml.compose(raw)
    if document is None:
        raise RuntimeError("versioned config is empty")
    key, value = find_yaml_value(document, ["discord", "channel_prompts", thread_id])
    replacement = serialize_scalar(prompt, key.start_mark.column)
    updated = raw[: value.start_mark.index] + replacement + raw[value.end_mark.index :]
    parsed = yaml.safe_load(updated)
    if str(parsed["discord"]["channel_prompts"][thread_id]).strip() != prompt.strip():
        raise RuntimeError(f"versioned prompt readback mismatch for {thread_id}")
    VERSIONED_CONFIG.write_text(updated, encoding="utf-8")


def sync_prompt(thread_id: str, prompt_path: Path) -> dict[str, Any]:
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    set_versioned_prompt(thread_id, prompt)
    subprocess.run(
        ["hermes", "-p", "ares", "config", "set", f"discord.channel_prompts.{thread_id}", prompt],
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = subprocess.run(
        ["hermes", "-p", "ares", "config", "get", f"discord.channel_prompts.{thread_id}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    versioned = yaml.safe_load(VERSIONED_CONFIG.read_text(encoding="utf-8"))["discord"]["channel_prompts"][thread_id].strip()
    return {
        "thread_id": thread_id,
        "source_equals_versioned": prompt == versioned,
        "source_equals_runtime": prompt == resolved,
        "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }


def publish_projection(token: str, registry: dict[str, Any], operation_id: str, consumer: dict[str, Any], route: str, content: str) -> dict[str, Any]:
    if len(content) > 2000:
        raise RuntimeError("projection exceeds Discord 2000-character limit")
    thread_id = str(consumer["routes"][route])
    message_id = str(consumer.setdefault("projection_messages", {}).get(route) or "")
    action = "none"
    if message_id:
        status, current = request(token, "GET", f"/channels/{thread_id}/messages/{message_id}")
        if status != 200 or not isinstance(current, dict):
            raise RuntimeError(f"persisted projection unavailable: {operation_id}/{route} HTTP {status}")
        if str((current.get("author") or {}).get("id")) != ARES_BOT_ID:
            raise RuntimeError("persisted projection is not owned by Ares")
        if current.get("content") != content:
            status, _ = request(token, "PATCH", f"/channels/{thread_id}/messages/{message_id}", {"content": content})
            if status != 200:
                raise RuntimeError(f"projection PATCH failed HTTP {status}")
            action = "edited"
    else:
        recent_status, recent = request(token, "GET", f"/channels/{thread_id}/messages?limit=100")
        matching = []
        if recent_status == 200 and isinstance(recent, list):
            matching = [
                row for row in recent
                if row.get("content") == content and str((row.get("author") or {}).get("id")) == ARES_BOT_ID
            ]
        if len(matching) > 1:
            raise RuntimeError(f"duplicate exact projections require reconciliation: {operation_id}/{route}")
        if matching:
            message_id = str(matching[0]["id"])
            consumer["projection_messages"][route] = message_id
            atomic_json(CONSUMERS_PATH, registry)
            action = "reconciled_existing"
        else:
            status, created = request(token, "POST", f"/channels/{thread_id}/messages", {"content": content})
            if status != 200 or not isinstance(created, dict) or not created.get("id"):
                # Reconcile a possible accepted write after a lost response.
                recent_status, recent = request(token, "GET", f"/channels/{thread_id}/messages?limit=100")
                matching = [
                    row for row in (recent if recent_status == 200 and isinstance(recent, list) else [])
                    if row.get("content") == content and str((row.get("author") or {}).get("id")) == ARES_BOT_ID
                ]
                if len(matching) != 1:
                    raise RuntimeError(f"projection POST unresolved HTTP {status}")
                created = matching[0]
                action = "reconciled_after_post_response_loss"
            else:
                action = "created"
            message_id = str(created["id"])
            consumer["projection_messages"][route] = message_id
            atomic_json(CONSUMERS_PATH, registry)
    status, after = request(token, "GET", f"/channels/{thread_id}/messages/{message_id}")
    ok = status == 200 and isinstance(after, dict) and after.get("content") == content and str((after.get("author") or {}).get("id")) == ARES_BOT_ID
    return {
        "operation_id": operation_id,
        "route": route,
        "thread_id": thread_id,
        "message_id": message_id,
        "action": action,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "readback_ok": ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["family", "operation"], default="operation")
    parser.add_argument("--operation")
    parser.add_argument("--route", action="append", choices=["rules", "campaign_creation", "campaign_cloning", "roas_cycle", "daily_reporting", "page_guardrails"])
    parser.add_argument("--sync-prompts", action="store_true")
    parser.add_argument("--publish-discord", action="store_true")
    parser.add_argument("--message-file", type=Path)
    parser.add_argument("--change-id")
    parser.add_argument("--source-thread")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    family = load_json(FAMILY_PATH)
    registry = load_json(CONSUMERS_PATH)
    consumers = selected_consumers(registry, args.scope, args.operation)
    routes = route_set(args.route or [])
    validations = {key: validate_consumer(family, registry, key, value, routes) for key, value in consumers.items()}
    if not all(row["ok"] for row in validations.values()):
        payload = {"ok": False, "stage": "validation", "validations": validations}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    prompt_sync: list[dict[str, Any]] = []
    if args.sync_prompts:
        aliases = {"page_guardrails": "page_lead_guardrail"}
        for operation_id, consumer in consumers.items():
            route_registry = load_json(ROOT / consumer["route_registry"])
            for route in routes:
                registered = route_registry["routes"][aliases.get(route, route)]
                prompt_sync.append(sync_prompt(str(consumer["routes"][route]), ROOT / registered["prompt_file"]))

    projections: list[dict[str, Any]] = []
    if args.publish_discord:
        if not args.message_file or not args.change_id:
            raise RuntimeError("--publish-discord requires --message-file and --change-id")
        body = args.message_file.read_text(encoding="utf-8").strip()
        token = load_token()
        for operation_id, consumer in consumers.items():
            for route in routes:
                content = f"🔄 **ATUALIZAÇÃO CANÔNICA — {args.change_id}**\n\n{body}\n\nEscopo: `{operation_id}` • Rota: `{route}`"
                projections.append(publish_projection(token, registry, operation_id, consumer, route, content))
        atomic_json(CONSUMERS_PATH, registry)

    payload = {
        "ok": all(row["ok"] for row in validations.values())
        and all(row["source_equals_versioned"] and row["source_equals_runtime"] for row in prompt_sync)
        and all(row["readback_ok"] for row in projections),
        "scope": args.scope,
        "operations": list(consumers),
        "routes": routes,
        "validations": validations,
        "prompt_sync": prompt_sync,
        "projections": projections,
        "source_thread": args.source_thread,
    }
    if args.output:
        atomic_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
