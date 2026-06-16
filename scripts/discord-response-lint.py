#!/usr/bin/env python3
"""MGS Discord response lint.

Purpose: prevent malformed/ugly Discord output before long operational reports.
This is a local helper for agents: pipe a draft into it with --check or --fix.
It is intentionally conservative and does not call external services.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LANG_FENCE_RE = re.compile(r"^```[A-Za-z0-9_-]+\s*$", re.M)
FENCE_RE = re.compile(r"^```", re.M)
PIPE_TABLE_RE = re.compile(r"^\|.*\|\s*$", re.M)
STANDALONE_TEXT_RE = re.compile(r"(?m)^text\s*$")


def load_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(errors="replace")
    return sys.stdin.read()


def lint(text: str) -> list[str]:
    issues: list[str] = []
    lang_fences = LANG_FENCE_RE.findall(text)
    fence_count = len(FENCE_RE.findall(text))
    if lang_fences:
        issues.append(f"language-tagged code fences found: {len(lang_fences)}; use plain ``` or no fence in Discord")
    if fence_count > 2:
        issues.append(f"too many code fences: {fence_count}; prefer one plain block max or bullet sections")
    if STANDALONE_TEXT_RE.search(text):
        issues.append("standalone 'text' line found; this often leaks from rendered language labels")
    pipe_lines = PIPE_TABLE_RE.findall(text)
    if len(pipe_lines) >= 2:
        issues.append("raw Markdown pipe table detected; use aligned plain text blocks/bullets for Discord")
    if "```text" in text or "```bash" in text or "```json" in text:
        issues.append("explicit ```text/```bash/```json fence detected; avoid language tags in Discord replies")
    return issues


def fix(text: str) -> str:
    # Convert language-tagged fences to plain fences.
    text = re.sub(r"^```[A-Za-z0-9_-]+\s*$", "```", text, flags=re.M)
    # Remove standalone accidental language labels.
    text = re.sub(r"(?m)^text\s*\n", "", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint/fix Discord-safe MGS response drafts")
    parser.add_argument("path", nargs="?", help="Draft file. If omitted, read stdin.")
    parser.add_argument("--fix", action="store_true", help="Print fixed text to stdout")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if issues are found")
    args = parser.parse_args()

    text = load_text(args.path)
    if args.fix:
        sys.stdout.write(fix(text))
        return 0

    issues = lint(text)
    if issues:
        print("DISCORD_RESPONSE_LINT: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1 if args.check else 0
    print("DISCORD_RESPONSE_LINT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
