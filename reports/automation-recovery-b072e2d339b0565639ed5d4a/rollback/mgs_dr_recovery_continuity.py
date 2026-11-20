"""Read-only closure receipt for the exact corrected hourly DR occurrence.

This certifies current protection restored, NOT recreation of the lost snapshot.
Never uploads, changes scheduler history, deletes, or sends a business report.
"""
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

from mgs_automation_continuity import native_contract_hash

BASE = Path('/root/mgs-agent')
KEY = '30e890e4a3e5d052791e2ada'
JOB = '3ff8bd8ca40d'
CONTRACT = '0326574c266953ac88ed1f23c23eaae7dfc2a6897b2f4ce050feeb8bb48e927e'
THREAD = '1527004682382479380'
SLOT = '2026-11-15T05:23:00-05:00'
LAST_RUN = '2026-11-15T05:28:52.460668-05:00'
FILE = '1nZjELCY2DU_nH8WOlNBOSdJYr60VyNU9'
ACK = '1Be8V1dgjj0nc66aX-I5rvfcehKOHWyTE'
PARENT = '1SSClDHGxRQY3y2_FJ5I9OiiHD-HXpo2V'
ACK_PARENT = '1vrC6oOrTwNrxQRdGA12U_iKT9GqyXLgO'
SHA = '3da5a14492ec6d6c882e7a5a699399116a1983ec5ed46e257f16a63fbbd9c9ec'
MD5 = '3f200bc9de63f9301dc18ac55d5b03d1'
SIZE = '1892829458'
REPORT = '1571476086137819247'
CHANNEL = '1498132022634483894'


def scope(job):
    return (job.get('id') == JOB and job.get('enabled') is True
            and job.get('state') == 'scheduled' and not job.get('fire_claim')
            and native_contract_hash(job) == CONTRACT
            and job.get('last_run_at') == LAST_RUN
            and (job.get('last_dispatch') or {}).get('scheduled_at') == SLOT)


def drive_reader():
    from mgs_google_workspace_auth import (load_service_account,
                                           service_account_access_token, DRIVE_SCOPE)
    sa = load_service_account()
    if (sa.get('client_email') != 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
            or sa.get('project_id') != 'mgs-core-prod'):
        raise ValueError('Canonical corporate SA required')
    token = service_account_access_token(DRIVE_SCOPE)

    def get(file_id, media=False):
        query = {'alt': 'media'} if media else {
            'fields': 'id,name,size,parents,trashed,md5Checksum,sha256Checksum,appProperties'}
        query['supportsAllDrives'] = 'true'
        url = 'https://www.googleapis.com/drive/v3/files/' + file_id + '?' + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, method='GET', headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    return get


def observation(job, *, base=BASE, reader=None, getter=None):
    if not scope(job):
        return None
    try:
        root = base / ('reports/automation-recovery-' + KEY)
        execution = json.loads((root / 'canonical-execution.json').read_text())
        result = json.loads((root / 'canonical-retry.stdout').read_text())
        prior = json.loads((root / 'independent-readback.json').read_text())
        if (execution.get('operation') != KEY or execution.get('returncode') != 0
                or execution.get('command') != 'canonical backup --mode quick --no-retention'
                or result.get('status') != 'PASS' or result.get('mode') != 'quick'
                or result.get('tier') != 'hourly' or result.get('remote_file_id') != FILE
                or str(result.get('remote_size_bytes')) != SIZE
                or result.get('retention_applied') is not False
                or result.get('retention_trashed_count') != 0
                or prior.get('operation') != KEY
                or prior.get('canonical_result', {}).get('archive_sha256_stream_verified') is not True):
            return None
        reader = reader or drive_reader()
        remote = reader(FILE)
        if (remote.get('id') != FILE or remote.get('trashed') is not False
                or remote.get('parents') != [PARENT] or remote.get('size') != SIZE
                or remote.get('md5Checksum') != MD5 or remote.get('sha256Checksum') != SHA
                or remote.get('appProperties', {}).get('sha256') != SHA):
            return None
        ack_meta = reader(ACK)
        if ack_meta.get('id') != ACK or ack_meta.get('trashed') is not False or ack_meta.get('parents') != [ACK_PARENT]:
            return None
        ack = reader(ACK, True)
        expected = {'file_id': FILE, 'parent_id': PARENT, 'sha256': SHA, 'md5': MD5,
                    'size': SIZE, 'status': 'verified', 'tier': 'hourly',
                    'schema': 'mgs.backup.direct.archive.ack.v1',
                    'canonical_sa_upload': True, 'independent_sa_stream_verified': True,
                    'archive_trash_enabled': False}
        if any(ack.get(k) != v for k, v in expected.items()):
            return None
        if getter is None:
            from mgs_alert_transport import request
            getter = request
        message = getter('GET', f'https://discord.com/api/v10/channels/{CHANNEL}/messages/{REPORT}')
        if (message.get('id') != REPORT or message.get('channel_id') != CHANNEL
                or message.get('author', {}).get('id') != '1496296175014252634'
                or message.get('content', '') or message.get('mentions')
                or len(message.get('embeds', [])) != 1
                or FILE not in json.dumps(message['embeds'])):
            return None
        return {'status': 'OK', 'verified': True, 'target': 'native:zeus:' + JOB,
                'at': time.time(), 'slot': SLOT,
                'source': {'kind': 'native', 'profile': 'zeus', 'job_id': JOB,
                           'thread_id': THREAD, 'contract_hash': CONTRACT},
                'receipt': f'dr-recovery:{KEY};drive:{FILE};ack:{ACK};discord:{CHANNEL}/{REPORT}',
                'evidence': {'remote_id': FILE, 'ack_id': ACK, 'size': SIZE, 'sha256': SHA,
                             'recovery': 'current_protection_restored',
                             'historical_snapshot_recreated': False}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
        return None
