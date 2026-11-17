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
