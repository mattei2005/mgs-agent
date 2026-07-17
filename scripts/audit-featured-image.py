#!/usr/bin/env python3
"""Semantic featured-image audit for MGS REC/P1 runners.

Hard-gates the generated featured image before WordPress upload. It compares the
featured composition against the source card artwork and returns strict JSON.
Credentials are read from GEMINI_API_KEY or 1Password and are never printed.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple


class AuditError(Exception):
    pass


def image_size(path: Path) -> Tuple[int, int]:
    try:
        from PIL import Image
    except Exception as exc:
        raise AuditError(f"PIL unavailable for image audit: {exc}")
    with Image.open(path) as img:
        return img.size


def mime_for(path: Path) -> str:
    guessed = mimetypes.guess_type(str(path))[0]
    return guessed or "image/jpeg"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def load_env_file() -> None:
    env_file = Path("/root/mgs-agent/.env")
    if not env_file.exists():
        return
    for line in env_file.read_text(errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip().lstrip("export ").strip()
        v = v.strip().strip('"\'')
        if k and k not in os.environ:
            os.environ[k] = v


def gemini_key() -> str:
    load_env_file()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GEMINI_API_KEY"):
        if os.getenv(name):
            return os.environ[name]
    try:
        p = subprocess.run(
            ["op", "item", "get", "Gemini API Key - MGS Core", "--vault", os.getenv("OP_DEFAULT_VAULT", "MGS Conteúdo"), "--fields", "api_key", "--reveal"],
            text=True,
            capture_output=True,
            timeout=20,
            env=os.environ.copy(),
        )
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    except Exception:
        pass
    raise AuditError("Gemini API key unavailable for featured image semantic audit")


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise AuditError(f"Vision model did not return JSON: {text[:500]}")
    return json.loads(m.group(0))


def call_gemini(featured: Path, card: Path, mode: str, card_name: str, require_person: bool) -> Dict[str, Any]:
    prompt = f"""
You are a strict visual QA auditor for MGS Digital Corp credit-card article featured images.

Compare IMAGE A (featured composition) against IMAGE B (source card artwork).
Return ONLY valid JSON. No markdown.

Context:
- Article type: {mode.upper()}
- Card name: {card_name or 'unknown'}
- A realistic person is required: {'yes' if require_person else 'no'}

Hard requirements:
1. IMAGE A must be horizontal 16:9 hero artwork, not a card-only product shot.
2. The credit card must be clearly visible in IMAGE A.
3. The card in IMAGE A must preserve the same issuer/design/colours/layout as IMAGE B. Minor lighting/reflection is OK; redesigned, recoloured, wrong-logo, cropped, badge-like, or invented cards fail.
4. The composition must be a realistic contextual/lifestyle finance scene, not a generic stock background, illustration, CGI render, frame, poster, UI mockup, or decorative badge.
5. There must be no duplicate cards, competitor branding, site logo overlays, badges/stickers, readable fake UI text, or fingers/objects hiding important card identity.
6. If person_required is true, at least one realistic human/person/hand must be present naturally in the scene.

Return this exact JSON shape:
{{
  "ok": boolean,
  "score": number,
  "checks": {{
    "landscape_16_9": boolean,
    "card_visible": boolean,
    "card_identity_preserved": boolean,
    "theme_relevant": boolean,
    "not_generic_stock": boolean,
    "person_required": boolean,
    "person_present": boolean,
    "no_bad_artifacts": boolean
  }},
  "blocking_reasons": ["short reason", ...],
  "summary": "one concise sentence"
}}

Be conservative: if uncertain about card identity, fail card_identity_preserved.
""".strip()
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_for(featured), "data": b64(featured)}},
                {"inline_data": {"mime_type": mime_for(card), "data": b64(card)}},
            ]
        }],
        "generationConfig": {"temperature": 0.0, "response_mime_type": "application/json"},
    }
    model = os.getenv("MGS_FEATURED_AUDIT_MODEL", "gemini-2.5-flash")
    query = urllib.parse.urlencode({"key": gemini_key()})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?{query}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise AuditError(f"Gemini audit HTTP {exc.code}: {body}")
    doc = json.loads(raw)
    text_parts: List[str] = []
    for cand in doc.get("candidates", []) or []:
        for part in ((cand.get("content") or {}).get("parts") or []):
            if part.get("text"):
                text_parts.append(part["text"])
    if not text_parts:
        raise AuditError(f"Gemini audit returned no text: {raw[:500]}")
    return extract_json("\n".join(text_parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--featured", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--mode", choices=["rec", "p1"], required=True)
    ap.add_argument("--card-name", default="")
    ap.add_argument("--require-person", action="store_true", default=False)
    args = ap.parse_args()

    featured = Path(args.featured)
    card = Path(args.card)
    result: Dict[str, Any] = {
        "ok": False,
        "mode": args.mode,
        "featured_path": str(featured),
        "card_path": str(card),
        "blocking_reasons": [],
        "checks": {},
    }
    try:
        if not featured.exists():
            raise AuditError(f"featured image not found: {featured}")
        if not card.exists():
            raise AuditError(f"card image not found: {card}")
        fw, fh = image_size(featured)
        cw, ch = image_size(card)
        mechanical_ok = fw >= 1000 and fh >= 600 and abs((fw / fh) - (16 / 9)) <= 0.01
        result["dimensions"] = {"featured": {"width": fw, "height": fh, "aspect": round(fw / fh, 4)}, "card": {"width": cw, "height": ch, "aspect": round(cw / ch, 4) if ch else None}}
        if not mechanical_ok:
            raise AuditError(f"featured image failed mechanical 16:9/size gate: {fw}x{fh}")
        audit = call_gemini(featured, card, args.mode, args.card_name, bool(args.require_person))
        checks = audit.get("checks") or {}
        required = ["landscape_16_9", "card_visible", "card_identity_preserved", "theme_relevant", "not_generic_stock", "no_bad_artifacts"]
        if args.require_person:
            required.append("person_present")
        missing = [name for name in required if checks.get(name) is not True]
        score = float(audit.get("score") or 0.0)
        reasons = list(audit.get("blocking_reasons") or [])
        if score < 0.80:
            reasons.append(f"semantic score below 0.80: {score:.2f}")
        if missing:
            reasons.append("failed checks: " + ", ".join(missing))
        ok = not reasons and audit.get("ok") is True
        result.update(audit)
        result["ok"] = ok
        result["blocking_reasons"] = reasons
        result["dimensions"] = result.get("dimensions")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else 2
    except Exception as exc:
        result["error"] = str(exc)
        result.setdefault("blocking_reasons", []).append(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
