#!/usr/bin/env python3
"""Public, credential-free GET transport for MGS editorial downloads.
DNS answers are validated and connections pinned, including every redirect.
No production policy, CTA validation, provider credential or campaign code here.
"""
from __future__ import annotations
import argparse
import contextlib
import http.client
import importlib.util
import io
import ipaddress
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import zlib
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
MAX_REDIRECTS = 8
PUBLIC_HEADERS = {'user-agent', 'accept', 'accept-language', 'cache-control', 'range'}

class PublicFetchError(ValueError):
    pass

def _public_ip(value):
    ip = ipaddress.ip_address(value)
    if not ip.is_global or ip.is_multicast:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _public_ip(str(ip.ipv4_mapped))
        if ip.sixtofour is not None or ip.teredo is not None:
            return False
        if ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48'):
            return False
    return True

def validate_public_url(url, *, resolver=None):
    if not isinstance(url, str) or '\\' in url or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise PublicFetchError('URL syntax denied')
    try:
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ('https', 'http') or not p.hostname or p.username is not None or p.password is not None:
            raise ValueError('unsupported public URL')
        host = p.hostname.encode('idna').decode('ascii')
        port = p.port or (443 if p.scheme == 'https' else 80)
        if port not in (80, 443):
            raise ValueError('unsupported public port')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not _public_ip(host):
                raise ValueError('non-public literal')
        rows = (resolver or socket.getaddrinfo)(host, port, type=socket.SOCK_STREAM)
        ips = sorted({row[4][0] for row in rows})
        if not ips or any(not _public_ip(ip) for ip in ips):
            raise ValueError('non-public DNS answer')
        path = urllib.parse.urlunsplit(('', '', p.path or '/', p.query, ''))
        # Request paths must be ASCII; preserve escaped URLs and query values.
        path = urllib.parse.quote(path, safe="/%?=&:+,;@!$'()*[]~-._")
        return {'scheme': p.scheme, 'host': host, 'port': port, 'ips': ips, 'path': path}
    except (OSError, UnicodeError, ValueError) as e:
        raise PublicFetchError('URL destination denied') from e

class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, ip, timeout):
        self._tls_context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=self._tls_context)
        self._public_ip = ip
    def connect(self):
        raw = socket.create_connection((self._public_ip, self.port), timeout=self.timeout)
        try:
            self.sock = self._tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise

class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self._public_ip = ip
    def connect(self):
        self.sock = socket.create_connection((self._public_ip, self.port), timeout=self.timeout)

@dataclass
class PublicResponse:
    status_code: int
    content: bytes
    url: str
    headers: dict
    @property
    def text(self):
        content_type = self.headers.get('content-type', '')
        encoding = 'utf-8'
        if 'charset=' in content_type.lower():
            encoding = content_type.lower().split('charset=', 1)[1].split(';', 1)[0].strip(' \"\'')
        try:
            return self.content.decode(encoding, errors='replace')
        except LookupError:
            return self.content.decode('utf-8', errors='replace')
    def json(self):
        return json.loads(self.text)

def _decode_body(body, encoding, max_bytes):
    encoding = encoding.strip().lower()
    if encoding in ('', 'identity'):
        return body
    if encoding not in ('gzip', 'deflate'):
        raise PublicFetchError('unsupported response encoding')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == 'gzip' else zlib.MAX_WBITS)
    decoded = decoder.decompress(body, max_bytes + 1)
    if len(decoded) > max_bytes or decoder.unconsumed_tail or not decoder.eof:
        raise PublicFetchError('decoded response size or integrity denied')
    return decoded

def public_response(url, *, timeout=25, headers=None, max_bytes=MAX_BYTES, method='GET', **kwargs):
    if kwargs:
        raise PublicFetchError('unsupported public transport arguments')
    if method not in ('GET', 'HEAD') or not 0 < max_bytes <= MAX_BYTES or timeout <= 0:
        raise PublicFetchError('public transport bounds denied')
    clean_headers = {}
    for key, value in (headers or {}).items():
        if key.lower() not in PUBLIC_HEADERS or '\r' in str(value) or '\n' in str(value):
            raise PublicFetchError('public transport header denied')
        clean_headers[key] = value
    clean_headers.setdefault('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) MGS-Public-Fetch/1.0')
    clean_headers['Accept-Encoding'] = 'identity'
    current = url
    deadline = time.monotonic() + timeout
    seen = set()
    for hop in range(MAX_REDIRECTS + 1):
        if current in seen:
            raise PublicFetchError('redirect loop denied')
        seen.add(current)
        target = validate_public_url(current)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PublicFetchError('public fetch deadline exceeded')
        typ = _PinnedHTTPS if target['scheme'] == 'https' else _PinnedHTTP
        con = None
        response = None
        for ip in target['ips']:
            con = typ(target['host'], target['port'], ip, max(0.1, remaining))
            try:
                con.request(method, target['path'], headers=clean_headers)
                response = con.getresponse()
                break
            except (OSError, http.client.HTTPException):
                con.close()
                if ip == target['ips'][-1]:
                    raise PublicFetchError('public connection failed') from None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PublicFetchError('public fetch deadline exceeded')
        assert con is not None and response is not None
        try:
            status = response.status
            if status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location or hop == MAX_REDIRECTS:
                    raise PublicFetchError('redirect destination or limit denied')
                current = urllib.parse.urljoin(current, location)
                continue
            length = response.getheader('Content-Length')
            if length and (not length.isdigit() or int(length) > max_bytes):
                raise PublicFetchError('response size denied')
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise PublicFetchError('response size denied')
            body = _decode_body(body, response.getheader('Content-Encoding') or '', max_bytes)
            response_headers = {k.lower(): v for k, v in response.getheaders()
                                if k.lower() not in ('content-length', 'content-encoding', 'transfer-encoding', 'set-cookie', 'connection')}
            return PublicResponse(status, body, current, response_headers)
        finally:
            con.close()
    raise PublicFetchError('redirect limit denied')

