"""Read-only Discord permission proof for SHEIN; no global user/role mutation."""
from __future__ import annotations
import json
import email.utils
import math
import threading
import urllib.parse
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
    return _read_json(request)


# Transport only: pacing metadata never contains response bodies or authority.
_READ_LOCK = threading.Lock()
_READ_DEADLINES = {}
_READ_MAX_ATTEMPTS = 4
_READ_MAX_WAIT = 30.0
_READ_MAX_ELAPSED = 90.0
_READ_MARGIN = 0.05


def _read_scope(request):
    # Conservatively share the whole major channel/guild budget, including
    # distinct message IDs. Different majors must not share route-local limits.
    parts = urllib.parse.urlsplit(request.full_url).path.split('/')
    for major in ('channels', 'guilds'):
        if major in parts:
            i = parts.index(major)
            if i + 1 < len(parts):
                return major + '/' + parts[i + 1]
    return urllib.parse.urlsplit(request.full_url).path


def _read_number(value):
    if isinstance(value, bool):
        raise ValueError('invalid rate delay')
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError('invalid rate delay')
    return number


def _read_delay(headers, body=None, *, limited=False):
    headers = {str(k).lower(): v for k, v in headers.items()}
    delays = []
    if 'retry-after' in headers:
        value = headers['retry-after']
        try:
            delay = _read_number(value)
        except ValueError:
            # Discord normally sends seconds; accept RFC HTTP dates, not NaN.
            date = email.utils.parsedate_to_datetime(value)
            if date is None or date.tzinfo is None:
                raise ValueError('invalid Retry-After')
            delay = max(0.0, date.timestamp() - time.time())
        delays.append(delay)
    if 'x-ratelimit-reset-after' in headers:
        delays.append(_read_number(headers['x-ratelimit-reset-after']))
    if 'x-ratelimit-reset' in headers:
        delays.append(max(0.0, _read_number(headers['x-ratelimit-reset']) - time.time()))
    if limited:
        if not isinstance(body, dict):
            raise ValueError('invalid rate response')
        if 'global' in body and not isinstance(body['global'], bool):
            raise ValueError('invalid global rate flag')
        if 'retry_after' in body:
            delays.append(_read_number(body['retry_after']))
    if not delays:
        raise ValueError('rate delay unavailable')
    return max(delays) + _READ_MARGIN


def _read_json(request):
    # One process-local transport lock; no persistent permission/content cache.
    # Cross-process competition still receives bounded fresh 429 retries.
    with _READ_LOCK:
        started = time.monotonic()
        waited = 0.0
        scope = _read_scope(request)
        for attempt in range(_READ_MAX_ATTEMPTS):
            now = time.monotonic()
            delay = max(0.0, max(_READ_DEADLINES.get(scope, 0.0),
                                 _READ_DEADLINES.get('*', 0.0)) - now)
            if (waited + delay > _READ_MAX_WAIT
                    or now - started + delay >= _READ_MAX_ELAPSED):
                raise ValueError('Discord permission proof rate limit wait bound exceeded')
            if delay:
                time.sleep(delay)
                waited += delay
            remaining = _READ_MAX_ELAPSED - (time.monotonic() - started)
            if remaining <= 0:
                raise ValueError('Discord permission proof elapsed bound exceeded')
            try:
                with urllib.request.urlopen(request, timeout=min(15, remaining)) as response:
                    body = json.load(response)
                    headers = {str(k).lower(): v for k, v in response.headers.items()}
                    if 'x-ratelimit-remaining' in headers:
                        count = _read_number(headers['x-ratelimit-remaining'])
                        if not count.is_integer():
                            raise ValueError('invalid remaining count')
                        if count == 0:
                            until = time.monotonic() + _read_delay(headers)
                            _READ_DEADLINES[scope] = max(_READ_DEADLINES.get(scope, 0.0), until)
                    return body
            except urllib.error.HTTPError as exc:
                if exc.code != 429:
                    exc.close()
                    raise ValueError('Discord permission proof unavailable; HTTP=' + str(exc.code)) from None
                try:
                    # The error document is small; never log its raw contents.
                    raw = exc.read(65537)
                    if len(raw) > 65536:
                        raise ValueError('oversize rate response')
                    body = json.loads(raw)
                    delay = _read_delay(exc.headers, body, limited=True)
                    global_limit = body.get('global') is True or str(exc.headers.get('X-RateLimit-Global', '')).lower() == 'true'
                    key = '*' if global_limit else scope
                    _READ_DEADLINES[key] = max(_READ_DEADLINES.get(key, 0.0), time.monotonic() + delay)
                except Exception:
                    raise ValueError('Discord permission proof malformed rate limit; HTTP=429') from None
                finally:
                    exc.close()
                if attempt + 1 == _READ_MAX_ATTEMPTS:
                    raise ValueError('Discord permission proof rate limit retry bound exceeded; HTTP=429') from None
            except Exception:
                raise ValueError('Discord permission proof transport unavailable') from None
        raise ValueError('Discord permission proof retry bound exceeded')


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
