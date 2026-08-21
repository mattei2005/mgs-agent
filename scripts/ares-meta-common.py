#!/usr/bin/env python3
"""Common helpers for Ares Meta Ads operations. Never print tokens."""
from __future__ import annotations
import fcntl, json, math, os, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
GRAPH_VERSION = os.environ.get('ARES_META_GRAPH_VERSION', 'v20.0')
TOKEN_ITEM_DEFAULT = 'Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN'
TOKEN_CACHE_PATH = Path(os.environ.get('ARES_META_TOKEN_CACHE_PATH', '/root/.cache/mgs/ares-meta-token.json'))
TOKEN_CACHE_LOCK_PATH = Path(os.environ.get('ARES_META_TOKEN_CACHE_LOCK_PATH', f'{TOKEN_CACHE_PATH}.lock'))
TOKEN_CACHE_REFRESH_SECONDS = int(os.environ.get('ARES_META_TOKEN_CACHE_REFRESH_SECONDS', '86400'))
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
BUSINESS_USAGE_SOFT_LIMIT_PERCENT = float(os.environ.get('ARES_META_BUSINESS_USAGE_SOFT_LIMIT_PERCENT', '80'))
BUSINESS_USAGE_SOFT_LIMIT_WAIT_SECONDS = int(os.environ.get('ARES_META_BUSINESS_USAGE_SOFT_LIMIT_WAIT_SECONDS', '60'))
BUSINESS_USAGE_MAX_INLINE_WAIT_SECONDS = int(os.environ.get('ARES_META_BUSINESS_USAGE_MAX_INLINE_WAIT_SECONDS', str(RATE_LIMIT_MAX_TOTAL_SLEEP)))
AD_ACCOUNT_USAGE_SOFT_LIMIT_PERCENT = float(os.environ.get('ARES_META_AD_ACCOUNT_USAGE_SOFT_LIMIT_PERCENT', '75'))
DEVELOPMENT_ACCESS_SCORE_MAX = 60
STANDARD_ACCESS_SCORE_MAX = 9000
DEFAULT_AD_ACCOUNT_RESET_SECONDS = 300
LOCAL_SCORE_WINDOW_SECONDS = 300
LOCAL_SCORE_MAX_ENTRIES = 512
TRANSIENT_5XX_RETRY_SECONDS = 10
THROTTLE_STATE_PATH = BASE / 'cache' / 'meta-api-throttle-state.json'
BUSINESS_USAGE_HEADER = 'x-business-use-case-usage'
AD_ACCOUNT_USAGE_HEADER = 'x-ad-account-usage'


class AresMetaUsageBlocked(RuntimeError):
    def __init__(self, retry_after_seconds, reason='business_usage_soft_limit'):
        self.retry_after_seconds = max(0, int(retry_after_seconds))
        self.reason = str(reason)
        super().__init__(f'Meta API blocked by {self.reason}; retry after {self.retry_after_seconds}s')

def load_json(path):
    return json.loads(Path(path).read_text())

def account_config(account_id):
    return load_json(BASE / 'accounts' / f'{account_id}.json')['accounts'][0]

def _identify_token_field(data):
    for field in data.get('fields', []):
        label = (field.get('label') or field.get('id') or '').lower()
        val = field.get('value')
        if val and any(k in label for k in ['token', 'password', 'credential', 'api key', 'access']):
            return val, field.get('label') or field.get('id')
    raise RuntimeError('1Password item found but token field was not identified')


