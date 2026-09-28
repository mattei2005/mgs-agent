#!/usr/bin/env python3
"""Fail-closed MGS domain scope gate for shared Ares/Atena operations."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path("/root/mgs-agent")
DEFAULT_REGISTRY = BASE / "data/mgs-domain-scope.json"
VALID_AGENTS = {"ares", "atena"}
HOST_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


class ScopeError(ValueError):
    pass


def registry_path(cli_value: str | None = None) -> Path:
    return Path(
        cli_value
        or os.environ.get("MGS_DOMAIN_SCOPE_REGISTRY")
        or DEFAULT_REGISTRY
    )


def normalize_target(value: str) -> str:
    raw = str(value or "").strip()
    if not raw or len(raw) > 2048 or any(ord(ch) < 32 for ch in raw):
        raise ScopeError("invalid target")
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    if parsed.username is not None or parsed.password is not None:
        raise ScopeError("credentials in target are not accepted")
    try:
        host = (parsed.hostname or "").rstrip(".").lower().encode("idna").decode("ascii")
        _ = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise ScopeError("invalid host") from exc
    if not host or not HOST_RE.fullmatch(host):
        raise ScopeError("invalid host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ScopeError("IP targets are outside the domain registry")
    return host


def load_registry(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeError("domain registry unavailable") from exc
    validate_registry(data, path)
    return data


def validate_registry(data: dict, path: Path) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ScopeError("unsupported registry schema")
    if data.get("classification") != "shareable_mgs_domains_only":
        raise ScopeError("invalid registry classification")
    consumers = data.get("consumers")
    if not isinstance(consumers, list) or set(consumers) != VALID_AGENTS:
        raise ScopeError("registry consumers must be exactly Ares and Atena")
    policy = data.get("policy")
    required_policy = {
        "default": "deny",
        "exact_host_match": True,
        "allow_www_alias": True,
        "allow_implicit_subdomains": False,
        "store_non_mgs_domains": False,
    }
    if not isinstance(policy, dict) or any(policy.get(k) != v for k, v in required_policy.items()):
        raise ScopeError("registry is not fail-closed")
    deny_response = policy.get("deny_response")
    if not isinstance(deny_response, str) or not deny_response.strip():
        raise ScopeError("deny response missing")
    domains = data.get("domains")
    if not isinstance(domains, list) or not domains:
        raise ScopeError("domain allowlist is empty")
    if domains != sorted(domains) or len(domains) != len(set(domains)):
        raise ScopeError("domains must be unique and sorted")
    for domain in domains:
        if not isinstance(domain, str) or normalize_target(domain) != domain or domain.startswith("www."):
            raise ScopeError("registry contains a non-canonical domain")
    sources = data.get("canonical_sources")
    if not isinstance(sources, list) or not sources:
        raise ScopeError("canonical sources missing")
    ownership_source = data.get("ownership_source")
    if not isinstance(ownership_source, str) or ownership_source not in sources:
        raise ScopeError("ownership source missing")
    if path.resolve() == DEFAULT_REGISTRY.resolve():
        missing = [source for source in sources if not (BASE / source).is_file()]
        if missing:
            raise ScopeError("canonical source missing")
        try:
            ownership_text = (BASE / ownership_source).read_text(encoding="utf-8").lower()
        except OSError as exc:
            raise ScopeError("ownership source unavailable") from exc
        uncovered = [
            domain
            for domain in domains
            if not re.search(
                rf"(?<![a-z0-9.-]){re.escape(domain)}(?![a-z0-9.-])",
                ownership_text,
            )
        ]
        if uncovered:
            raise ScopeError("domain lacks affirmative ownership source")


def allowed_domain(target: str, data: dict) -> str | None:
    try:
        host = normalize_target(target)
    except ScopeError:
        return None
    allowed = set(data["domains"])
    if host in allowed:
        return host
    if data["policy"].get("allow_www_alias") and host.startswith("www.") and host[4:] in allowed:
        return host[4:]
    return None


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if payload.get("allowed") is True:
        print(f"ALLOWED: {payload['domain']}")
    elif isinstance(payload.get("domains"), list):
        print("\n".join(payload["domains"]))
    elif "allowed_domains" in payload:
        print("\n".join(payload["allowed_domains"]))
        if payload.get("blocked_count"):
            print(payload["message"])
    else:
        print(payload.get("message", "OK"))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--registry", help="Override registry path (tests only).")
    commands = root.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--json", action="store_true")

    list_cmd = commands.add_parser("list")
    list_cmd.add_argument("--agent", required=True, choices=sorted(VALID_AGENTS))
    list_cmd.add_argument("--json", action="store_true")

    check = commands.add_parser("check")
    check.add_argument("--agent", required=True, choices=sorted(VALID_AGENTS))
    check.add_argument("target")
    check.add_argument("--json", action="store_true")

    filter_cmd = commands.add_parser("filter")
    filter_cmd.add_argument("--agent", required=True, choices=sorted(VALID_AGENTS))
    filter_cmd.add_argument("targets", nargs="+")
    filter_cmd.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        path = registry_path(args.registry)
        data = load_registry(path)
    except ScopeError:
        print("MGS domain scope is unavailable; operation denied.")
        return 4

    if args.command == "validate":
        emit({"status": "ok", "domains": len(data["domains"])}, args.json)
        return 0

    if args.agent not in data["consumers"]:
        print("MGS domain scope is unavailable; operation denied.")
        return 4

    if args.command == "list":
        emit({"agent": args.agent, "domains": data["domains"]}, args.json)
        return 0

    if args.command == "check":
        domain = allowed_domain(args.target, data)
        if domain:
            emit({"agent": args.agent, "allowed": True, "domain": domain}, args.json)
            return 0
        emit({"agent": args.agent, "allowed": False, "message": data["policy"]["deny_response"]}, args.json)
        return 3

    allowed: list[str] = []
    blocked_count = 0
    for target in args.targets:
        domain = allowed_domain(target, data)
        if domain:
            if domain not in allowed:
                allowed.append(domain)
        else:
            blocked_count += 1
    payload = {
        "agent": args.agent,
        "allowed_domains": allowed,
        "blocked_count": blocked_count,
        "all_allowed": blocked_count == 0,
    }
    if blocked_count:
        payload["message"] = data["policy"]["deny_response"]
    emit(payload, args.json)
    return 0 if allowed else 3


if __name__ == "__main__":
    sys.exit(main())
