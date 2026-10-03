"""Direct Zeus bot delivery with durable callback and exact target readback.
No 1Password lookup; secrets never appear in exceptions or payloads.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL = '1498132022634483894'


def bot_token() -> str:
    override = os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')
    if override is not None:
        return override
    token = os.environ.get('DISCORD_BOT_TOKEN', '')
    if not token:
        p = Path(os.environ.get('MGS_DISCORD_ENV_FILE', '/root/.hermes/profiles/zeus/.env'))
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith('DISCORD_BOT_TOKEN='):
                    token = line.split('=', 1)[1].strip().strip('\"\'')
                    break
    if not token:
        raise RuntimeError('Discord bot authentication unavailable; delivery remains pending')
    return token


def collection_url(channel: str) -> str:
    return os.environ.get('MGS_DISCORD_API_URL_OVERRIDE') or f'https://discord.com/api/v10/channels/{channel}/messages'


def request(method: str, url: str, payload=None):
    if os.environ.get('MGS_FORCE_DISCORD_AUTH_FAIL') == '1':
        raise RuntimeError('Discord authentication failure fixture; delivery remains pending')
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
        headers={'Authorization': 'Bot ' + bot_token(), 'Content-Type': 'application/json', 'User-Agent': 'MGS-Zeus-alerts/2'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Discord HTTP {exc.code}; delivery remains pending') from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError('Discord transport/readback unavailable; delivery remains pending') from None


def post_verified(payload: dict, *, channel=CHANNEL, prior_id=None, on_created=None):
    # The caller persists an outbox BEFORE calling this function. A returned POST
    # ID is persisted BEFORE GET so a GET outage retries readback, not delivery.
    for embed in payload.get('embeds') or []:
        for field in embed.get('fields') or []:
            field.setdefault('inline', False)
    url = collection_url(channel)
    if not prior_id:
        result = request('POST', url, payload)
        prior_id = str(result.get('id') or '')
        if not prior_id.isdigit():
            raise RuntimeError('Discord POST missing message identity; delivery remains pending')
        if on_created:
            on_created(prior_id)
    result = request('GET', url.rstrip('/') + '/' + str(prior_id))
    expected = payload.get('embeds') or []
    actual = result.get('embeds') or []
    if str(result.get('id')) != str(prior_id) or result.get('content', '') != payload.get('content', ''):
        raise RuntimeError('Discord target identity/content readback mismatch; delivery remains pending')
    if len(expected) != len(actual):
        raise RuntimeError('Discord embed count readback mismatch; delivery remains pending')
    for wanted, got in zip(expected, actual):
        for key in ('title', 'description', 'fields', 'color'):
            if key in wanted and wanted[key] != got.get(key):
                raise RuntimeError('Discord embed readback mismatch; delivery remains pending')
    return str(prior_id)