def _write_token_cache(item_name, token, field):
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(TOKEN_CACHE_PATH.parent, 0o700)
    payload = json.dumps({
        'item': item_name,
        'field': field,
        'token': token,
        'cached_at': int(time.time()),
    }, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(prefix='.ares-meta-token-', dir=TOKEN_CACHE_PATH.parent)
    tmp = Path(tmp_name)
    os.fchmod(fd, 0o600)
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(payload + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, TOKEN_CACHE_PATH)
        os.chmod(TOKEN_CACHE_PATH, 0o600)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _read_token_cache(item_name, max_age_seconds=TOKEN_CACHE_MAX_AGE_SECONDS):
    try:
        st = TOKEN_CACHE_PATH.stat()
        if st.st_mode & 0o077:
            return None
        data = json.loads(TOKEN_CACHE_PATH.read_text())
        age = time.time() - float(data.get('cached_at') or 0)
        token = str(data.get('token') or '').strip()
        if data.get('item') != item_name or not token or age < 0 or age > max_age_seconds:
            return None
        return token, str(data.get('field') or 'cached'), age
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _open_token_cache_lock():
    TOKEN_CACHE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(TOKEN_CACHE_LOCK_PATH.parent, 0o700)
    fd = os.open(TOKEN_CACHE_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'r+')


def _fetch_token_from_1password(item_name):
    # Exactly one 1Password request per refresh. The old field-by-field loop made
    # up to six requests and amplified service-account throttling across crons.
    cmd = f"set -a; [ -f /root/mgs-agent/.env ] && . /root/mgs-agent/.env; set +a; op item get {shell_quote(item_name)} --vault {shell_quote(os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'))} --format json --reveal"
    res = subprocess.run(['bash', '-lc', cmd], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if res.returncode == 0:
        data = json.loads(res.stdout)
        token, field = _identify_token_field(data)
        _write_token_cache(item_name, token, field)
        return token, field
    return None, res.stderr or ''


def get_token_from_1password(item_name=TOKEN_ITEM_DEFAULT, force_refresh=False):
    """Return a Meta token without calling 1Password on every process run.

    A fresh protected cache is the normal path. Refreshes are serialized across
    cron processes and double-checked after locking to avoid a request stampede.
    If refresh fails, a bounded older cache may be used until its maximum age.
    """
    if not force_refresh:
        cached = _read_token_cache(item_name, TOKEN_CACHE_REFRESH_SECONDS)
        if cached:
            token, field, age = cached
            return token, f'{field} (cache {int(age)}s)'

    with _open_token_cache_lock() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not force_refresh:
            cached = _read_token_cache(item_name, TOKEN_CACHE_REFRESH_SECONDS)
            if cached:
                token, field, age = cached
                return token, f'{field} (cache {int(age)}s)'

        token, field_or_error = _fetch_token_from_1password(item_name)
        if token:
            return token, field_or_error

        if not force_refresh:
            cached = _read_token_cache(item_name, TOKEN_CACHE_MAX_AGE_SECONDS)
            if cached:
                token, field, age = cached
                return token, f'{field} (stale-cache {int(age)}s)'

        error = field_or_error.lower()
        if 'rate-limit' in error or 'rate limit' in error or 'too many requests' in error:
            raise RuntimeError('1Password rate-limited and no valid local token cache is available')
        raise RuntimeError('1Password item not readable and no valid local token cache is available')


def invalidate_token_cache(item_name=TOKEN_ITEM_DEFAULT, rejected_token=None):
    """Invalidate only the matching cached credential; never print its value."""
    with _open_token_cache_lock() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            data = json.loads(TOKEN_CACHE_PATH.read_text())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False
        if data.get('item') != item_name:
            return False
        if rejected_token is not None and data.get('token') != rejected_token:
            return False
        try:
            TOKEN_CACHE_PATH.unlink()
            return True
        except FileNotFoundError:
            return False

def shell_quote(s):
    import shlex
    return shlex.quote(str(s))

def _header_value(headers, name):
    wanted = str(name).lower()
    for key, value in dict(headers or {}).items():
        if str(key).lower() == wanted:
            return value
    return None


def _as_number(value, default=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else float(default)
    except (TypeError, ValueError):
        return float(default)


def parse_business_usage_headers(headers):
    """Parse Meta X-Business-Use-Case-Usage without trusting its shape."""
    raw = _header_value(headers, BUSINESS_USAGE_HEADER)
    empty = {
        'entry_count': 0,
        'entries': [],
        'max_usage_pct': 0.0,
        'limiting_metric': None,
        'estimated_time_to_regain_access_minutes': 0.0,
    }
    if raw in (None, ''):
        return empty
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty
    groups = []
    if isinstance(data, dict):
        for business_id, value in data.items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, dict):
                    groups.append((str(business_id), item))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                groups.append((str(item.get('business_id') or ''), item))
    entries = []
    max_usage = 0.0
    limiting_metric = None
    estimated_minutes = 0.0
    for business_id, item in groups:
        normalized = {
            'business_id': business_id,
            'type': item.get('type'),
            'call_count': _as_number(item.get('call_count')),
            'total_cputime': _as_number(item.get('total_cputime')),
            'total_time': _as_number(item.get('total_time')),
            'estimated_time_to_regain_access': _as_number(item.get('estimated_time_to_regain_access')),
            'ads_api_access_tier': item.get('ads_api_access_tier'),
        }
        if len(entries) < 32:
            entries.append(normalized)
        estimated_minutes = max(estimated_minutes, normalized['estimated_time_to_regain_access'])
        for metric in ('call_count', 'total_cputime', 'total_time'):
            value = normalized[metric]
            if value > max_usage:
                max_usage = value
                limiting_metric = metric
    return {
        'entry_count': len(groups),
        'entries': entries,
        'max_usage_pct': max_usage,
        'limiting_metric': limiting_metric,
        'estimated_time_to_regain_access_minutes': estimated_minutes,
    }


def parse_ad_account_usage_headers(headers):
    """Parse Meta X-Ad-Account-Usage independently from BUC usage."""
    empty = {
        'present': False,
        'acc_id_util_pct': 0.0,
        'reset_time_duration_seconds': 0,
        'ads_api_access_tier': None,
    }
    raw = _header_value(headers, AD_ACCOUNT_USAGE_HEADER)
    if raw in (None, ''):
        return empty
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty
    if not isinstance(data, dict):
        return empty
    return {
        'present': True,
        'acc_id_util_pct': max(0.0, _as_number(data.get('acc_id_util_pct'))),
        'reset_time_duration_seconds': max(0, int(math.ceil(_as_number(data.get('reset_time_duration'))))),
        'ads_api_access_tier': str(data.get('ads_api_access_tier') or '').strip() or None,
    }


def marketing_access_tier(ad_account_usage=None, business_usage=None):
    tier = str((ad_account_usage or {}).get('ads_api_access_tier') or '').strip()
    if tier:
        return tier
    for entry in (business_usage or {}).get('entries') or []:
        tier = str(entry.get('ads_api_access_tier') or '').strip()
        if tier:
            return tier
    return None


def ad_account_usage_decision(usage, now_epoch=None):
    now_epoch = time.time() if now_epoch is None else float(now_epoch)
    present = bool((usage or {}).get('present'))
    util_pct = _as_number((usage or {}).get('acc_id_util_pct'))
    soft_limited = present and util_pct >= AD_ACCOUNT_USAGE_SOFT_LIMIT_PERCENT
    reset_seconds = max(0, int((usage or {}).get('reset_time_duration_seconds') or 0))
    wait_seconds = reset_seconds if soft_limited and reset_seconds > 0 else (DEFAULT_AD_ACCOUNT_RESET_SECONDS if soft_limited else 0)
    return {
        'soft_limited': soft_limited,
        'wait_seconds': wait_seconds,
        'blocked_until_epoch': now_epoch + wait_seconds,
        'acc_id_util_pct': util_pct,
        'ads_api_access_tier': (usage or {}).get('ads_api_access_tier'),
    }


def ads_management_score_budget(ad_account_usage, business_usage, *, read_calls, write_calls, reserve_points=5, local_score=None):
    """Project logical Marketing API score; Graph batch children count separately."""
    tier = marketing_access_tier(ad_account_usage, business_usage)
    if tier == 'development_access':
        maximum = DEVELOPMENT_ACCESS_SCORE_MAX
    elif tier == 'standard_access':
        maximum = STANDARD_ACCESS_SCORE_MAX
    else:
        maximum = None
    header_present = bool((ad_account_usage or {}).get('present'))
    util_pct = max(0.0, _as_number((ad_account_usage or {}).get('acc_id_util_pct')))
    local_ready = bool((local_score or {}).get('ready'))
    projected = max(0, int(read_calls)) + 3 * max(0, int(write_calls)) + max(0, int(reserve_points))
    if maximum is not None and header_present:
        used = int(math.ceil(maximum * min(util_pct, 100.0) / 100.0))
        available = max(0, maximum - used)
        measurement_source = 'x_ad_account_usage'
    elif maximum is not None and local_ready:
        used = max(0, int((local_score or {}).get('points') or 0))
        available = max(0, maximum - used)
        measurement_source = 'local_rolling_ledger'
    else:
        used = None
        available = None
        measurement_source = None
    usage_soft_limited = header_present and util_pct >= AD_ACCOUNT_USAGE_SOFT_LIMIT_PERCENT
    allowed = bool(maximum is not None and available is not None and projected <= available and not usage_soft_limited)
    if maximum is None:
        reason = 'unknown_access_tier'
    elif not header_present and not local_ready:
        reason = 'local_score_warmup' if local_score else 'missing_x_ad_account_usage'
    elif usage_soft_limited:
        reason = 'ad_account_usage_soft_limit'
    elif available is not None and projected > available:
        reason = 'projected_score_exceeds_available'
    else:
        reason = 'within_budget'
    return {
        'allowed': allowed,
        'reason': reason,
        'tier': tier,
        'header_present': header_present,
        'measurement_source': measurement_source,
        'maximum_score': maximum,
        'estimated_used_score': used,
        'estimated_available_score': available,
        'projected_score': projected,
        'read_calls': max(0, int(read_calls)),
        'write_calls': max(0, int(write_calls)),
        'reserve_points': max(0, int(reserve_points)),
        'acc_id_util_pct': util_pct,
        'local_score_ready': local_ready,
        'local_score_warmup_remaining_seconds': max(0, int((local_score or {}).get('warmup_remaining_seconds') or 0)),
    }


def business_usage_decision(usage, now_epoch=None):
    now_epoch = time.time() if now_epoch is None else float(now_epoch)
    max_usage = _as_number((usage or {}).get('max_usage_pct'))
    estimated_minutes = _as_number((usage or {}).get('estimated_time_to_regain_access_minutes'))
    soft_limited = max_usage >= BUSINESS_USAGE_SOFT_LIMIT_PERCENT
    wait_seconds = 0
    if soft_limited:
        wait_seconds = max(1, int(math.ceil(estimated_minutes * 60))) if estimated_minutes > 0 else BUSINESS_USAGE_SOFT_LIMIT_WAIT_SECONDS
    return {
        'soft_limited': soft_limited,
        'wait_seconds': max(0, wait_seconds),
        'blocked_until_epoch': now_epoch + max(0, wait_seconds),
        'max_usage_pct': max_usage,
        'limiting_metric': (usage or {}).get('limiting_metric'),
    }


def retry_wait_seconds(status, payload, headers, attempt=1):
    err = payload.get('error') if isinstance(payload, dict) else None
    code = err.get('code') if isinstance(err, dict) else None
    subcode = err.get('error_subcode') if isinstance(err, dict) else None
    if status == 429 or code in RATE_LIMIT_CODES:
        ad_usage = parse_ad_account_usage_headers(headers)
        if ad_usage['reset_time_duration_seconds'] > 0:
            return ad_usage['reset_time_duration_seconds']
        usage = parse_business_usage_headers(headers)
        estimated_minutes = _as_number(usage.get('estimated_time_to_regain_access_minutes'))
        if estimated_minutes > 0:
            return max(1, int(math.ceil(estimated_minutes * 60)))
        if subcode == 2446079 or (code == 17 and marketing_access_tier(ad_usage, usage) == 'development_access'):
            return DEFAULT_AD_ACCOUNT_RESET_SECONDS
        return min(RATE_LIMIT_INITIAL_SLEEP * (2 ** max(0, int(attempt) - 1)), RATE_LIMIT_MAX_TOTAL_SLEEP)
    if isinstance(status, int) and 500 <= status <= 599:
        return TRANSIENT_5XX_RETRY_SECONDS
    return None


def _open_throttle_state():
    THROTTLE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(THROTTLE_STATE_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, 'r+')


def _read_state_locked(fh):
    fh.seek(0)
    try:
        state = json.loads(fh.read() or '{}')
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _write_state_locked(fh, state):
    fh.seek(0)
    fh.truncate()
    fh.write(json.dumps(state, ensure_ascii=False, sort_keys=True))
    fh.flush()
    os.fsync(fh.fileno())


def _update_local_score_ledger(state, now_epoch, logical_points, business_usage, ad_account_usage):
    ads_management = bool(ad_account_usage.get('present')) or any(
        str(entry.get('type') or '') == 'ads_management'
        for entry in business_usage.get('entries') or []
    )
    ledger = state.get('local_score') if isinstance(state.get('local_score'), dict) else {}
    raw_events = ledger.get('events')
    events = raw_events if isinstance(raw_events, list) else []
    cutoff = now_epoch - LOCAL_SCORE_WINDOW_SECONDS
    cleaned = []
    for event in events:
        if not isinstance(event, dict):
            continue
        at = _as_number(event.get('at'), default=-1)
        points = max(0, int(_as_number(event.get('points'))))
        if at >= cutoff and points:
            cleaned.append({'at': at, 'points': points})
    if ads_management and int(logical_points or 0) > 0:
        cleaned.append({'at': now_epoch, 'points': max(0, int(logical_points))})
    cleaned = cleaned[-LOCAL_SCORE_MAX_ENTRIES:]
    started_at = _as_number(ledger.get('window_started_at_epoch'))
    if ads_management and started_at <= 0:
        started_at = now_epoch
    warmup_remaining = max(0, int(math.ceil((started_at + LOCAL_SCORE_WINDOW_SECONDS) - now_epoch))) if started_at > 0 else LOCAL_SCORE_WINDOW_SECONDS
    state['local_score'] = {
        'window_seconds': LOCAL_SCORE_WINDOW_SECONDS,
        'window_started_at_epoch': started_at or None,
        'ready': bool(started_at > 0 and warmup_remaining == 0),
        'warmup_remaining_seconds': warmup_remaining,
        'points': sum(event['points'] for event in cleaned),
        'events': cleaned,
        'updated_at_epoch': now_epoch,
    }


def record_response_usage(headers, status, payload, now_epoch=None, logical_points=0):
    """Persist independent BUC and ad-account usage/cooldown from every response."""
    now_epoch = time.time() if now_epoch is None else float(now_epoch)
    usage = parse_business_usage_headers(headers)
    decision = business_usage_decision(usage, now_epoch=now_epoch)
    ad_usage = parse_ad_account_usage_headers(headers)
    ad_decision = ad_account_usage_decision(ad_usage, now_epoch=now_epoch)
    err = payload.get('error') if isinstance(payload, dict) else None
    error_code = err.get('code') if isinstance(err, dict) else None
    error_subcode = err.get('error_subcode') if isinstance(err, dict) else None
    with _open_throttle_state() as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        state = _read_state_locked(fh)
        if usage['entry_count']:
            state['business_usage'] = usage
            state['usage_updated_at_epoch'] = now_epoch
        if ad_usage['present']:
            state['ad_account_usage'] = ad_usage
            state['ad_account_usage_updated_at_epoch'] = now_epoch
        tier = marketing_access_tier(ad_usage, usage)
        if tier:
            state['ads_api_access_tier'] = tier
        state['last_response_status'] = status
        state['last_error_code'] = error_code
        state['last_error_subcode'] = error_subcode
        current_block = _as_number(state.get('blocked_until_epoch'))
        blocked_until = current_block
        reason = state.get('block_reason')
        if decision['soft_limited']:
            blocked_until = max(blocked_until, decision['blocked_until_epoch'])
            reason = 'business_usage_soft_limit'
        if ad_decision['soft_limited']:
            blocked_until = max(blocked_until, ad_decision['blocked_until_epoch'])
            reason = 'ad_account_usage_soft_limit'
        rate_wait = retry_wait_seconds(status, payload, headers, attempt=1)
        if (status == 429 or error_code in RATE_LIMIT_CODES) and rate_wait is not None:
            blocked_until = max(blocked_until, now_epoch + rate_wait)
            reason = 'meta_rate_limit'
        fresh_usage = bool(usage['entry_count'] or ad_usage['present'])
        if fresh_usage and not decision['soft_limited'] and not ad_decision['soft_limited'] and status < 400 and current_block <= now_epoch:
            blocked_until = 0
            reason = None
        state['blocked_until_epoch'] = blocked_until
        state['block_reason'] = reason
        state['soft_limit_percent'] = BUSINESS_USAGE_SOFT_LIMIT_PERCENT
        state['ad_account_soft_limit_percent'] = AD_ACCOUNT_USAGE_SOFT_LIMIT_PERCENT
        _write_state_locked(fh, state)
        fcntl.flock(fh, fcntl.LOCK_UN)
    return state


def read_throttle_state():
    if not THROTTLE_STATE_PATH.exists():
        return {}
    with _open_throttle_state() as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        state = _read_state_locked(fh)
        fcntl.flock(fh, fcntl.LOCK_UN)
    return state


def _wait_before_request_from_state(now_epoch=None):
    fixed_now = None if now_epoch is None else float(now_epoch)
    total_wait = 0
    while True:
        current = time.time() if fixed_now is None else fixed_now
        if not THROTTLE_STATE_PATH.exists():
            return total_wait
        with _open_throttle_state() as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = _read_state_locked(fh)
            blocked_until = _as_number(state.get('blocked_until_epoch'))
            remaining = max(0, int(math.ceil(blocked_until - current)))
            reason = state.get('block_reason') or 'business_usage_soft_limit'
            if remaining <= 0 and blocked_until and blocked_until <= current:
                state['blocked_until_epoch'] = 0
                state['block_reason'] = None
                _write_state_locked(fh, state)
            fcntl.flock(fh, fcntl.LOCK_UN)
        if remaining <= 0:
            return total_wait
        if remaining > BUSINESS_USAGE_MAX_INLINE_WAIT_SECONDS:
            raise AresMetaUsageBlocked(remaining, reason=reason)
        time.sleep(remaining)
        total_wait += remaining
        if fixed_now is not None:
            fixed_now += remaining


def _throttle_before_request():
    """Cross-process BUC gate plus minimum spacing between Meta calls."""
    while True:
        now_epoch = time.time()
        now_mono = time.monotonic()
        with _open_throttle_state() as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = _read_state_locked(fh)
            blocked_until = _as_number(state.get('blocked_until_epoch'))
            cooldown_wait = max(0.0, blocked_until - now_epoch)
            reason = state.get('block_reason') or 'business_usage_soft_limit'
            last = _as_number(state.get('last_request_monotonic'))
            if last > now_mono:
                last = 0
            interval_wait = max(0.0, MIN_INTERVAL_SECONDS - (now_mono - last)) if MIN_INTERVAL_SECONDS > 0 else 0.0
            wait = max(cooldown_wait, interval_wait)
            if wait <= 0:
                state['last_request_monotonic'] = now_mono
                state['min_interval_seconds'] = MIN_INTERVAL_SECONDS
                if blocked_until and blocked_until <= now_epoch:
                    state['blocked_until_epoch'] = 0
                    state['block_reason'] = None
                _write_state_locked(fh, state)
                fcntl.flock(fh, fcntl.LOCK_UN)
                return
            fcntl.flock(fh, fcntl.LOCK_UN)
        if cooldown_wait > BUSINESS_USAGE_MAX_INLINE_WAIT_SECONDS:
            raise AresMetaUsageBlocked(int(math.ceil(cooldown_wait)), reason=reason)
        time.sleep(wait)


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
    params = dict(params or {})
    params['access_token'] = token
    url = f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}?'+urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent':'mgs-ares-meta-ads/0.2'})
    try:
        _throttle_before_request()
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode('utf-8', 'replace')
            payload = json.loads(body)
            headers = dict(resp.headers)
            record_response_usage(headers, resp.status, payload)
            return resp.status, payload, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8','replace')
        try: payload = json.loads(body)
        except Exception: payload = {'raw_length': len(body)}
        headers = dict(e.headers)
        record_response_usage(headers, e.code, payload)
        return e.code, payload, headers


