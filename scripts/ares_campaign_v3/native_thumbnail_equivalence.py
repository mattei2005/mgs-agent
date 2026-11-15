"""Strict pairwise native Facebook thumbnail byte proof; never a URL normalizer.

Receipts are evidence, not authorization or a cache: every production comparison
fetches both URLs afresh. No cookies, tokens or proxies are used. Only one
strictly validated HTTPS image-CDN redirect is accepted.
"""
from __future__ import annotations

import copy
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import urlsplit
from typing import Any

MAX_BYTES = 4 * 1024 * 1024
TIMEOUT = 10
NATIVE = re.compile(r'https://www\.facebook\.com/ads/image/\?d=[A-Za-z0-9_-]{1,2048}\Z')
EDGES = ('ads', 'all_ads', 'technical_seed_ads')
SUFFIX = ('creative', 'object_story_spec', 'video_data', 'image_url')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_url(url):
    if not isinstance(url, str) or not NATIVE.fullmatch(url):
        raise ValueError('native thumbnail URL shape rejected')
    p = urlsplit(url)
    if (p.scheme, p.netloc, p.path, p.fragment) != ('https', 'www.facebook.com', '/ads/image/', ''):
        raise ValueError('native thumbnail endpoint rejected')
    return url


class _PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        # Resolve once, reject mixed private/public answers, connect to the exact
        # validated numeric IP; TLS still verifies www.facebook.com (no rebinding).
        answers = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(str(row[4][0]) for row in answers))
        if not ips or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast or ipaddress.ip_address(ip).is_reserved for ip in ips):
            raise ValueError('native thumbnail DNS rejected')
        raw = socket.create_connection((ips[0], 443), self.timeout)
        try:
            self.sock = getattr(self, '_context').wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def _cdn_redirect(url):
    # Exactly one image CDN hop is intrinsic to /ads/image/. Never a generic
    # redirect follower: no ports/userinfo/fragments, HTML paths or arbitrary host.
    if not isinstance(url, str) or len(url) > 8192 or not re.fullmatch(r'[\x21-\x7e]+', url):
        raise ValueError('native thumbnail CDN redirect rejected')
    p = urlsplit(url)
    if p.scheme != 'https' or not re.fullmatch(r'scontent-[a-z0-9-]+\.xx\.fbcdn\.net', p.netloc) or p.fragment:
        raise ValueError('native thumbnail CDN endpoint rejected')
    if not re.fullmatch(r'/v/t[0-9.]+-[0-9]+/[0-9]+_[0-9]+_[0-9]+_n\.(?:jpg|png|webp)', p.path):
        raise ValueError('native thumbnail CDN image path rejected')
    from urllib.parse import parse_qsl
    pairs = parse_qsl(p.query, keep_blank_values=True, strict_parsing=True)
    if not pairs or len({k for k, _ in pairs}) != len(pairs) or any(not v or not (re.fullmatch(r'_nc_[a-z]+', k) or k in {'oh', 'oe', 'ccb'}) for k, v in pairs):
        raise ValueError('native thumbnail CDN query rejected')
    return p


def fetch_native(url):
    validate_url(url)
    conn = _PinnedHTTPS('www.facebook.com', timeout=TIMEOUT, context=ssl.create_default_context())
    headers = {'Accept': 'image/*', 'User-Agent': 'python-requests/2.32.3', 'Connection': 'close'}
    try:
        conn.request('GET', '/ads/image/?' + urlsplit(url).query, headers=headers)
        response = conn.getresponse()
        if response.status in {301, 302, 303, 307, 308}:
            target = _cdn_redirect(response.getheader('Location'))
            conn.close()
            conn = _PinnedHTTPS(target.netloc, timeout=TIMEOUT, context=ssl.create_default_context())
            conn.request('GET', target.path + '?' + target.query, headers=headers)
            response = conn.getresponse()
        if response.status != 200 or response.getheader('Location') is not None:
            raise ValueError('native thumbnail fetch status/redirect rejected')
        if response.getheader('Content-Encoding', 'identity') != 'identity':
            raise ValueError('native thumbnail encoding rejected')
        size = response.getheader('Content-Length')
        if size is not None and (not size.isdigit() or not 0 < int(size) <= MAX_BYTES):
            raise ValueError('native thumbnail size rejected')
        mime = response.getheader('Content-Type', '').split(';')[0].lower()
        if mime not in {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}:
            raise ValueError('native thumbnail content type rejected')
        body = response.read(MAX_BYTES + 1)
        if not body or len(body) > MAX_BYTES or (size is not None and len(body) != int(size)):
            raise ValueError('native thumbnail incomplete/oversize response')
        signatures = {'image/jpeg': body.startswith(b'\xff\xd8\xff'), 'image/png': body.startswith(b'\x89PNG\r\n\x1a\n'),
                      'image/webp': body.startswith(b'RIFF') and body[8:12] == b'WEBP',
                      'image/gif': body.startswith((b'GIF87a', b'GIF89a'))}
        if not signatures[mime]:
            raise ValueError('native thumbnail signature rejected')
        return body
    except Exception:
        # Never include the signed URL or transport exception in durable errors.
        raise ValueError('native thumbnail safe fetch failed') from None
    finally:
        conn.close()


def _diff(a: Any, b: Any, path: tuple = ()) -> list[tuple]:
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        if set(a) != set(b):
            return [path]
        return [p for k in a for p in _diff(a[k], b[k], path + (k,))]
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in _diff(x, y, path + (i,))]
    return [] if a == b else [path]


