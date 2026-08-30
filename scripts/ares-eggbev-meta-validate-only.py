#!/usr/bin/env python3
"""Validate the Eggbev direct ad-creative payload against Meta without creating it."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("/root/mgs-agent")
SCRIPTS = BASE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
AUDIT = BASE / "data/ares/meta-ads/audit/eggbev/creation/meta-validate-only-creative-20260830.json"
ACCOUNT = "1034081997659047"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_error(payload: Any) -> dict[str, Any]:
    error = payload.get("error") if isinstance(payload, dict) else {}
    error = error if isinstance(error, dict) else {}
    return {
        "code": error.get("code"),
        "subcode": error.get("error_subcode"),
        "type": error.get("type"),
        "user_title": error.get("error_user_title"),
        "user_message": error.get("error_user_msg"),
        "message": str(error.get("message") or "")[:500],
    }


def creative_names(meta, token: str, expected: str) -> list[dict[str, Any]]:
    status, payload, _ = meta.graph_get(
        f"act_{ACCOUNT}/adcreatives",
        token,
        {"fields": "id,name,status", "limit": 100},
    )
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"creative inventory GET failed http={status}")
    return [row for row in payload.get("data") or [] if str(row.get("name") or "") == expected]


def main() -> int:
    runner = load(SCRIPTS / "ares-eggbev-creation.py", "eggbev_validate_runner")
    from ares_campaign_v3 import eggbev_create as create
    page, meta, token = runner.live_page_and_token("pg_5024")
    status, videos_payload, _ = meta.graph_get(
        f"act_{ACCOUNT}/advideos",
        token,
        {"fields": "id,title,status", "limit": 100},
    )
    if status != 200 or not isinstance(videos_payload, dict):
        raise RuntimeError(f"video GET failed http={status}")
    ready = []
    for row in videos_payload.get("data") or []:
        text = json.dumps(row.get("status") or {}, sort_keys=True).upper()
        if ("READY" in text or "COMPLETE" in text or "PUBLISHED" in text) and "ERROR" not in text and "FAILED" not in text:
            ready.append(str(row["id"]))
    ready = list(dict.fromkeys(ready))
    if len(ready) < 2:
        raise RuntimeError("two ready ad-account videos were not available")
    unique = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    creative_name = f"VALIDATE ONLY EGGBEV pg_5024 {unique}"
    payload = create._creative_payload(
        media={"vertical_video_id": ready[0], "square_video_id": ready[1]},
        page_id=str(page["id"]),
        instagram_user_id=str(page["instagram_user_id"]),
        page_token="pg_5024",
        label_prefix=f"validate_{unique}",
        primary_text="",
        headlines=["APPLY NOW ✅", "CARD APPROVED", "✔️ APPLY CARD"],
        description="⭐️⭐️⭐️⭐️⭐️",
        cta="APPLY_NOW",
    )
    payload["name"] = creative_name
    before = creative_names(meta, token, creative_name)
    if before:
        raise RuntimeError("validate-only creative name unexpectedly existed before POST")
    params = {**payload, "execution_options": ["validate_only"]}
    http, response, _ = meta.graph_post_once(f"act_{ACCOUNT}/adcreatives", token, params)
    after = creative_names(meta, token, creative_name)
    side_effect_ids = [str(response.get("id"))] if isinstance(response, dict) and response.get("id") else []
    side_effect_ids.extend(str(row.get("id")) for row in after if row.get("id"))
    result = {
        "operation": "Eggbev-US-CC-EN-BOT",
        "mode": "direct_adcreative_validate_only",
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_token": "pg_5024",
        "page_readback": {"id_present": bool(page.get("id")), "name": page.get("name")},
        "video_inputs": {"count": 2, "account_associated": True, "ready": True},
        "creative_name": creative_name,
        "payload_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "http": http,
        "response_success": bool(isinstance(response, dict) and response.get("success") is True),
        "error": safe_error(response),
        "before_name_matches": len(before),
        "after_name_matches": len(after),
        "side_effect_ids": side_effect_ids,
        "status": "VALIDATE_ONLY_OK" if http in {200, 201} and not side_effect_ids else ("SIDE_EFFECT_DETECTED" if side_effect_ids else "VALIDATE_ONLY_REJECTED"),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "VALIDATE_ONLY_OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