def _encode_form(params):
    clean = {}
    for key, value in dict(params or {}).items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            clean[key] = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        elif isinstance(value, bool):
            clean[key] = 'true' if value else 'false'
        else:
            clean[key] = str(value)
    return clean


def _graph_post_once(path, token, params=None):
    clean = _encode_form(params)
    clean['access_token'] = token
    req = urllib.request.Request(
        f'https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip("/")}',
        data=urllib.parse.urlencode(clean).encode(),
        headers={'User-Agent':'mgs-ares-meta-ads/0.2'},
        method='POST',
    )
    try:
        _throttle_before_request()
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode('utf-8', 'replace')
            payload = json.loads(body) if body else {}
            headers = dict(resp.headers)
            record_response_usage(headers, resp.status, payload)
            return resp.status, payload, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8','replace')
        try: payload = json.loads(body)
        except Exception: payload = {'raw_length': len(body)}
        headers = dict(e.headers)
        record_response_usage(headers, e.code, payload)
        return e.code, payload, headers


def _deferred_payload(status, payload, attempts, total_sleep, retry_after):
    return {
        'error': {
            'message': 'Meta API request deferred by quota-aware backoff; stopped before exceeding the bounded wait.',
            'type': 'AresRateLimitDeferred',
            'code': 'ARES_RATE_LIMIT_DEFERRED',
            'http_status': status,
            'attempts': attempts,
            'total_sleep_seconds': total_sleep,
            'retry_after_seconds': retry_after,
            'last_meta_error': safe_meta_error(payload),
        }
    }


