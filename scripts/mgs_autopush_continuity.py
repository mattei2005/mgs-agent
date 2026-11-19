"""Read-only verification of the exact reviewed-path auto-push recovery.

Never commit, push, reload the watcher, or deliver the diagnostic here.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
from datetime import datetime

KEY = '056ec882525a87def44d9359'
ALERT = '1572369782659874817'
SOURCE_KEY = 'alert:' + ALERT
ROOT = Path('/root/.hermes/shared/automation-continuity/runs') / KEY
DB = Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')
BASE = Path('/root/mgs-agent')
INDEX_KEY = '3e1e5a580dd9f2151ef142e8'
INDEX_ALERT = '1572894488660017277'


def live_check(base, receipt):
    from mgs_alert_transport import request, collection_url
    def git(*args):
        return subprocess.check_output(['git', '-C', str(base), *args], timeout=25)
    if subprocess.check_output(['systemctl', 'is-active', 'mgs-autocommit.service'], timeout=10).strip() != b'active':
        raise ValueError('Watcher inactive')
    remote = git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0]
    if git('rev-parse', 'HEAD').decode().strip() != remote:
        raise ValueError('Remote not synchronized')
    for name, expected in receipt['validated_artifact_hashes'].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Local artifact drift')
        if hashlib.sha256(git('show', remote + ':' + name)).hexdigest() != expected:
            raise ValueError('Remote artifact drift')
    message = request('GET', collection_url('1498132022634483894') + '/' + receipt['report_infra_message_id'])
    if message.get('content') != '' or str(message.get('id')) != receipt['report_infra_message_id'] or message.get('mentions'):
        raise ValueError('Infrastructure delivery mismatch')
    if not message.get('embeds') or KEY not in json.dumps(message['embeds']):
        raise ValueError('Infrastructure receipt scope mismatch')
    return {'remote_main': remote, 'exact_remote_hashes': True, 'report_infra_get_verified': message['id']}


def observation(base=BASE, root=ROOT, queue_path=DB, reader=None, now=None):
    path = root / 'recovery-evidence.json'
    if not path.exists():
        return None
    if queue_path is not None:
        try:
            with sqlite3.connect(f'file:{queue_path}?mode=ro', uri=True) as db:
                row = db.execute('SELECT source_key,state FROM requests WHERE key=?', (KEY,)).fetchone()
            if not row or row[0] != SOURCE_KEY or row[1] in ('completed_validated', 'cancelled_owner'):
                return None
        except sqlite3.Error:
            return None
    now = time.time() if now is None else now
    result = {'status': 'UNKNOWN', 'verified': False, 'target': SOURCE_KEY,
              'receipt': str(path), 'at': now,
              'source': {'kind': 'alert', 'profile': 'zeus', 'alert_id': ALERT,
                         'alert_channel': '1498132022634483894'}}
    try:
        receipt = json.loads(path.read_text())
        if receipt.get('operation_key') != KEY or receipt.get('alert_id') != ALERT:
            raise ValueError('Wrong occurrence')
        if receipt.get('authority_message_id') != '1569193434189668453':
            raise ValueError('Wrong authority')
        if receipt.get('status') != 'recovered_waiting_supervisor_validation':
            raise ValueError('Recovery not certified')
        if len(receipt.get('validated_artifact_hashes', {})) < 5:
            raise ValueError('Incomplete artifact receipt')
        state_path = base / 'data/auto-push-monitor.json'
        before = state_path.read_bytes()
        state = json.loads(before)
        stamp = datetime.fromisoformat(state['last_check'].replace('Z', '+00:00')).timestamp()
        if stamp < receipt['recovery_not_before'] or stamp > now + 30 or now - stamp > 1800:
            raise ValueError('Fresh recovered monitor missing')
        if state['consecutive_failures'] != 0 or state.get('last_failure_details'):
            raise ValueError('Auto-push monitor unhealthy')
        evidence = (reader or live_check)(base, receipt)
        if state_path.read_bytes() != before:
            raise ValueError('Concurrent monitor mutation')
        result.update(status='OK', verified=True, evidence=evidence)
    except Exception as exc:
        result['receipt'] += '; unverified:' + type(exc).__name__
    return result


def index_lock_live_check(base, receipt):
    """Only read the native retry and existing delivery; never remove a lock."""
    from mgs_alert_transport import request, collection_url
    commit = receipt['native_retry_commit']
    import re
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid retry identity')
    if (base / '.git/index.lock').exists():
        raise ValueError('Git index still occupied')
    if subprocess.check_output(['systemctl', 'is-active', 'mgs-autocommit.service'], timeout=10).strip() != b'active':
        raise ValueError('Native watcher inactive')
    log = (base / 'logs/auto-commit-watcher.log').read_text()
    if "Unable to create '/root/mgs-agent/.git/index.lock': File exists." not in log:
        raise ValueError('Original failure evidence missing')
    if f'[main {commit[:10]}]' not in log:
        raise ValueError('Native retry commit missing')
    push = (base / 'logs/auto-push.log').read_text()
    if f'auto-push OK commit={commit[:10]} branch=main' not in push:
        raise ValueError('Native push missing')
    remote = subprocess.check_output(['git', '-C', str(base), 'ls-remote', 'origin', 'refs/heads/main'], timeout=25).decode().split()[0]
    subprocess.run(['git', '-C', str(base), 'merge-base', '--is-ancestor', commit, remote], check=True, capture_output=True, timeout=10)
    source = request('GET', collection_url('1498132022634483894') + '/' + INDEX_ALERT)
    if str(source.get('author', {}).get('id')) != '1496296175014252634' or source.get('content') != '' or len(source.get('embeds', [])) != 1:
        raise ValueError('Untrusted source alert')
    embed = source['embeds'][0]
    if embed.get('title') != 'Auto-push falhando' or embed.get('color') != 15158332:
        raise ValueError('Source scope changed')
    source_fields = {f['name']: f['value'] for f in embed.get('fields', [])}
    if 'auto-commit falhou [commit/push não iniciou; consultar auto-commit-watcher.log]' not in source_fields.get('Último erro', ''):
        raise ValueError('Source failure changed')
    source_at = datetime.fromisoformat(source['timestamp'].replace('Z', '+00:00')).timestamp()
    if receipt['recovery_not_before'] < source_at:
        raise ValueError('Receipt predates source')
    push_times = re.findall(r'^\[([^]]+)\] auto-push OK commit=' + commit[:10] + r' branch=main$', push, re.M)
    if not any(datetime.fromisoformat(stamp).timestamp() >= source_at for stamp in push_times):
        raise ValueError('Retry predates incident')
    notice = request('GET', collection_url('1498132022634483894') + '/' + receipt['recovery_notice_id'])
    embeds = notice.get('embeds', [])
    if str(notice.get('author', {}).get('id')) != '1496296175014252634' or notice.get('content') != '' or len(embeds) != 1:
        raise ValueError('Untrusted recovery notice')
    if embeds[0].get('title') != 'Auto-push restabelecido' or embeds[0].get('color') != 3066993:
        raise ValueError('Recovery delivery mismatch')
    if datetime.fromisoformat(notice['timestamp'].replace('Z', '+00:00')).timestamp() < source_at:
        raise ValueError('Recovery notice predates incident')
    fields = {f['name']: f['value'] for f in embeds[0].get('fields', [])}
    if fields.get('Último commit OK', '').strip('`') != commit[:10]:
        raise ValueError('Recovery notice commit mismatch')
    return {'remote_main': remote, 'native_retry_commit': commit, 'recovery_notice_get_verified': notice['id']}


def index_lock_observation(base=BASE, root=None, queue_path=DB, reader=None, now=None):
    """Scoped receipt for the one transient index-lock occurrence."""
    root = Path(root) if root is not None else ROOT.parent / INDEX_KEY
    path = root / 'recovery-evidence.json'
    if not path.exists():
        return None
    if queue_path is not None:
        from contextlib import closing
        try:
            with closing(sqlite3.connect(f'file:{queue_path}?mode=ro', uri=True)) as db:
                row = db.execute('SELECT source_key,state FROM requests WHERE key=?', (INDEX_KEY,)).fetchone()
        except sqlite3.Error:
            return None
        if not row or row[0] != 'alert:' + INDEX_ALERT or row[1] in ('completed_validated', 'cancelled_owner'):
            return None
    now = time.time() if now is None else now
    result = {'status': 'UNKNOWN', 'verified': False, 'target': 'alert:' + INDEX_ALERT,
              'receipt': str(path), 'at': now,
              'source': {'kind': 'alert', 'profile': 'zeus', 'alert_id': INDEX_ALERT,
                         'alert_channel': '1498132022634483894'}}
    try:
        receipt = json.loads(path.read_text())
        if (receipt.get('operation_key'), receipt.get('alert_id'), receipt.get('authority_message_id'), receipt.get('status')) != (INDEX_KEY, INDEX_ALERT, '1569193434189668453', 'recovered_waiting_supervisor_validation'):
            raise ValueError('Uncertified occurrence')
        state_path = base / 'data/auto-push-monitor.json'
        before = state_path.read_bytes()
        state = json.loads(before)
        stamp = datetime.fromisoformat(state['last_check'].replace('Z', '+00:00')).timestamp()
        if stamp < receipt['recovery_not_before'] or stamp > now + 30 or now - stamp > 1800:
            raise ValueError('Fresh monitor missing')
        if state['consecutive_failures'] != 0 or state.get('last_failure_details'):
            raise ValueError('Monitor remains unhealthy')
        result['evidence'] = (reader or index_lock_live_check)(base, receipt)
        if state_path.read_bytes() != before:
            raise ValueError('Concurrent monitor mutation')
        result.update(status='OK', verified=True)
    except Exception as exc:
        result['receipt'] += '; unverified:' + type(exc).__name__
    return result
