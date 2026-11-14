"""Read-only receipt adapter for one recovered Utility reservoir occurrence.

Never changes candidates, scheduler history or delivery. Historical success is
valid only for the exact native contract/slot and independently read artifacts.
"""
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

from mgs_automation_continuity import native_contract_hash

BASE = Path('/root/mgs-agent')
JOB = '62dfebef142b'
KEY = '673b5f8f33b370cfd870301d'
THREAD = '1535306062457081926'
CONTRACT = '7eaec82a82eda7edaf5e7ac6d45e83e237da7148150e3082dd54f553154175c5'
SLOT = '2026-11-14T06:30:00-05:00'
LAST_RUN = '2026-11-14T06:34:37.615050-05:00'
CATALOG_SHA = 'b389e22d99ea70510bb214dcd7387591ce6d0660a8007d8f5a1be3ed57bc73b2'
REPORT = '1571126195251187714'
CHANNEL = '1498132022634483894'
CANDIDATE = 'us-job-es-20261114-01'
COVERAGE = {'US-CC-EN': 24, 'US-CC-ES': 19, 'US-JOB-ES': 4}


def scope(job):
    return (job.get('id') == JOB and job.get('enabled') is True
            and job.get('state') not in ('paused', 'completed')
            and not job.get('fire_claim') and native_contract_hash(job) == CONTRACT
            and job.get('last_run_at') == LAST_RUN
            and (job.get('last_dispatch') or {}).get('scheduled_at') == SLOT)


def local_validation(base=BASE):
    """Use the business runner's eligibility rules; no browser or login."""
    raw = (base / 'data/sb-utility-generated-candidates.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA:
        raise ValueError('Recovered catalog drift; no historical receipt reuse')
    spec = importlib.util.spec_from_file_location(
        'reservoir_candidate_runner', base / 'scripts/sb-utility-candidate-approval.py')
    if spec is None or spec.loader is None:
        raise ValueError('Canonical candidate runner unavailable')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # Reuse the canonical lock without creating/truncating or taking a lease.
    with runner.LOCK_PATH.open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return _validate_locked(base, raw, runner)


def _validate_locked(base, raw, runner):
    catalog = json.loads(raw)
    bank_path = base / 'data/utility-message-bank.json'
    state_path = base / 'data/sb-utility-candidate-approval-state.json'
    bank_raw, state_raw = bank_path.read_bytes(), state_path.read_bytes()
    bank, state = json.loads(bank_raw), json.loads(state_raw)
    all_candidates = [runner.formatted_candidate(c, v)
                      for v, items in catalog['candidates'].items() for c in items]
    for values in ([c['candidate_id'] for c in all_candidates],
                   [c['text_cta_hash'] for c in all_candidates],
                   [runner.repair.normalized(c['text']) for c in all_candidates]):
        if len(values) != 107 or len(set(values)) != 107 or not all(values):
            raise ValueError('Recovered catalog uniqueness mismatch')
    available = {}
    for vertical, required in COVERAGE.items():
        selected = runner.select_catalog_candidates(catalog, vertical, 10000, bank, state, set())
        available[vertical] = len(selected)
        if len(selected) < required:
            raise ValueError('Recovered candidate coverage changed: ' + vertical)
    added = [c for c in all_candidates if c['candidate_id'] == CANDIDATE]
    bank_texts = {runner.repair.normalized(r.get('text', '')) for r in bank['records'].values()}
    if (len(added) != 1 or added[0]['text_cta_hash'] in bank['records']
            or runner.repair.normalized(added[0]['text']) in bank_texts):
        raise ValueError('Original candidate no longer eligible')
    events = [json.loads(line) for line in (base / 'logs/events-audit.jsonl').read_text().splitlines()
              if 'sb_utility_candidate_catalog_replenished' in line
              and '2026-11-14T11:34:11.458931+00:00' in line]
    if len(events) != 1:
        raise ValueError('Original audit event missing or ambiguous')
    event = events[0]
    if (event.get('source_thread_id') != THREAD or event.get('candidate_ids_added') != [CANDIDATE]
            or event.get('verticals_changed') != {'US-JOB-ES': 1}
            or event.get('smart_bidding_templates_changed') is not False):
        raise ValueError('Original audit scope mismatch')
    if {v: r['available'] for v, r in event['coverage'].items()} != COVERAGE:
        raise ValueError('Original audit coverage mismatch')
    if ((base / 'data/sb-utility-generated-candidates.json').read_bytes() != raw
            or bank_path.read_bytes() != bank_raw or state_path.read_bytes() != state_raw):
        raise ValueError('Concurrent reservoir inputs changed; retain pending verification')
    return {'catalog_sha256': CATALOG_SHA, 'available': available, 'candidate_id': CANDIDATE}


def read_local(base):
    result = subprocess.run([str(base / '.venv-sb/bin/python'), str(base / 'scripts/mgs_sb_reservoir_continuity.py'),
                             '--validate-local'], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError('Reservoir local receipt validation unavailable')
    return json.loads(result.stdout)


def observation(job, *, base=BASE, validator=read_local, getter=None):
    """Fresh local eligibility + exact Discord GET; never accept worker wording."""
    if not scope(job):
        return None
    try:
        evidence = validator(base)
        if (evidence.get('catalog_sha256') != CATALOG_SHA or evidence.get('candidate_id') != CANDIDATE
                or any(evidence.get('available', {}).get(v, 0) < n for v, n in COVERAGE.items())):
            return None
        if getter is None:
            from mgs_alert_transport import request
            getter = request
        message = getter('GET', f'https://discord.com/api/v10/channels/{CHANNEL}/messages/{REPORT}')
        fields = {f['name']: f['value'] for e in message.get('embeds', []) for f in e.get('fields', [])}
        if (str(message.get('id')) != REPORT or str(message.get('channel_id')) != CHANNEL
                or str(message.get('author', {}).get('id')) != '1496296175014252634'
                or message.get('content', '') or message.get('mentions')
                or len(message.get('embeds', [])) != 1
                or fields.get('Tipo') != 'data'
                or 'data/sb-utility-generated-candidates.json' not in fields.get('Path', '')
                or CANDIDATE not in fields.get('Evidência', '')
                or '24/19/4' not in fields.get('Evidência', '')
                or datetime.fromisoformat(message['timestamp']).timestamp()
                   < datetime.fromisoformat(SLOT).timestamp()):
            return None
        return {'status': 'OK', 'verified': True, 'target': 'native:zeus:' + JOB,
                'receipt': f'reservoir:{KEY};catalog:{CATALOG_SHA};discord:{CHANNEL}/{REPORT}',
                'at': time.time(), 'source': {'kind': 'native', 'profile': 'zeus', 'job_id': JOB,
                'thread_id': THREAD, 'contract_hash': CONTRACT}, 'slot': SLOT, 'evidence': evidence}
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError):
        return None


if __name__ == '__main__':
    import sys
    if sys.argv[1:] != ['--validate-local']:
        raise SystemExit('Only --validate-local is supported; read-only')
    print(json.dumps(local_validation(), ensure_ascii=False))
