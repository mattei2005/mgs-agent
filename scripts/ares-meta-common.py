#!/usr/bin/env python3
"""Common helpers for Ares Meta Ads operations. Never print tokens."""
from __future__ import annotations
import fcntl, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
GRAPH_VERSION = os.environ.get('ARES_META_GRAPH_VERSION', 'v20.0')
TOKEN_ITEM_DEFAULT = 'Token Meta API'
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

def graph_get(path, token, params=None):
    params=dict(params or {})
    params['access_token']=token
    url=f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={'User-Agent':'mgs-ares-meta-ads/0.1'})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body=resp.read().decode('utf-8', 'replace')
            return resp.status, json.loads(body), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        try: payload=json.loads(body)
        except Exception: payload={'raw':body[:1000]}
        return e.code, payload, dict(e.headers)

def safe_meta_error(payload):
    err=payload.get('error') if isinstance(payload,dict) else None
    if not err:
        return payload
    return {k:err.get(k) for k in ['message','type','code','error_subcode','fbtrace_id'] if k in err}