def _request_with_retry(once, path, token, params=None):
    total_sleep = 0
    attempt = 0
    while True:
        attempt += 1
        try:
            status, payload, headers = once(path, token, params)
        except AresMetaUsageBlocked as exc:
            return 429, {
                'error': {
                    'message': str(exc),
                    'type': 'AresMetaUsageBlocked',
                    'code': 'ARES_BUSINESS_USAGE_BLOCKED',
                    'retry_after_seconds': exc.retry_after_seconds,
                    'reason': exc.reason,
                }
            }, {}
        wait_seconds = retry_wait_seconds(status, payload, headers, attempt=attempt)
        if wait_seconds is None:
            return status, payload, headers
        if total_sleep + wait_seconds > RATE_LIMIT_MAX_TOTAL_SLEEP:
            return status, _deferred_payload(status, payload, attempt, total_sleep, wait_seconds), headers
        time.sleep(wait_seconds)
        total_sleep += wait_seconds


def graph_get(path, token, params=None):
    return _request_with_retry(_graph_get_once, path, token, params)


def graph_post(path, token, params=None):
    return _request_with_retry(_graph_post_once, path, token, params)


def graph_post_once(path, token, params=None):
    """Single-attempt POST for non-idempotent writes; caller must GET before any retry."""
    return _graph_post_once(path, token, params)


