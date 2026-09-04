#!/usr/bin/env python3
import importlib.util
import json
import os
import urllib.request
from pathlib import Path

POSTER = Path('/root/mgs-agent/scripts/discord-bot-post.py')
CHANNEL_ID = '1498132022634483894'
MESSAGE_ID = '1545540177831665695'
spec = importlib.util.spec_from_file_location('discord_poster', POSTER)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load Discord poster')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.load_env(mod.DEFAULT_ENV)
token = os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN')
if not token:
    raise RuntimeError('Discord bot token unavailable')
url = f'https://discord.com/api/v10/channels/{CHANNEL_ID}/messages/{MESSAGE_ID}'
req = urllib.request.Request(url, headers={'Authorization': 'Bot ' + token, 'User-Agent': 'MGS-Zeus/1.0'})
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.load(resp)
embeds = data.get('embeds') or []
result = {
    'http': resp.status,
    'message_id_matches': str(data.get('id')) == MESSAGE_ID,
    'channel_id_matches': str(data.get('channel_id')) == CHANNEL_ID,
    'content_empty': data.get('content') == '',
    'embed_count': len(embeds),
    'embed_title': embeds[0].get('title') if embeds else None,
    'has_mentions': bool(data.get('mentions')),
    'has_thread': bool(data.get('thread')),
}
result['all_pass'] = all([
    result['http'] == 200,
    result['message_id_matches'],
    result['channel_id_matches'],
    result['content_empty'],
    result['embed_count'] == 1,
    str(result['embed_title']).startswith('REPORT-INFRA'),
    not result['has_mentions'],
    not result['has_thread'],
])
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['all_pass'] else 2)