def _at(value, path):
    for key in path:
        value = value[key]
    return value


def _binding(original, current, context, normalize):
    if set(context) != {'request_id', 'approved_digest', 'account_id', 'source_campaign_id'}:
        raise ValueError('native thumbnail exact context required')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{8,120}', context['request_id']) or not re.fullmatch(r'[a-f0-9]{64}', context['approved_digest']):
        raise ValueError('native thumbnail request/seal invalid')
    for key in ('account_id', 'source_campaign_id'):
        if not isinstance(context[key], str) or not context[key].isdigit() or int(context[key]) == 0:
            raise ValueError('native thumbnail source identity invalid')
    for snapshot in (original, current):
        c = snapshot['campaign']
        if c['id'] != context['source_campaign_id'] or c['account_id'] != context['account_id']:
            raise ValueError('native thumbnail source identity mismatch')
    a, b = normalize(original), normalize(current)
    differences = _diff(a, b)
    entries = []
    for path in differences:
        if len(path) != 6 or path[0] not in EDGES or type(path[1]) is not int or path[2:] != SUFFIX:
            raise ValueError('source snapshot changed outside native thumbnail')
        edge, slot = path[:2]
        left, right = a[edge][slot], b[edge][slot]
        if len({x.get('id') for x in a[edge]}) != len(a[edge]):
            raise ValueError('native thumbnail duplicate source ad')
        identity = {'ad_id': left.get('id'), 'creative_id': left['creative'].get('id'), 'adset_id': left.get('adset_id')}
        if any(not isinstance(v, str) or not v.isdigit() or int(v) == 0 for v in identity.values()):
            raise ValueError('native thumbnail slot identity missing')
        if identity != {'ad_id': right.get('id'), 'creative_id': right['creative'].get('id'), 'adset_id': right.get('adset_id')} or identity['adset_id'] != a['adset']['id']:
            raise ValueError('native thumbnail slot identity changed')
        old, new = validate_url(_at(a, path)), validate_url(_at(b, path))
        entries.append({'edge': edge, 'slot': slot, **identity, 'original_url_sha256': hashlib.sha256(old.encode()).hexdigest(),
                        'current_url_sha256': hashlib.sha256(new.encode()).hexdigest()})
    return a, b, differences, {'schema': 1, 'mechanism': 'native-thumbnail-bytes-v1', 'context': copy.deepcopy(context),
                              'original_snapshot_sha256': digest(original), 'current_snapshot_sha256': digest(current), 'entries': entries}


def compare(original, current, *, context, normalize, fetcher=None):
    """Prove all native deltas, with no other delta. Inputs are never modified."""
    a, b, paths, receipt = _binding(original, current, context, normalize)
    fetcher = fetch_native if fetcher is None else fetcher
    cache = {}
    for path, entry in zip(paths, receipt['entries']):
        bodies = []
        for snapshot in (a, b):
            url = _at(snapshot, path)
            if url not in cache:
                body = fetcher(url)
                if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BYTES:
                    raise ValueError('native thumbnail bytes unavailable/oversize')
                cache[url] = body
            bodies.append(cache[url])
        if bodies[0] != bodies[1]:
            raise ValueError('native thumbnail bytes differ')
        entry.update(original_bytes=len(bodies[0]), current_bytes=len(bodies[1]),
                     original_bytes_sha256=hashlib.sha256(bodies[0]).hexdigest(), current_bytes_sha256=hashlib.sha256(bodies[1]).hexdigest())
        # In-memory comparison only; neither raw response is rewritten.
        _at(a, path[:-1])[path[-1]] = _at(b, path[:-1])[path[-1]] = {'native_thumbnail_bytes_sha256': entry['original_bytes_sha256']}
    if _diff(a, b):
        raise ValueError('source snapshot changed after native thumbnail proof')
    return receipt


def verify_receipt(receipt, *, expected_sha256, original, current, context, normalize):
    """Offline audit/replay validation only. Never used to authorize execute."""
    if digest(receipt) != expected_sha256:
        raise ValueError('native thumbnail receipt tampered')
    _, _, _, expected = _binding(original, current, context, normalize)
    if set(receipt) != set(expected):
        raise ValueError('native thumbnail receipt shape mismatch')
    for key in expected:
        if key != 'entries' and receipt[key] != expected[key]:
            raise ValueError('native thumbnail receipt binding mismatch')
    if len(receipt['entries']) != len(expected['entries']):
        raise ValueError('native thumbnail receipt coverage mismatch')
    fields = {'original_bytes', 'current_bytes', 'original_bytes_sha256', 'current_bytes_sha256'}
    for row, binding in zip(receipt['entries'], expected['entries']):
        if set(row) != set(binding) | fields or any(row[k] != v for k, v in binding.items()):
            raise ValueError('native thumbnail receipt slot/URL mismatch')
        if type(row['original_bytes']) is not int or not 0 < row['original_bytes'] <= MAX_BYTES or row['original_bytes'] != row['current_bytes']:
            raise ValueError('native thumbnail receipt size mismatch')
        if not isinstance(row['original_bytes_sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', row['original_bytes_sha256']) or row['original_bytes_sha256'] != row['current_bytes_sha256']:
            raise ValueError('native thumbnail receipt hash mismatch')
    return True
