#!/usr/bin/env python3
"""Validate a self-contained Google Ads AMPHTML creative and optionally zip it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

AMP_RUNTIME = "https://cdn.ampproject.org/amp4ads-v0.js"


def fail(message: str) -> None:
    print(json.dumps({"status": "FAIL", "error": message}, ensure_ascii=False))
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--zip", dest="zip_path", type=Path)
    return parser.parse_args()


def require(pattern: str, text: str, label: str, flags: int = 0) -> None:
    if not re.search(pattern, text, flags):
        fail(f"mandatory marker missing: {label}")


def forbid(pattern: str, text: str, label: str, flags: int = 0) -> None:
    if re.search(pattern, text, flags):
        fail(f"forbidden construct found: {label}")


def main() -> None:
    args = parse_args()
    html_path = args.html.resolve()
    if not html_path.is_file():
        fail(f"HTML file not found: {html_path}")
    if args.width <= 0 or args.height <= 0:
        fail("width and height must be positive")

    raw = html_path.read_bytes()
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"index.html is not UTF-8: {exc}")

    require(r"<!doctype\s+html>", html, "doctype", re.I)
    require(r"<html\b[^>]*(?:⚡4ads|\bamp4ads\b)", html, "html AMP4ADS attribute", re.I)
    require(r"<meta\s+charset=[\"']utf-8[\"']", html, "UTF-8 charset", re.I)
    require(r"<meta\b[^>]*name=[\"']viewport[\"']", html, "viewport", re.I)
    require(r"<style\s+amp4ads-boilerplate>", html, "amp4ads boilerplate", re.I)
    require(r"<style\s+amp-custom>", html, "amp-custom", re.I)
    require(re.escape(AMP_RUNTIME), html, "official AMP4ADS runtime")

    expected_size = rf"width\s*=\s*{args.width}\s*,\s*height\s*=\s*{args.height}"
    require(
        rf"<meta\b[^>]*name=[\"']ad\.size[\"'][^>]*content=[\"'][^\"']*{expected_size}[^\"']*[\"']",
        html,
        f"ad.size {args.width}x{args.height}",
        re.I,
    )

    forbidden = [
        (r"<(?:amp-)?img\b", "raster image tag"),
        (r"<image\b", "SVG image reference"),
        (r"\burl\s*\(", "CSS url()"),
        (r"\bdata\s*:", "data URI"),
        (r"<link\b[^>]*rel=[\"']stylesheet[\"']", "external stylesheet"),
        (r"amp-ad-exit|exit-api|ExitApi", "custom exit component/API"),
        (r"\bfinalUrl\b", "embedded finalUrl"),
        (r"\btap\s*:[^\"']*\.exit\s*\(", "custom tap exit"),
        (r"<script\b(?![^>]*src=[\"']https://cdn\.ampproject\.org/amp4ads-v0\.js[\"'])", "custom or extra script"),
    ]
    for pattern, label in forbidden:
        forbid(pattern, html, label, re.I | re.S)

    validator = subprocess.run(
        [
            "npx",
            "--yes",
            "amphtml-validator",
            "--html_format",
            "AMP4ADS",
            "--format",
            "text",
            str(html_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    validator_output = "\n".join(
        part.strip() for part in (validator.stdout, validator.stderr) if part.strip()
    )
    if validator.returncode != 0 or not re.search(r":\s*PASS\s*$", validator.stdout, re.M):
        fail(f"AMP4ADS validator failed: {validator_output[-1500:]}")

    result: dict[str, object] = {
        "status": "PASS",
        "html": str(html_path),
        "dimension": f"{args.width}x{args.height}",
        "amp4ads": "PASS",
        "self_contained": True,
        "custom_exit": False,
    }

    if args.zip_path:
        zip_path = args.zip_path.resolve()
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{zip_path.name}.", suffix=".tmp", dir=str(zip_path.parent)
        )
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("index.html", raw)
            with zipfile.ZipFile(tmp_path) as archive:
                members = archive.namelist()
                bad_member = archive.testzip()
                readback = archive.read("index.html")
            if members != ["index.html"]:
                fail(f"unexpected ZIP members: {members}")
            if bad_member is not None:
                fail(f"corrupt ZIP member: {bad_member}")
            if readback != raw:
                fail("ZIP index.html readback differs from validated HTML")
            os.replace(tmp_path, zip_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        result.update(
            {
                "zip": str(zip_path),
                "zip_members": ["index.html"],
                "zip_member_count": 1,
                "zip_readback": True,
                "zip_size_bytes": zip_path.stat().st_size,
            }
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
