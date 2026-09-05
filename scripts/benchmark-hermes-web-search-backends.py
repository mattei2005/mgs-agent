#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""A/B benchmark for Hermes DDGS and Perplexity web search providers.

The Perplexity key is resolved from the profile's configured 1Password
reference and is never printed or persisted in the output artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--query", action="append", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument(
        "--config", default="/root/.hermes/profiles/zeus/config.yaml"
    )
    return p.parse_args()


def _resolve_perplexity_key(config_path: str) -> str:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    op_cfg = ((cfg.get("secrets") or {}).get("onepassword") or {})
    if op_cfg.get("enabled") is not True:
        raise RuntimeError("Hermes 1Password secret source is not enabled")
    ref = (op_cfg.get("env") or {}).get("PERPLEXITY_API_KEY")
    if not isinstance(ref, str) or not ref.startswith("op://"):
        raise RuntimeError("PERPLEXITY_API_KEY has no valid op:// mapping")
    binary = op_cfg.get("binary_path") or "/usr/bin/op"
    proc = subprocess.run(
        [binary, "read", "--", ref],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    key = proc.stdout.strip()
    if not key:
        raise RuntimeError("1Password returned an empty PERPLEXITY_API_KEY")
    return key


def _dedupe(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for run in runs:
        for item in run.get("results", []):
            url = str(item.get("url") or "").strip().rstrip("/")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)
    return unique


def main() -> int:
    args = _args()
    if not 1 <= args.limit <= 20:
        raise SystemExit("--limit must be between 1 and 20")

    from plugins.web.ddgs.provider import DDGSWebSearchProvider
    from plugins.web.perplexity.provider import PerplexityWebSearchProvider

    key = _resolve_perplexity_key(args.config)
    os.environ["PERPLEXITY_API_KEY"] = key
    providers = {
        "ddgs": DDGSWebSearchProvider(),
        "perplexity": PerplexityWebSearchProvider(),
    }
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "method": "same queries, same result limit, native Hermes providers",
        "limit": args.limit,
        "queries": args.query,
        "backends": {},
    }
    try:
        for name, provider in providers.items():
            runs: list[dict[str, Any]] = []
            for query in args.query:
                started = time.monotonic()
                response = provider.search(query, limit=args.limit)
                elapsed = round(time.monotonic() - started, 3)
                rows = ((response.get("data") or {}).get("web") or []) if response.get("success") else []
                runs.append(
                    {
                        "query": query,
                        "success": bool(response.get("success")),
                        "elapsed_seconds": elapsed,
                        "error": response.get("error"),
                        "results": rows,
                    }
                )
            artifact["backends"][name] = {
                "runs": runs,
                "successful_queries": sum(1 for r in runs if r["success"]),
                "total_results": sum(len(r["results"]) for r in runs),
                "unique_results": _dedupe(runs),
                "total_elapsed_seconds": round(
                    sum(float(r["elapsed_seconds"]) for r in runs), 3
                ),
            }
    finally:
        os.environ.pop("PERPLEXITY_API_KEY", None)
        key = ""

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(output)

    summary = {
        name: {
            "successful_queries": data["successful_queries"],
            "total_results": data["total_results"],
            "unique_results": len(data["unique_results"]),
            "elapsed_seconds": data["total_elapsed_seconds"],
        }
        for name, data in artifact["backends"].items()
    }
    print(json.dumps({"output": str(output), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
