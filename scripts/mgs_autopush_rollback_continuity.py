"""Read-only exact-occurrence evidence; never replay or close a queue row."""
import hashlib
import json
import re
import sqlite3
import subprocess
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

KEY = 'fb3abfb178aacd92d9633715'
ALERT = '1573426742474051796'
BASE = Path('/root/mgs-agent')
DB = Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')
ROOT = Path('/root/.hermes/shared/automation-continuity/runs') / KEY
ROLLBACK = 'reports/automation-recovery-b072e2d339b0565639ed5d4a/rollback/mgs_private_control_store.py'
ARTIFACTS = {'.gitignore', 'tests/test_auto_commit_sensitive_paths.py',
             'tests/test_auto_commit_empty_index.py', 'scripts/mgs_autopush_rollback_continuity.py',
             'scripts/mgs_automation_supervisor.py', 'tests/test_autopush_rollback_continuity.py'}


def live_check(base, receipt):
    from mgs_alert_transport import request, collection_url
    commit = receipt['native_retry_commit']
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid native retry identity')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(base), *args], timeout=25)
    if subprocess.check_output(['systemctl', 'is-active', 'mgs-autocommit.service'], timeout=10).strip() != b'active':
        raise ValueError('Native watcher inactive')
    if (base / '.git/index.lock').exists():
        raise ValueError('Git index occupied')
    if hashlib.sha256((base / ROLLBACK).read_bytes()).hexdigest() != '0022cbd3973d0cab0b86cfde7e5ed3c877f7a3f62dd4637706c2dcdf647d2567':
        raise ValueError('Rollback bytes changed')
    git('check-ignore', '-q', '--', ROLLBACK)
    remote = git('ls-remote', 'origin', 'refs/heads/main').decode().split()[0]
    subprocess.run(['git', '-C', str(base), 'merge-base', '--is-ancestor', commit, remote], check=True, capture_output=True, timeout=10)
    for path, digest in receipt['validated_artifact_hashes'].items():
        if hashlib.sha256((base / path).read_bytes()).hexdigest() != digest or hashlib.sha256(git('show', remote + ':' + path)).hexdigest() != digest:
            raise ValueError('Reviewed artifact drift')
    log = (base / 'logs/auto-commit-watcher.log').read_text()
    push = (base / 'logs/auto-push.log').read_text()
    if f'[main {commit[:10]}]' not in log or f'auto-push OK commit={commit[:10]} branch=main' not in push:
        raise ValueError('Native commit/push missing')
    source = request('GET', collection_url('1498132022634483894') + '/' + ALERT)
    if str(source.get('author', {}).get('id')) != '1496296175014252634' or source.get('content') != '' or len(source.get('embeds', [])) != 1:
        raise ValueError('Untrusted original alert')
    embed = source['embeds'][0]
    fields = {f['name']: f['value'] for f in embed.get('fields', [])}
    if embed.get('title') != 'Auto-push falhando' or 'auto-commit bloqueado por guardrail sensível' not in fields.get('Último erro', ''):
        raise ValueError('Original scope changed')
    source_at = datetime.fromisoformat(source['timestamp'].replace('Z', '+00:00')).timestamp()
    if receipt['recovery_not_before'] < source_at:
        raise ValueError('Receipt predates incident')
    stamps = re.findall(r'^\[([^]]+)\] auto-push OK commit=' + commit[:10] + r' branch=main$', push, re.M)
    if not any(datetime.fromisoformat(s).timestamp() >= source_at for s in stamps):
        raise ValueError('Native retry predates incident')
    for key, title in [('recovery_notice_id', 'Auto-push restabelecido'), ('report_infra_message_id', 'REPORT-INFRA — modificada')]:
        msg = request('GET', collection_url('1498132022634483894') + '/' + receipt[key])
        if msg.get('content') != '' or msg.get('mentions') or str(msg.get('author', {}).get('id')) != '1496296175014252634' or len(msg.get('embeds', [])) != 1 or msg['embeds'][0].get('title') != title:
            raise ValueError('Delivery mismatch')
        if datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).timestamp() < source_at:
            raise ValueError('Delivery predates incident')
        if key == 'report_infra_message_id' and KEY not in json.dumps(msg['embeds']):
            raise ValueError('Infrastructure receipt scope mismatch')
        if key == 'recovery_notice_id':
            fields = {f['name']: f['value'] for f in msg['embeds'][0].get('fields', [])}
            if fields.get('Último commit OK', '').strip('`') != receipt['recovery_notice_commit']:
                raise ValueError('Recovery notice commit mismatch')
    return {'remote_main': remote, 'native_retry_commit': commit,
            'recovery_notice_get_verified': receipt['recovery_notice_id'],
            'report_infra_get_verified': receipt['report_infra_message_id']}


def observation(base=BASE, root=ROOT, queue_path=DB, reader=None, now=None):
    path = Path(root) / 'recovery-evidence.json'
    if not path.exists():
        return None
    if queue_path is not None:
        try:
            with closing(sqlite3.connect(f'file:{queue_path}?mode=ro', uri=True)) as db:
                row = db.execute('SELECT source_key,state FROM requests WHERE key=?', (KEY,)).fetchone()
            if not row or row[0] != 'alert:' + ALERT or row[1] in ('completed_validated', 'cancelled_owner', 'blocked_decision'):
                return None
        except sqlite3.Error:
            return None
    now = time.time() if now is None else now
    result = {'status': 'UNKNOWN', 'verified': False, 'target': 'alert:' + ALERT,
              'receipt': str(path), 'at': now,
              'source': {'kind': 'alert', 'profile': 'zeus', 'alert_id': ALERT,
                         'alert_channel': '1498132022634483894'}}
    try:
        receipt = json.loads(path.read_text())
        if (receipt.get('operation_key'), receipt.get('alert_id'), receipt.get('authority_message_id'), receipt.get('status')) != (KEY, ALERT, '1569193434189668453', 'recovered_waiting_supervisor_validation'):
            raise ValueError('Uncertified occurrence')
        if set(receipt.get('validated_artifact_hashes', {})) != ARTIFACTS:
            raise ValueError('Incomplete reviewed artifact set')
        state_path = base / 'data/auto-push-monitor.json'
        before = state_path.read_bytes()
        state = json.loads(before)
        stamp = datetime.fromisoformat(state['last_check'].replace('Z', '+00:00')).timestamp()
        if stamp < receipt['recovery_not_before'] or stamp > now + 30 or now - stamp > 1800 or state['consecutive_failures'] != 0 or state.get('last_failure_details'):
            raise ValueError('Fresh healthy monitor missing')
        result['evidence'] = (reader or live_check)(base, receipt)
        if state_path.read_bytes() != before:
            raise ValueError('Concurrent monitor mutation')
        result.update(status='OK', verified=True)
    except Exception as exc:
        result['receipt'] += '; unverified:' + type(exc).__name__
    return result