def graph_batch_get(token, requests):
    if not isinstance(requests, list) or not requests or len(requests) > 50:
        raise ValueError('batch GET requires 1..50 requests')
    batch = []
    names = []
    for index, item in enumerate(requests):
        if not isinstance(item, dict) or not item.get('path'):
            raise ValueError(f'invalid batch request at index {index}')
        params = _encode_form(item.get('params') or {})
        relative_url = str(item['path']).lstrip('/')
        if params:
            relative_url += '?' + urllib.parse.urlencode(params)
        batch.append({'method': 'GET', 'relative_url': relative_url})
        names.append(str(item.get('name') or f'request_{index+1}'))
    status, payload, headers = graph_post('', token, {'batch': batch})
    if status != 200 or not isinstance(payload, list):
        return status, payload, headers
    normalized = []
    for index, item in enumerate(payload):
        code = int(item.get('code') or 0) if isinstance(item, dict) else 0
        child_headers = {}
        for row in (item.get('headers') or []) if isinstance(item, dict) else []:
            if isinstance(row, dict) and row.get('name'):
                child_headers[str(row['name'])] = row.get('value')
        raw_body = item.get('body') if isinstance(item, dict) else None
        try: body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except (TypeError, ValueError, json.JSONDecodeError): body = {'raw_length': len(raw_body or '')}
        record_response_usage(child_headers, code, body if isinstance(body, dict) else {})
        normalized.append({'name': names[index], 'code': code, 'body': body, 'headers': child_headers})
    return status, normalized, headers


def safe_meta_error(payload):
    err = payload.get('error') if isinstance(payload, dict) else None
    if not isinstance(err, dict):
        return payload
    result = {
        key: err.get(key)
        for key in (
            'message', 'type', 'code', 'error_subcode', 'error_user_title',
            'error_user_msg', 'error_data', 'fbtrace_id', 'retry_after_seconds',
            'reason', 'http_status', 'attempts', 'total_sleep_seconds',
            'last_meta_error',
        )
        if err.get(key) is not None
    }
    error_data = result.get('error_data')
    if isinstance(error_data, str):
        try:
            parsed = json.loads(error_data)
            result['error_data'] = parsed
            if isinstance(parsed, dict) and parsed.get('blame_field_specs') is not None:
                result['blame_field_specs'] = parsed.get('blame_field_specs')
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return result
