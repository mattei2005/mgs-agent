#!/usr/bin/env python3
"""Common helpers for Ares Meta Ads operations. Never print tokens."""
from __future__ import annotations
import fcntl, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
GRAPH_VERSION = os.environ.get('ARES_META_GRAPH_VERSION', 'v20.0')
TOKEN_ITEM_DEFAULT = 'Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN'
TOKEN_CACHE_PATH = Path(os.environ.get('ARES_META_TOKEN_CACHE_PATH', '/root/.cache/mgs/ares-meta-token.json'))
TOKEN_CACHE_MAX_AGE_SECONDS = int(os.environ.get('ARES_META_TOKEN_CACHE_MAX_AGE_SECONDS', '604800'))
RATE_LIMIT_CODES = {4, 17, 32, 613, 80004}
RATE_LIMIT_MESSAGE_PATTERNS = (
    'rate limit',
    'too many calls',
    'reduce the amount of data',
    'temporarily blocked',
)
MIN_INTERVAL_SECONDS = float(os.environ.get('ARES_META_MIN_INTERVAL_SECONDS', '0.75'))
RATE_LIMIT_MAX_TOTAL_SLEEP = int(os.environ.get('ARES_META_RATE_LIMIT_MAX_TOTAL_SLEEP', '600'))
RATE_LIMIT_INITIAL_SLEEP = int(os.environ.get('ARES_META_RATE_LIMIT_INITIAL_SLEEP', '30'))
THROTTLE_STATE_PATH = BASE / 'cache' / 'meta-api-throttle-state.json'

def load_json(path):
    return json.loads(Path(path).read_text())

def account_config(account_id):
    return load_json(BASE / 'accounts' / f'{account_id}.json')['accounts'][0]

def get_token_from_1password(item_name=TOKEN_ITEM_DEFAULT):
    # Source /root/mgs-agent/.env for OP_SERVICE_ACCOUNT_TOKEN without exposing it.
    field_candidates = ['credential', 'password', 'token', 'api key', 'access token']
    for field in field_candidates:
        cmd = f"set -a; [ -f /root/mgs-agent/.env ] && . /root/mgs-agent/.env; set +a; op item get {shell_quote(item_name)} --vault {shell_quote(os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'))} --fields {shell_quote(field)} --reveal 2>/dev/null"
        res = subprocess.run(['bash','-lc',cmd], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        token = res.stdout.strip()
        if res.returncode == 0 and token:
            return token, field
    # fallback: JSON and common field labels
    cmd = f"set -a; [ -f /root/mgs-agent/.env ] && . /root/mgs-agent/.env; set +a; op item get {shell_quote(item_name)} --vault {shell_quote(os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'))} --format json --reveal"
    res = subprocess.run(['bash','-lc',cmd], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if res.returncode != 0:
        raise RuntimeError('1Password item not readable or not found')
    data=json.loads(res.stdout)
    for field in data.get('fields',[]):
        label=(field.get('label') or field.get('id') or '').lower()
        val=field.get('value')
        if val and any(k in label for k in ['token','password','credential','api key','access']):
            return val, field.get('label') or field.get('id')
    raise RuntimeError('1Password item found but token field was not identified')

def shell_quote(s):
    import shlex
    return shlex.quote(str(s))

def _throttle_before_request():
    """Cross-process soft throttle to avoid Meta API bursts."""
    if MIN_INTERVAL_SECONDS <= 0:
        return
    THROTTLE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with THROTTLE_STATE_PATH.open('a+') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            state = json.loads(fh.read() or '{}')
        except Exception:
            state = {}
        now = time.monotonic()
        last = float(state.get('last_request_monotonic') or 0)
        # time.monotonic() is process/boot-local. If the VPS rebooted after the
        # throttle state was persisted, a previous high monotonic value can be
        # greater than the current boot's value and would otherwise sleep for
        # days while holding the cross-process lock.
        if last > now:
            last = 0
        wait = MIN_INTERVAL_SECONDS - (now - last)
        if 0 < wait <= MIN_INTERVAL_SECONDS:
            time.sleep(wait)
            now = time.monotonic()
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps({'last_request_monotonic': now, 'min_interval_seconds': MIN_INTERVAL_SECONDS}))
        fh.flush()
        fcntl.flock(fh, fcntl.LOCK_UN)

def is_rate_limit_response(status, payload):
    err = payload.get('error') if isinstance(payload, dict) else None
    if status == 429:
        return True
    if isinstance(err, dict):
        code = err.get('code')
        message = str(err.get('message') or '').lower()
        if code in RATE_LIMIT_CODES:
            return True
        if any(pattern in message for pattern in RATE_LIMIT_MESSAGE_PATTERNS):
            return True
    return False

def _graph_get_once(path, token, params=None):
    params=dict(params or {})
    params['access_token']=token
    url=f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={'User-Agent':'mgs-ares-meta-ads/0.1'})
    try:
        _throttle_before_request()
        with urllib.request.urlopen(req, timeout=45) as resp:
            body=resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(body), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        try: payload=json.loads(body)
        except Exception: payload={'raw':body[:1000]}
        return e.code, payload, dict(e.headers)

def graph_get(path, token, params=None):
    """GET Meta Graph with burst throttling and bounded rate-limit backoff.

    Backoff sequence starts at 30s and doubles, capped at 10 minutes total
    sleep. If Meta still rate-limits after that, return a structured error so
    the caller/agent can stop and alert the current channel.
    """
    total_sleep = 0
    next_sleep = RATE_LIMIT_INITIAL_SLEEP
    attempts = 0
    while True:
        attempts += 1
        status, payload, headers = _graph_get_once(path, token, params)
        if not is_rate_limit_response(status, payload):
            return status, payload, headers
        if total_sleep >= RATE_LIMIT_MAX_TOTAL_SLEEP:
            payload = {
                'error': {
                    'message': 'Meta API rate limit persisted after bounded backoff; stopped to avoid hammering the API.',
                    'type': 'AresRateLimitExceeded',
                    'code': 'ARES_RATE_LIMIT_EXHAUSTED',
                    'attempts': attempts,
                    'total_sleep_seconds': total_sleep,
                    'last_meta_error': safe_meta_error(payload),
                }
            }
            return status, payload, headers
        sleep_for = min(next_sleep, RATE_LIMIT_MAX_TOTAL_SLEEP - total_sleep)
        time.sleep(sleep_for)
        total_sleep += sleep_for
        next_sleep *= 2

def safe_meta_error(payload):
    err=payload.get('error') if isinstance(payload,dict) else None
    if not err:
        return payload
    return {k:err.get(k) for k in ['message','type','code','error_subcode','fbtrace_id'] if k in err}
