"""Read-only closure receipts for explicitly reconciled hourly DR occurrences.

Each receipt distinguishes restored current protection from an original snapshot.
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
            'fields': 'id,name,size,parents,trashed,md5Checksum,sha256Checksum,appProperties,properties'}
        query['supportsAllDrives'] = 'true'
        url = 'https://www.googleapis.com/drive/v3/files/' + file_id + '?' + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, method='GET', headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    return get


def observation(job, *, base=BASE, reader=None, getter=None):
    slot = (job.get('last_dispatch') or {}).get('scheduled_at')
    if isinstance(slot, str) and slot in COMMITTED_OCCURRENCES:
        return _finalized_observation(job, slot, COMMITTED_OCCURRENCES[slot],
                                      base=base, reader=reader, getter=getter,
                                      native_committed=True)
    if not scope(job):
        return finalized_observation(job, base=base, reader=reader, getter=getter)
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


FINAL_KEY = 'b072e2d339b0565639ed5d4a'
FINAL_SLOT = '2026-11-20T14:23:00-05:00'
FINAL_LAST_RUN = '2026-11-20T14:30:28.371171-05:00'
FINAL_FILE = '1oPnCHSP-jmTPaVFNLn10zpzBNdQB3MRh'
FINAL_ACK = '1c-Qiakb8qlQNnL5q42IrgwevMmUe6lTv'
FINAL_NAME = 'mgs-dr-hourly-20261120T192348Z.zip.gpg'
FINAL_SHA = 'f2ac92366e1163d7021bfa4ea80de7c3d4e3d2fc03cfd1a0247abd095d1245f5'
FINAL_MD5 = '9317cedd295f8adb81cea517c0328e1b'
FINAL_SIZE = '2070821835'


FINALIZED_OCCURRENCES = {
    '2026-11-23T16:23:00-05:00': (
        '4d9d9e58fa760d6a46dd7f29', '2026-11-23T16:30:49.097709-05:00',
        '1dAPxBdUBnX8rLShPShTR2bO-LQcwjqtE', '1JYIuJnNBYd5QSIClHy2bGMDJHLC1aad_',
        'mgs-dr-hourly-20261123T212347Z.zip.gpg',
        '047209457d51401bc5593e92a884f1771a37203b67f5ef4c6ea27962555781d4',
        '07f5fd5fd89614084c780ddd0b73d553', '2130844424'),
}


COMMITTED_OCCURRENCES = {
    '2026-11-23T22:23:00-05:00': (
        '998e2b8cf7b40407b62aff50', '2026-11-23T22:30:36.778275-05:00',
        '1iZiCFlJ9qsHOi5f3D5FhifjQACUR_6vI', '1rvauyzSGMecwqLBB_hestYbI5Tb-G5Ni',
        'mgs-dr-hourly-20261124T032348Z.zip.gpg',
        'ffb2fcada124066f034a5975f10665432df4e0f602a1a757791e8e5677f1314f',
        '8cb7cd965f143ff868b19a9cd34acd7f', '2138597966'),
}


def finalized_observation(job, *, base=BASE, reader=None, getter=None):
    slot = (job.get('last_dispatch') or {}).get('scheduled_at')
    occurrence = FINALIZED_OCCURRENCES.get(slot) if isinstance(slot, str) else None
    if occurrence is None:
        occurrence = (FINAL_KEY, FINAL_LAST_RUN, FINAL_FILE, FINAL_ACK,
                      FINAL_NAME, FINAL_SHA, FINAL_MD5, FINAL_SIZE)
        slot = FINAL_SLOT
    return _finalized_observation(job, slot, occurrence, base=base,
                                  reader=reader, getter=getter)


def _finalized_observation(job, slot, occurrence, *, base=BASE, reader=None, getter=None,
                           native_committed=False):
    """Read-only exact-occurrence proof; never finalize or replay business here."""
    (FINAL_KEY, FINAL_LAST_RUN, FINAL_FILE, FINAL_ACK,
     FINAL_NAME, FINAL_SHA, FINAL_MD5, FINAL_SIZE) = occurrence
    FINAL_SLOT = slot
    if (job.get('id') != JOB or job.get('enabled') is not True
            or job.get('state') != 'scheduled' or job.get('fire_claim')
            or native_contract_hash(job) != CONTRACT
            or job.get('last_run_at') != FINAL_LAST_RUN
            or (job.get('last_dispatch') or {}).get('scheduled_at') != FINAL_SLOT):
        return None
    try:
        root = base / ('reports/automation-recovery-' + FINAL_KEY)
        execution = {}
        if native_committed:
            if (job.get('last_status') != 'error'
                    or 'worker exited with status -15' not in str(job.get('last_error', ''))):
                return None
            result = json.loads((root / 'canonical-native-result.json').read_text())
            state = json.loads((base / 'data/mgs-offsite-backup-state.json').read_text())
            if state.get('last_success', {}).get('quick') != result:
                return None
            matches = []
            with (base / 'logs/mgs-offsite-backup.jsonl').open() as events:
                for line in events:
                    # Historical log damage outside this immutable ID is not
                    # evidence about this occurrence. Matching damage fails closed.
                    if FINAL_FILE not in line:
                        continue
                    event = json.loads(line)
                    if event.get('remote_file_id') == FINAL_FILE and event.get('event') == 'backup_success':
                        matches.append(event)
            if (len(matches) != 1 or matches[0].get('mode') != 'quick'
                    or matches[0].get('tier') != 'hourly'
                    or str(matches[0].get('size_bytes')) != FINAL_SIZE
                    or matches[0].get('sha256') != FINAL_SHA
                    or matches[0].get('retention_trashed_count') != 0):
                return None
        else:
            execution = json.loads((root / 'canonical-execution.json').read_text())
            result = json.loads((root / 'canonical-finalize.stdout').read_text())
        delivery = json.loads((root / 'independent-readback.json').read_text())
        command = ['/usr/bin/python3', '/root/mgs-agent/scripts/mgs-offsite-backup.py',
                   'finalize-direct', '--remote-id', FINAL_FILE, '--expected-name', FINAL_NAME]
        expected = {'status': 'PASS', 'mode': 'quick', 'tier': 'hourly',
                    'remote_file_id': FINAL_FILE, 'remote_name': FINAL_NAME,
                    'remote_size_bytes': int(FINAL_SIZE), 'encrypted_sha256': FINAL_SHA,
                    'encrypted_md5': FINAL_MD5, 'archive_sha256_stream_verified': True,
                    'retention_applied': False, 'retention_trashed_count': 0}
        if not native_committed:
            expected['recovery'] = 'same_snapshot_existing_upload_finalized'
            if (execution.get('operation') != FINAL_KEY or execution.get('returncode') != 0
                    or execution.get('command') != command):
                return None
        if (any(result.get(k) != v for k, v in expected.items())
                or result.get('archive_native_ack', {}).get('file_id') != FINAL_ACK
                or delivery.get('operation') != FINAL_KEY or delivery.get('GET_verified') is not True):
            return None
        report = delivery['report_infra_message_id']
        if not str(report).isdigit():
            return None
        reader = reader or drive_reader()
        remote = reader(FINAL_FILE)
        if (remote.get('id') != FINAL_FILE or remote.get('name') != FINAL_NAME
                or remote.get('parents') != [PARENT] or remote.get('trashed') is not False
                or remote.get('size') != FINAL_SIZE or remote.get('md5Checksum') != FINAL_MD5
                or remote.get('sha256Checksum') != FINAL_SHA):
            return None
        ack_meta = reader(FINAL_ACK)
        if (ack_meta.get('id') != FINAL_ACK or ack_meta.get('parents') != [ACK_PARENT]
                or ack_meta.get('trashed') is not False
                or ack_meta.get('properties', {}).get('mgsArchiveType') != 'backup_direct_ack'
                or ack_meta.get('sha256Checksum') != result['archive_native_ack']['sha256']):
            return None
        ack = reader(FINAL_ACK, True)
        expected_ack = {'schema': 'mgs.backup.direct.archive.ack.v1', 'status': 'verified',
                        'file_id': FINAL_FILE, 'parent_id': PARENT, 'size': FINAL_SIZE,
                        'md5': FINAL_MD5, 'sha256': FINAL_SHA, 'tier': 'hourly',
                        'canonical_sa_upload': True, 'independent_sa_stream_verified': True,
                        'archive_trash_enabled': False}
        if any(ack.get(k) != v for k, v in expected_ack.items()):
            return None
        if getter is None:
            from mgs_alert_transport import request
            getter = request
        msg = getter('GET', f'https://discord.com/api/v10/channels/{CHANNEL}/messages/{report}')
        if (msg.get('id') != report or msg.get('channel_id') != CHANNEL
                or msg.get('author', {}).get('id') != '1496296175014252634'
                or msg.get('content') != '' or msg.get('mentions') != []
                or len(msg.get('embeds', [])) != 1 or FINAL_FILE not in json.dumps(msg['embeds'])):
            return None
        return {'status': 'OK', 'verified': True, 'target': 'native:zeus:' + JOB,
                'at': time.time(), 'slot': FINAL_SLOT,
                'source': {'kind': 'native', 'profile': 'zeus', 'job_id': JOB,
                           'thread_id': THREAD, 'contract_hash': CONTRACT},
                'receipt': f'dr-finalization:{FINAL_KEY};drive:{FINAL_FILE};ack:{FINAL_ACK};discord:{CHANNEL}/{report}',
                'evidence': {'remote_id': FINAL_FILE, 'ack_id': FINAL_ACK,
                             'same_original_snapshot': True, 'upload_replayed': False,
                             'native_already_committed': native_committed}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
        return None
