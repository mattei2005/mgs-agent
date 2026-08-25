#!/usr/bin/env python3
"""Post Ares cron output to Discord.

Default behavior: post to a channel and create a thread from the message.
When --thread-id is provided: post directly into that existing thread and do
not create a new thread. This is used for operation-level daily/fixed threads
where each checkpoint should stay in one conversation instead of creating a
large thread list.

Reads message body from stdin. If stdin is empty, exits silently.
Does not print tokens or message content on errors beyond sanitized Discord error payloads.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = 'https://discord.com/api/v10'
DEFAULT_CHANNEL_ID = '1516887105543077949'  # ares-aquisicao
DEFAULT_ARCHIVE_MINUTES = 1440


def load_env(path: str = '/root/.hermes/profiles/ares/.env') -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def discord_request(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {
        'Authorization': f'Bot {token}',
        'User-Agent': 'mgs-ares-cron-thread-poster/1.0',
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {'raw': raw[:1000]}
        return e.code, payload


def thread_title(message: str, fallback: str) -> str:
    # Prefer the first title line inside the text block produced by Ares scripts.
    lines = [ln.strip() for ln in message.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        if ln == '```text' and i + 1 < len(lines):
            title = lines[i + 1]
            break
    else:
        title = fallback
    title = re.sub(r'[`*_#>\[\]()]+', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.replace(' — decisões simuladas', '')
    title = title.replace(' — ', ' - ')
    if len(title) > 90:
        title = title[:87].rstrip() + '...'
    return title or fallback


def split_message(message: str, limit: int = 1900) -> list[str]:
    """Split Discord content safely below the 2000-char hard limit.

    Prefer splitting at complete fenced code blocks so Discord never receives a
    chunk with an opening ``` but no closing ```. If a single fenced block is
    larger than the safe limit, fall back to line splitting for that block.
    """
    if len(message) <= limit:
        return [message]

    code_blocks = list(re.finditer(r'```[\s\S]*?```', message))
    if code_blocks:
        parts: list[str] = []
        pos = 0
        for match in code_blocks:
            pre = message[pos:match.start()]
            block = match.group(0)
            if pre.strip():
                parts.append(pre.strip())
            parts.append(block.strip())
            pos = match.end()
        tail = message[pos:]
        if tail.strip():
            parts.append(tail.strip())

        chunks: list[str] = []
        current = ''
        for part in parts:
            if len(part) > limit:
                if current:
                    chunks.append(current.rstrip())
                    current = ''
                chunks.extend(split_message_by_lines(part, limit))
                continue
            candidate = part if not current else current.rstrip() + '\n\n' + part
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    chunks.append(current.rstrip())
                current = part
        if current:
            chunks.append(current.rstrip())
        return chunks

    return split_message_by_lines(message, limit)


def split_message_by_lines(message: str, limit: int = 1900) -> list[str]:
    fence_match = re.match(r'^(?P<fence>```[^\n]*\n)(?P<body>[\s\S]*?)(?P<close>```\s*)$', message)
    if fence_match and len(message) > limit:
        return split_fenced_block(
            fence_match.group('fence'),
            fence_match.group('body').splitlines(),
            fence_match.group('close').strip(),
            limit,
        )
    chunks: list[str] = []
    current = ''
    for raw_line in message.splitlines(keepends=True):
        line = raw_line
        while len(line) > limit:
            if current:
                chunks.append(current.rstrip())
                current = ''
            chunks.append(line[:limit].rstrip())
            line = line[limit:]
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current:
        chunks.append(current.rstrip())
    return chunks


def split_fenced_block(opening: str, body_lines: list[str], closing: str = '```', limit: int = 1900) -> list[str]:
    """Split one oversized fenced block into valid fenced chunks.

    Discord rejects >2000 chars and renders badly when a chunk has an opening
    fence without a closing fence. Keep every part independently renderable.
    """
    chunks: list[str] = []
    current = opening
    close = closing or '```'
    overhead = len(opening) + len(close) + 2
    hard_line_limit = max(20, limit - overhead)
    for raw_line in body_lines:
        pieces = [raw_line]
        if len(raw_line) > hard_line_limit:
            pieces = [raw_line[i:i + hard_line_limit] for i in range(0, len(raw_line), hard_line_limit)]
        for line in pieces:
            candidate = current + line + '\n' + close
            if len(candidate) > limit and current != opening:
                chunks.append((current + close).rstrip())
                current = opening
            current += line + '\n'
    if current != opening:
        chunks.append((current + close).rstrip())
    return chunks or [(opening + close).rstrip()]


def with_part_labels(chunks: list[str], limit: int = 2000) -> list[str]:
    if len(chunks) == 1:
        return chunks
    total = len(chunks)
    labeled: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        prefix = f'Parte {i} de {total}\n'
        if len(prefix) + len(chunk) <= limit:
            labeled.append(prefix + chunk)
        else:
            labeled.append(chunk[:limit])
    return labeled


def post_message(target_channel: str, token: str, content: str) -> tuple[int, dict]:
    return discord_request('POST', f'/channels/{target_channel}/messages', token, {'content': content})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--channel-id', default=DEFAULT_CHANNEL_ID)
    ap.add_argument('--thread-id', help='Existing Discord thread/channel ID to post into; disables thread creation')
    ap.add_argument('--fallback-title', default='Ares Meta Ads')
    ap.add_argument('--archive-minutes', type=int, default=DEFAULT_ARCHIVE_MINUTES)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    msg = sys.stdin.read()
    if not msg.strip():
        return 0
    if msg.lstrip().startswith('[REPORT-INFRA]') and not args.thread_id:
        print(json.dumps({
            'ok': False,
            'error': 'report_infra_must_not_create_thread',
            'detail': 'Use /root/mgs-agent/scripts/ares-report-infra.sh for REPORT-INFRA so alerts-infra receives a plain channel message, not a new thread.',
        }, ensure_ascii=False), file=sys.stderr)
        return 8
    load_env()
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print(json.dumps({'ok': False, 'error': 'missing_discord_bot_token'}, ensure_ascii=False), file=sys.stderr)
        return 2
    title = thread_title(msg, args.fallback_title)
    chunks = with_part_labels(split_message(msg))
    if args.dry_run:
        print(json.dumps({
            'ok': True,
            'dry_run': True,
            'channel_id': args.channel_id,
            'thread_id': args.thread_id,
            'mode': 'post_existing_thread' if args.thread_id else 'post_channel_create_thread',
            'thread_title': title,
            'message_len': len(msg),
            'chunks': len(chunks),
            'chunk_lengths': [len(c) for c in chunks],
            'max_chunk_len': max(len(c) for c in chunks),
        }, ensure_ascii=False))
        return 0

    target_channel = args.thread_id or args.channel_id
    st, payload = post_message(target_channel, token, chunks[0])
    if st not in (200, 201):
        print(json.dumps({'ok': False, 'stage': 'post_message', 'target_channel': target_channel, 'status': st, 'chunk': 1, 'chunks': len(chunks), 'error': payload}, ensure_ascii=False), file=sys.stderr)
        return 3
    if args.thread_id:
        for idx, chunk in enumerate(chunks[1:], 2):
            st_next, payload_next = post_message(target_channel, token, chunk)
            if st_next not in (200, 201):
                print(json.dumps({'ok': False, 'stage': 'post_message_chunk', 'target_channel': target_channel, 'status': st_next, 'chunk': idx, 'chunks': len(chunks), 'error': payload_next}, ensure_ascii=False), file=sys.stderr)
                return 6
        return 0

    message_id = payload.get('id')
    if not message_id:
        print(json.dumps({'ok': False, 'stage': 'post_message', 'error': 'missing_message_id'}, ensure_ascii=False), file=sys.stderr)
        return 4

    st2, payload2 = discord_request('POST', f'/channels/{args.channel_id}/messages/{message_id}/threads', token, {
        'name': title,
        'auto_archive_duration': args.archive_minutes,
    })
    if st2 not in (200, 201):
        print(json.dumps({'ok': False, 'stage': 'create_thread', 'status': st2, 'message_id': message_id, 'error': payload2}, ensure_ascii=False), file=sys.stderr)
        return 5
    created_thread_id = payload2.get('id')
    if not created_thread_id:
        print(json.dumps({'ok': False, 'stage': 'create_thread', 'error': 'missing_thread_id', 'message_id': message_id}, ensure_ascii=False), file=sys.stderr)
        return 7
    for idx, chunk in enumerate(chunks[1:], 2):
        st_next, payload_next = post_message(created_thread_id, token, chunk)
        if st_next not in (200, 201):
            print(json.dumps({'ok': False, 'stage': 'post_thread_chunk', 'target_channel': created_thread_id, 'status': st_next, 'chunk': idx, 'chunks': len(chunks), 'error': payload_next}, ensure_ascii=False), file=sys.stderr)
            return 6
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