@contextlib.contextmanager
def public_urlopen(request, *, timeout=25):
    if hasattr(request, 'full_url'):
        if request.data is not None or request.get_method() not in ('GET', 'HEAD'):
            raise PublicFetchError('public request method denied')
        url, headers, method = request.full_url, dict(request.header_items()), request.get_method()
    else:
        url, headers, method = str(request), None, 'GET'
    r = public_response(url, timeout=timeout, headers=headers, method=method)
    if r.status_code >= 400:
        raise urllib.error.HTTPError(url, r.status_code, 'public fetch HTTP error', None, None)
    stream = io.BytesIO(r.content)
    stream.status = r.status_code
    stream.headers = r.headers
    stream.geturl = lambda: r.url
    try:
        yield stream
    finally:
        stream.close()

def public_urlretrieve(url, filename, *, timeout=30):
    r = public_response(url, timeout=timeout)
    if r.status_code >= 400:
        raise PublicFetchError('public image HTTP error')
    Path(filename).write_bytes(r.content)
    return filename, r.headers

def guard_browser_context(context):
    """Route public browser requests through the pinned transport, not browser DNS."""
    def handle(route):
        request = route.request
        if urllib.parse.urlsplit(request.url).scheme in ('data', 'blob', 'about'):
            route.continue_()
            return
        try:
            headers = {k: v for k, v in request.headers.items() if k.lower() in PUBLIC_HEADERS}
            r = public_response(request.url, timeout=25, headers=headers, method=request.method)
            # Browser receives a same-origin response but never connects to that destination itself.
            route.fulfill(status=r.status_code, headers=r.headers, body=r.content)
        except Exception:
            route.abort('blockedbyclient')
    if not hasattr(context, 'route_web_socket'):
        raise PublicFetchError('browser lacks required WebSocket interception')
    # Interception does not connect upstream unless connect_to_server() is called.
    # Do not synchronously call ws.close() inside the sync dispatch callback.
    context.route_web_socket('**/*', lambda ws: None)
    context.route('**/*', handle)
    return context

def run_bing_guarded(script, args):
    """Keep Bing ranking/normalization code intact; bind only its public download boundary."""
    from importlib import import_module
    Browser = import_module("playwright.sync_api").Browser
    original = Browser.new_context
    def guarded_new_context(self, *a, **kw):
        kw['service_workers'] = 'block'
        return guard_browser_context(original(self, *a, **kw))
    Browser.new_context = guarded_new_context
    spec = importlib.util.spec_from_file_location('mgs_bing_public_guard', script)
    if spec is None or spec.loader is None:
        raise PublicFetchError('Bing script loader unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def download(url, path):
        r = public_response(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'})
        if r.status_code >= 400:
            raise PublicFetchError('public Bing image HTTP error')
        Path(path).write_bytes(r.content)
        return len(r.content)
    module.download = download
    sys.argv = [str(script), *args]
    module.main()

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    download = sub.add_parser('download'); download.add_argument('url'); download.add_argument('path')
    text = sub.add_parser('text'); text.add_argument('url')
    sub.add_parser('validate').add_argument('url')
    bing = sub.add_parser('bing'); bing.add_argument('script'); bing.add_argument('args', nargs='*')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            validate_public_url(args.url)
        elif args.command == 'bing':
            run_bing_guarded(args.script, args.args)
        else:
            r = public_response(args.url)
            if args.command == 'text':
                sys.stdout.write(r.text + '\nHTTP_STATUS:' + str(r.status_code))
            elif r.status_code >= 400:
                raise PublicFetchError('public image HTTP error')
            else:
                Path(args.path).write_bytes(r.content)
    except Exception as e:
        # No remote bodies or potentially credential-bearing URL in failure receipts.
        print('Public download denied or failed: ' + type(e).__name__, file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
