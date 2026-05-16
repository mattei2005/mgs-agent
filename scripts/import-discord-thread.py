#!/usr/bin/env python3
"""Import a Discord thread/channel history by link or channel ID.

Read-only against Discord. Writes local JSON + Markdown snapshots under
/root/mgs-agent/data/discord-thread-imports/ so Zeus can answer questions about
specific historical threads when Rodolfo provides the link/ID.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("/root/mgs-agent/data/discord-thread-imports")
ENV_FILES = [Path("/root/.hermes/profiles/zeus/.env"), Path("/root/mgs-agent/.env")]
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "Hermes-Agent (https://github.com/NousResearch/hermes-agent)"


def load_env_files() -> None:
    """Load simple KEY=VALUE entries without overwriting existing env vars."""
    for env_path in ENV_FILES:
        if not env_path.exists():
            continue
        try:
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


def extract_channel_id(value: str) -> str:
    value = value.strip().strip("<>")
    if re.fullmatch(r"\d{15,25}", value):
        return value

    # Discord message/thread links:
    # https://discord.com/channels/{guild_id}/{channel_or_thread_id}/{message_id?}
    match = re.search(r"discord(?:app)?\.com/channels/\d+/(\d{15,25})(?:/\d{15,25})?", value)
    if match:
        return match.group(1)

    raise SystemExit("ERROR: informe um thread/channel ID ou link Discord válido")


def api_get(path: str, token: str, query: dict[str, str] | None = None) -> Any:
    url = f"{API_BASE}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": USER_AGENT,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"ERROR Discord API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"ERROR Discord API: {exc}") from exc


def fetch_all_messages(channel_id: str, token: str, limit: int | None = None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    before: str | None = None

    while True:
        page_limit = 100
        if limit is not None:
            remaining = limit - len(messages)
            if remaining <= 0:
                break
            page_limit = min(page_limit, remaining)

        query = {"limit": str(page_limit)}
        if before:
            query["before"] = before

        page = api_get(f"/channels/{channel_id}/messages", token, query)
        if not page:
            break

        messages.extend(page)
        before = page[-1]["id"]

        if len(page) < page_limit:
            break
        time.sleep(0.25)  # gentle pagination

    messages.sort(key=lambda m: int(m["id"]))
    return messages


def author_label(message: dict[str, Any]) -> str:
    author = message.get("author") or {}
    name = author.get("global_name") or author.get("username") or "unknown"
    uid = author.get("id", "unknown")
    return f"{name} ({uid})"


def message_text(message: dict[str, Any]) -> str:
    parts: list[str] = []
    content = message.get("content") or ""
    if content:
        parts.append(content)
    attachments = message.get("attachments") or []
    for att in attachments:
        url = att.get("url")
        filename = att.get("filename") or "attachment"
        if url:
            parts.append(f"[attachment: {filename}] {url}")
    embeds = message.get("embeds") or []
    for idx, embed in enumerate(embeds, start=1):
        title = embed.get("title") or "embed"
        desc = embed.get("description") or ""
        parts.append(f"[embed {idx}: {title}] {desc}".strip())
    return "\n".join(parts).strip()


def render_markdown(channel: dict[str, Any], messages: list[dict[str, Any]], source: str) -> str:
    imported_at = dt.datetime.now(dt.timezone.utc).isoformat()
    lines = [
        f"# Discord thread import: {channel.get('name') or channel.get('id')}",
        "",
        f"- Source: `{source}`",
        f"- Channel/thread ID: `{channel.get('id')}`",
        f"- Type: `{channel.get('type')}`",
        f"- Imported at UTC: `{imported_at}`",
        f"- Messages: `{len(messages)}`",
        "",
        "---",
        "",
    ]
    for msg in messages:
        ts = msg.get("timestamp", "")
        mid = msg.get("id", "")
        text = message_text(msg)
        if not text:
            text = "[sem texto]"
        lines.extend([
            f"## {ts} — {author_label(msg)} — {mid}",
            "",
            text,
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa histórico de uma thread/canal Discord por link ou ID (read-only).")
    parser.add_argument("thread", help="Link Discord ou ID da thread/canal")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help=f"Diretório de saída (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--limit", type=int, default=None, help="Limite máximo de mensagens para importar")
    args = parser.parse_args()

    load_env_files()
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("ERROR: DISCORD_BOT_TOKEN não encontrado no ambiente/.env")

    channel_id = extract_channel_id(args.thread)
    channel = api_get(f"/channels/{channel_id}", token)
    messages = fetch_all_messages(channel_id, token, args.limit)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    imported_at = dt.datetime.now(dt.timezone.utc).isoformat()

    payload = {
        "source": args.thread,
        "imported_at_utc": imported_at,
        "channel": channel,
        "message_count": len(messages),
        "messages": messages,
    }

    json_path = out_dir / f"{channel_id}.json"
    md_path = out_dir / f"{channel_id}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(channel, messages, args.thread), encoding="utf-8")

    print(f"OK imported thread_id={channel_id} messages={len(messages)}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
