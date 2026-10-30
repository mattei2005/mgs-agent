"""Read-only Discord permission proof for SHEIN; no global user/role mutation."""
from __future__ import annotations
import json
import re
import time
import urllib.error
import urllib.request
from contextvars import ContextVar
from pathlib import Path

GUILD = '1185714635991679006'
VIEW = 1 << 10
SEND = 1 << 11
THREAD_SEND = 1 << 38
MANAGE_THREADS = 1 << 34
ADMIN = 1 << 3
CACHE: ContextVar[dict | None] = ContextVar('shein_channel_permission_cache', default=None)


def _get(path):
    # Only the current Ares bot identity. No Zeus/personal/browser fallback.
    token = None
    for raw in Path('/root/.hermes/profiles/ares/.env').read_text().splitlines():
        key, sep, value = raw.strip().partition('=')
        if sep and key == 'DISCORD_BOT_TOKEN':
            token = value.strip().strip('"').strip("'")
            break
    if not token:
        raise ValueError('Ares Discord read identity unavailable')
    request = urllib.request.Request('https://discord.com/api/v10' + path, headers={
        'Authorization': 'Bot ' + token, 'User-Agent': 'MGS-Ares/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ValueError('Discord permission proof unavailable; HTTP=' + str(exc.code)) from None
    except Exception:
        raise ValueError('Discord permission proof transport unavailable') from None


def effective_permissions(guild_id, owner_id, roles, member, channel):
    actor = str((member.get('user') or {}).get('id') or '')
    role_ids = {str(r) for r in member.get('roles', [])} | {guild_id}
    found = {str(r.get('id')) for r in roles}
    if not role_ids.issubset(found):
        raise ValueError('Discord role proof incomplete')
    permissions = 0
    for role in roles:
        if str(role.get('id')) in role_ids:
            permissions |= int(role.get('permissions') or 0)
    if actor == owner_id or permissions & ADMIN:
        return (1 << 53) - 1
    overwrites = channel.get('permission_overwrites') or []
    for item in overwrites:
        if int(item['type']) == 0 and str(item['id']) == guild_id:
            permissions = (permissions & ~int(item.get('deny') or 0)) | int(item.get('allow') or 0)
    deny = allow = 0
    for item in overwrites:
        if int(item['type']) == 0 and str(item['id']) in role_ids - {guild_id}:
            deny |= int(item.get('deny') or 0)
            allow |= int(item.get('allow') or 0)
    permissions = (permissions & ~deny) | allow
    for item in overwrites:
        if int(item['type']) == 1 and str(item['id']) == actor:
            permissions = (permissions & ~int(item.get('deny') or 0)) | int(item.get('allow') or 0)
    return permissions


def verify(request, profile, *, force=False):
    actor = str(request.get('authorized_by') or '')
    parent = str(request.get('source_channel_id') or '')
    origin = str(request.get('source_thread_id') or '')
    if any(not re.fullmatch(r'[0-9]{17,20}', value) for value in [actor, parent, origin]):
        raise ValueError('exact sender, parent channel and origin IDs required')
    if parent != str(profile.get('channel_id')):
        raise ValueError('account and parent channel do not match')
    key = (actor, parent, origin)
    cache = CACHE.get()
    if not force and cache is not None and key in cache and time.monotonic() - cache[key][0] < 15:
        return cache[key][1]
    channel = _get('/channels/' + parent)
    if str(channel.get('id')) != parent or str(channel.get('guild_id')) != GUILD or channel.get('type') != 0:
        raise ValueError('canonical SHEIN channel identity mismatch')
    guild = _get('/guilds/' + GUILD)
    if str(guild.get('id')) != GUILD:
        raise ValueError('Discord guild identity mismatch')
    roles = _get('/guilds/' + GUILD + '/roles')
    member = _get('/guilds/' + GUILD + '/members/' + actor)
    if str((member.get('user') or {}).get('id')) != actor or (member.get('user') or {}).get('bot'):
        raise ValueError('human requester identity mismatch')
    if member.get('communication_disabled_until'):
        from datetime import datetime, timezone
        if datetime.fromisoformat(member['communication_disabled_until']) > datetime.now(timezone.utc):
            raise ValueError('requester cannot communicate in the channel')
    permissions = effective_permissions(GUILD, str(guild.get('owner_id')), roles, member, channel)
    required = VIEW | SEND
    if origin != parent:
        thread = _get('/channels/' + origin)
        if (str(thread.get('id')) != origin or str(thread.get('guild_id')) != GUILD
                or str(thread.get('parent_id')) != parent or thread.get('type') not in {11,12}):
            raise ValueError('thread does not belong to the account channel')
        required = VIEW | THREAD_SEND
        if thread.get('type') == 12 and not permissions & MANAGE_THREADS:
            membership = _get('/channels/' + origin + '/thread-members/' + actor)
            if str(membership.get('user_id')) != actor:
                raise ValueError('private thread requester access unconfirmed')
        metadata = thread.get('thread_metadata') or {}
        if metadata.get('locked') and metadata.get('archived') and not permissions & MANAGE_THREADS:
            raise ValueError('thread cannot accept requester messages')
    if permissions & required != required:
        raise ValueError('requester lacks effective channel communication permissions')
    proof = {'verified': True, 'sender_id': actor, 'parent_channel_id': parent, 'origin_id': origin,
             'source': 'live_discord_effective_permissions'}
    if cache is not None:
        cache[key] = (time.monotonic(), proof)
    return proof
