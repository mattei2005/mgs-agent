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
DEFAULT_CHANNEL_ID = '1516887105543077949'  # logs-aquisicao
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
    title = title.replace('OpenzedFinanzas-ES-CC-ES-03', 'OpenzedFinanzas')
    title = title.replace(' — decisões simuladas', '')
    title = title.replace(' — ', ' - ')
    if len(title) > 90:
        title = title[:87].rstrip() + '...'
    return title or fallback


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
    load_env()
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print(json.dumps({'ok': False, 'error': 'missing_discord_bot_token'}, ensure_ascii=False), file=sys.stderr)
        return 2
    title = thread_title(msg, args.fallback_title)
    if args.dry_run:
        print(json.dumps({
            'ok': True,
            'dry_run': True,
            'channel_id': args.channel_id,
            'thread_id': args.thread_id,
            'mode': 'post_existing_thread' if args.thread_id else 'post_channel_create_thread',
            'thread_title': title,
            'message_len': len(msg),
        }, ensure_ascii=False))
        return 0

    target_channel = args.thread_id or args.channel_id
    st, payload = discord_request('POST', f'/channels/{target_channel}/messages', token, {'content': msg})
    if st not in (200, 201):
        print(json.dumps({'ok': False, 'stage': 'post_message', 'target_channel': target_channel, 'status': st, 'error': payload}, ensure_ascii=False), file=sys.stderr)
        return 3
    if args.thread_id:
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
