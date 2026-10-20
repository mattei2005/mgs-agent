"""SHEIN contention queue. No Meta writer; resumes only the original central runner.

Waiting is durable and silent. Independent accounts/assets remain independent.
Never steal an active reservation, alter a manifest/clock or relax QA/authority.
"""
from __future__ import annotations
import copy
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

BASE = Path('/root/mgs-agent')
TERMINAL = {'COMPLETE', 'COMPLETED', 'COMPLETE_PAUSED', 'COMPLETE_FUTURE_ACTIVE'}
ACTIVE = {'ENGINE_PENDING', 'RECOVERY_PENDING', 'POSTPROCESS_PENDING', 'GLOBAL_QA_COMPLETE',
          'ACTIVATION_PENDING', 'ACTIVATION_DEFERRED'}
CONFLICTS = ('reservation changed', 'reserved by another request',
             'exact request', 'in-flight request')


def root(base=BASE):
    return base / 'data/ares/meta-ads/state/shein-campaigns'


def job_path(base, rid):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,150}', str(rid)):
        raise ValueError('invalid queue request ID')
    return root(base) / 'queue/jobs' / (rid + '.json')


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.' + str(os.getpid()) + '.atomic')
    with tmp.open('w') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path)


def state(base, rid):
    path = root(base) / 'single-clone' / rid / 'state.json'
    return json.loads(path.read_text()) if path.exists() else {}


def terminal(value):
    return value.get('phase') in TERMINAL and bool(value.get('summary', {}).get('campaigns'))


def selected(request, base):
    path = base / 'data/ares/creative-ops/inventory/assets.jsonl'
    refs = {r['asset_id'] for r in request.get('asset_refs', [])}
    names = {f for g in request.get('campaign_groups', []) for f in g['files']}
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    matches = [r for r in rows if r.get('asset_id') in refs or r.get('canonical_filename') in names]
    if refs and {r['asset_id'] for r in matches} != refs:
        raise ValueError('queue media identity coverage mismatch')
    if names and ({r['canonical_filename'] for r in matches} != names or len(matches) != len(names)):
        raise ValueError('queue selected filename coverage mismatch')
    if len(matches) != len({r['asset_id'] for r in matches}):
        raise ValueError('queue selected lineage ambiguous')
    return matches


def dependencies(request, account_id, base=BASE):
    rid = request['request_id']
    if terminal(state(base, rid)):
        return []
    deps = set()
    for row in selected(request, base):
        owner = row.get('reservation_request_id')
        if not owner or owner == rid:
            continue
        previous = state(base, owner)
        origin = previous.get('request') or {}
        if origin and origin.get('source_channel_id') != request['source_channel_id']:
            raise ValueError('queue reservation request partition mismatch')
        if not terminal(previous):
            deps.add(owner)
    directory = root(base) / 'single-clone'
    for path in directory.glob('*/state.json'):
        value = json.loads(path.read_text())
        origin = value.get('request') or {}
        owner = origin.get('request_id')
        if (owner and owner != rid and str(origin.get('account')) == str(account_id)
                and value.get('phase') in ACTIVE):
            waiting = job_path(base, owner)
            other_job = json.loads(waiting.read_text()) if waiting.exists() else {}
            if rid not in other_job.get('dependencies', []):
                deps.add(owner)
    return sorted(deps)


def enqueue(request, command, deps, base=BASE):
    path = job_path(base, request['request_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        job = json.loads(path.read_text()) if path.exists() else {}
        if job and job.get('execution_request', job['request']) != request and job['request'] != request:
            raise ValueError('queue request immutable parameter mismatch')
        if not job:
            job = {'request_id': request['request_id'], 'request': copy.deepcopy(request),
                   'command': command, 'enqueued_at': datetime.now(timezone.utc).isoformat(),
                   'attempts': 0, 'status': 'WAITING', 'notification': None}
        job['dependencies'] = deps
        if job['status'] != 'DELIVERED':
            job['status'] = 'WAITING'
        atomic(path, job)
    return {'status': 'QUEUED', 'request_id': request['request_id'],
            'waiting_for_dependencies': len(deps), 'campaign_writes': 0}


def claim_terminal(request, account_id, base=BASE):
    """Transfer only completed request reservations; readback + history retained."""
    rows = selected(request, base)
    conflicts = [r for r in rows if r.get('reservation_request_id') not in {None, request['request_id']}]
    if not conflicts:
        return
    owners = {r['reservation_request_id'] for r in conflicts}
    accounts = {account_id} | {str(state(base, owner).get('request', {}).get('account')) for owner in owners}
    with ExitStack() as stack:
        for account in sorted(accounts):
            lock = stack.enter_context((root(base) / 'single-clone' / ('account-' + account + '.lock')).open('a+'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if dependencies(request, account_id, base):
            raise BlockingIOError('queue dependency still running')
        from . import shein_single_clone as driver
        from .shein_media_handoff import _ops
        config = json.loads((base / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        common = driver._load_common()
        token, _ = common.get_token_from_1password(config['accounts'][account_id]['token_item'])
        proofs = {}
        for row in conflicts:
            aid = row.get('meta_ad_id')
            if aid:
                h, proof, _ = common.graph_get(aid, token, {'fields': 'id,account_id,campaign_id,status,effective_status,creative{id}'})
                if h != 200 or proof.get('id') != aid:
                    raise ValueError('queue historical ad readback unavailable')
                proofs[row['asset_id']] = proof
        inv = base / 'data/ares/creative-ops/inventory/assets.jsonl'
        with inv.with_suffix(inv.suffix + '.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = [json.loads(x) for x in inv.read_text().splitlines() if x.strip()]
            before = {r['asset_id']: r for r in conflicts}
            for row in current:
                if row.get('asset_id') not in before:
                    continue
                old = before[row['asset_id']]
                if row.get('reservation_request_id') != old['reservation_request_id'] or not terminal(state(base, old['reservation_request_id'])):
                    raise BlockingIOError('queue reservation changed; retry after dependency')
            audit = base / 'data/ares/meta-ads/audit/shein/campaigns/intake' / request['request_id']
            audit.mkdir(parents=True, exist_ok=True)
            backup = audit / 'queue-inventory-before.jsonl'
            if not backup.exists():
                backup.write_bytes(inv.read_bytes()); os.chmod(backup, 0o600)
            for row in current:
                if row.get('asset_id') not in before:
                    continue
                row.setdefault('reservation_history', []).append({
                    'request_id': request['request_id'], 'previous_request_id': row['reservation_request_id'],
                    'at': datetime.now(timezone.utc).isoformat(), 'authority': request['authorized_by'],
                    'reason': 'FIFO queue: prior request terminal; explicit selected-file reuse only',
                    'previous_ad_readback': proofs.get(row['asset_id'])})
                row['reservation_request_id'] = request['request_id']
            _ops(base).atomic_inventory(current)
            after = {r['asset_id']: r for r in selected(request, base)}
            if any(after[aid]['reservation_request_id'] != request['request_id'] for aid in before):
                raise ValueError('queue reservation claim readback mismatch')
            atomic(audit / 'queue-reservation-claim.json', {'request_id': request['request_id'],
                   'previous_requests': sorted(owners), 'asset_ids': sorted(before), 'historical_ads': proofs})


def gate(request, command, base=BASE, *, launch=True):
    operation = json.loads((base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    if not operation.get('request_queue_policy', {}).get('enabled'):
        return None
    from . import shein_single_clone as driver
    from .shein_general import authorize
    account = driver.lookup_account(request['account'])
    profile = json.loads((base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles'][account['account_id']]
    profile = {**profile, 'channel_authorization_policy': operation['channel_authorization_policy']}
    authorize(request, profile, force=True)
    driver.validate_request(driver.apply_request_defaults(copy.deepcopy(request), operation))
    scope = subprocess.run([sys.executable, str(base / 'scripts/mgs-domain-scope.py'),
                            'check', '--agent', 'ares', profile['destination_base']],
                           capture_output=True, timeout=20)
    if scope.returncode:
        raise ValueError('queue operational domain scope rejected')
    deps = dependencies(request, account['account_id'], base)
    if not deps:
        try:
            claim_terminal(request, account['account_id'], base)
            return None
        except BlockingIOError:
            deps = dependencies(request, account['account_id'], base)
    result = enqueue(request, command, deps, base)
    if launch:
        start_worker(base)
    return result


def start_worker(base=BASE):
    directory = root(base) / 'queue'; directory.mkdir(parents=True, exist_ok=True)
    if base == BASE and Path('/etc/systemd/system/ares-shein-request-queue.service').exists():
        subprocess.run(['systemctl', 'start', 'ares-shein-request-queue.service'],
                       capture_output=True, timeout=20, check=True)
        return
    with (directory / 'worker.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
    env = dict(os.environ); env['PYTHONPATH'] = str(base / 'scripts')
    with (directory / 'worker.log').open('ab') as log:
        subprocess.Popen([sys.executable, '-m', 'ares_campaign_v3.shein_request_queue', '--work'],
                         cwd=base, env=env, stdin=subprocess.DEVNULL, stdout=log,
                         stderr=log, start_new_session=True, close_fds=True)


def defer_conflict(request, command, detail, base=BASE):
    if not any(text in detail for text in CONFLICTS):
        return None
    result = gate(request, command, base)
    if result is not None:
        return result
    policy = json.loads((base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    if 'in-flight request' in detail and policy.get('request_queue_policy', {}).get('enabled'):
        result = enqueue(request, command, [], base)
        start_worker(base)
        return result
    return None


def completion_text(s):
    if not terminal(s):
        raise ValueError('queue final notice requires completed request')
    summary = s['summary']; trees = s.get('final_readback') or []
    if not trees:
        raise ValueError('queue completion lacks final readback')
    names = [t['campaign']['name'].split(' - ')[0] for t in trees]
    budget = Decimal(str(summary['budget_usd']))
    statuses = {t['campaign']['status'] for t in trees}
    status = 'ativas' if statuses == {'ACTIVE'} else 'pausadas' if statuses == {'PAUSED'} else 'com status mistos'
    body = (f"✅ Concluído: {len(trees)} campanhas na conta **{s.get('account', {}).get('name') or summary['account_id']}**, "
            f"a partir da campanha {s['request']['source_number']}.\n"
            f"- Campanhas: **{', '.join(names)}** — {status}.\n"
            f"- Orçamento: **US${budget:g}/dia por campanha**, total **US${budget * len(trees):g}/dia**.\n")
    bid = s.get('resolved_request', s['request'])
    if bid.get('bid_strategy') and bid.get('bid_usd'):
        body += f"- Cost per result goal: **US${Decimal(str(bid['bid_usd'])):g}**.\n"
    starts = [a['start_time'] for tree in trees for a in tree.get('adsets', {}).get('data', []) if a.get('start_time')]
    if starts:
        from zoneinfo import ZoneInfo
        zone = (s.get('account') or {}).get('timezone_name')
        if zone:
            dates = sorted({datetime.fromisoformat(x).astimezone(ZoneInfo(zone)).strftime('%d/%m/%Y %H:%M %Z') for x in starts})
            body += '- Início configurado: **' + ' / '.join(dates) + '**; habilitação após QA.\n'
    body += f"- **{summary['ads']} anúncios validados**, com os criativos e textos do pedido.\n"
    if not summary.get('posts_preserved'):
        body += '\nNovos posts, sem herdar a prova social da origem.'
    if summary.get('warnings'):
        body += '\nRessalva: a Meta normalizou flags opcionais de sugestões de idade/gênero; demais configurações conferidas.'
    return body


def find_notice(job, channel, nonce, content, actor, get):
    """Prove presence or absence since the original intent, not just page one."""
    floor_text = job.get('delivery_intent_at') or job.get('enqueued_at')
    floor = datetime.fromisoformat(floor_text) if floor_text else None
    before = None
    seen = set()
    for page_number in range(1, 51):
        path = '/channels/' + channel + '/messages?limit=100'
        if before:
            path += '&before=' + before
        rows = get(path)
        if not isinstance(rows, list):
            raise ValueError('queue notice history incomplete')
        for message in rows:
            if not isinstance(message, dict) or message.get('channel_id') != channel:
                raise ValueError('queue notice history channel mismatch')
            if (message.get('author', {}).get('id') == actor
                    and (str(message.get('nonce')) == nonce or message.get('content') == content)):
                return {'message': message, 'complete': True, 'pages': page_number}
        if len(rows) < 100:
            return {'message': None, 'complete': True, 'pages': page_number}
        dates = [datetime.fromisoformat(m['timestamp']) for m in rows]
        if floor is not None and min(dates) < floor:
            return {'message': None, 'complete': True, 'pages': page_number}
        cursor = str(rows[-1].get('id') or '')
        if not cursor or cursor in seen:
            raise ValueError('queue notice history pagination invalid')
        seen.add(cursor); before = cursor
    raise ValueError('queue notice history coverage limit; no blind resend')


def notify(job, s):
    """Deferred final only, as Ares; reconcile nonce and GET exact sent target."""
    from .shein_channel_authority import _get
    import urllib.request
    verify_final(s)
    channel = str(job['request']['source_thread_id'])
    nonce = 'sq' + re.sub('[^0-9]', '', job['request_id'])[-20:]
    content = job.get('native_completion_content') or completion_text(s)
    actor = _get('/users/@me')['id']
    scan = find_notice(job, channel, nonce, content, actor, _get)
    found = scan['message']
    job['delivery_reconciliation'] = {'complete': scan['complete'], 'pages': scan['pages'],
                                    'found': bool(found), 'checked_at': datetime.now(timezone.utc).isoformat()}
    if job.get('notification'):
        found = _get('/channels/' + channel + '/messages/' + job['notification'])
    if not found:
        if job.get('native_completion_content') and job.get('delivery_intent_at'):
            raise ValueError('queue delivery uncertain; reconcile exact target before any resend')
        if int(job.get('delivery_attempts') or 0) >= 3:
            job['delivery_attention_required'] = True
            atomic(job_path(BASE, job['request_id']), job)
            raise ValueError('queue delivery retry limit; attention required, no duplicate POST')
        if not scan['complete']:
            raise ValueError('queue delivery scan incomplete; no resend')
        import hashlib
        digest = hashlib.sha256(content.encode()).hexdigest()
        if job.get('delivery_payload_sha256') not in {None, digest}:
            raise ValueError('queue delivery payload changed; reconcile before retry')
        job['delivery_payload_sha256'] = digest
        job.setdefault('delivery_intent_at', datetime.now(timezone.utc).isoformat())
        job['delivery_attempts'] = int(job.get('delivery_attempts') or 0) + 1
        job['delivery_last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        atomic(job_path(BASE, job['request_id']), job)
        token = None
        for line in Path('/root/.hermes/profiles/ares/.env').read_text().splitlines():
            key, sep, value = line.strip().partition('=')
            if sep and key == 'DISCORD_BOT_TOKEN': token = value.strip().strip('\"\'')
        if not token: raise ValueError('queue completion identity unavailable')
        payload = {'content': content, 'nonce': nonce, 'enforce_nonce': True,
                   'allowed_mentions': {'parse': []}}
        req = urllib.request.Request('https://discord.com/api/v10/channels/' + channel + '/messages',
              data=json.dumps(payload).encode(), method='POST', headers={
                  'Authorization': 'Bot ' + token, 'Content-Type': 'application/json', 'User-Agent': 'MGS-Ares/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                job['delivery_http'] = response.status
                found = json.load(response)
        except Exception as exc:
            job['delivery_error_type'] = type(exc).__name__
            job['delivery_http'] = getattr(exc, 'code', None)
            if job['delivery_http'] == 429:
                try:
                    detail = json.loads(exc.read())
                    delay = float(detail.get('retry_after', 300))
                    job['delivery_retry_after_epoch'] = time.time() + max(1, min(delay, 3600))
                except (ValueError, TypeError, AttributeError):
                    pass
            atomic(job_path(BASE, job['request_id']), job)
            raise
        job['notification'] = found['id']; atomic(job_path(BASE, job['request_id']), job)
    read = _get('/channels/' + channel + '/messages/' + found['id'])
    if read.get('content') != content or read.get('channel_id') != channel or read.get('author', {}).get('id') != actor:
        raise ValueError('queue final delivery readback mismatch')
    job.update(status='DELIVERED', notification=read['id'], completed_at=s.get('completed_at'))
    job['delivery_confirmed_at'] = datetime.now(timezone.utc).isoformat()
    for key in ['last_error_type', 'retry_after_epoch', 'delivery_error_type',
                'delivery_retry_after_epoch', 'delivery_attention_required']:
        job.pop(key, None)
    atomic(job_path(BASE, job['request_id']), job)


def verify_final(s):
    if not terminal(s):
        raise ValueError('queue completion is not terminal')
    trees = s.get('final_readback') or []
    expected = {x['campaign_id'] for x in s['summary']['campaigns']}
    if not expected or len(trees) != len(expected) or {x['campaign']['id'] for x in trees} != expected:
        raise ValueError('queue final campaign coverage mismatch')
    ads_all = set()
    for tree in trees:
        campaign = tree['campaign']; ads = tree['ads']['data']; adsets = tree['adsets']['data']
        proof = (s.get('media_qa') or {}).get(campaign['id']) or {}
        if (not ads or not adsets or not proof.get('verified')
                or {x['id'] for x in ads} != set(proof.get('ad_ids', []))
                or {x['creative']['id'] for x in ads} != set(proof.get('creative_ids', []))
                or campaign.get('account_id') != str(s['summary']['account_id'])
                or campaign['status'] != s['request']['status']
                or any(x.get('status') != s['request']['status'] for x in ads + adsets)):
            raise ValueError('queue completion QA/status/account mismatch')
        ads_all.update(x['id'] for x in ads)
    if len(ads_all) != int(s['summary']['ads']):
        raise ValueError('queue completion ad coverage mismatch')


def tick(job, base=BASE):
    from . import shein_single_clone as driver
    request = job.get('execution_request') or job['request']; account = driver.lookup_account(request['account'])
    deps = dependencies(request, account['account_id'], base)
    job['dependencies'] = deps
    path = job_path(base, job['request_id'])
    if deps:
        job['status'] = 'WAITING'; atomic(path, job); return
    if float(job.get('retry_after_epoch', 0)) > time.time(): return
    s = state(base, job['request_id'])
    if terminal(s):
        notify(job, s); return
    claim_terminal(request, account['account_id'], base)
    inp = path.with_suffix('.request.json'); atomic(inp, request)
    job['attempts'] += 1; job['status'] = 'RUNNING'; atomic(path, job)
    args = [sys.executable, str(base / 'scripts/ares-shein-campaigns.py'), job['command'], '--input', str(inp), '--confirm-execute']
    p = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    try: result = json.loads(p.stdout)
    except (ValueError, TypeError): result = {'status': 'INVALID_OUTPUT'}
    s = state(base, job['request_id'])
    job['last_status'] = result.get('status'); job['last_error_type'] = result.get('detail', '')[:180]
    if terminal(s):
        notify(job, s); return
    if result.get('status') == 'PRESTAGED_GROUPS_READY':
        ready = base / 'data/ares/meta-ads/audit/shein/campaigns/intake' / job['request_id'] / 'request-ready.json'
        # Keep immutable original plus a separate validated stage input.
        job['execution_request'] = json.loads(ready.read_text()); job['command'] = 'campaign'
    job['status'] = 'WAITING' if result.get('status') == 'QUEUED' else 'RECOVERY_PENDING'
    job['retry_after_epoch'] = time.time() + max(30, int(result.get('retry_after_seconds') or 300))
    atomic(path, job)


def delivery_attention(job):
    """One technical escalation after bounded retries; never an origin warning."""
    if not job.get('delivery_attention_required') or job.get('delivery_alert_intent_at'):
        return
    from .shein_channel_authority import _get
    job['delivery_alert_intent_at'] = datetime.now(timezone.utc).isoformat()
    atomic(job_path(BASE, job['request_id']), job)
    try:
        result = subprocess.run(['bash', str(BASE / 'scripts/send-report-infra-embed.sh'),
            '--action', 'modificada', '--type', 'SHEIN completion delivery recovery',
            '--path', 'SHEIN request ' + job['request_id'],
            '--reason', 'Entrega de conclusão excedeu três tentativas reconciliadas; campanhas concluídas não devem ser reexecutadas.',
            '--evidence', 'Request=' + job['request_id'] + '; conta=' + str(job['request'].get('account', 'n/d'))
                + '; HTTP=' + str(job.get('delivery_http')) + '; conferir somente transporte e aviso na origem.'],
            capture_output=True, text=True, timeout=60)
        match = re.search(r'message_id=(\d+)', result.stdout)
        if result.returncode or not match:
            raise ValueError('queue delivery attention transport unavailable')
        message = _get('/channels/1498132022634483894/messages/' + match.group(1))
        if message.get('content') != '' or not message.get('embeds') or message.get('mentions'):
            raise ValueError('queue delivery attention readback mismatch')
        job['delivery_alert_message_id'] = message['id']
    except Exception as exc:
        job['delivery_alert_error_type'] = type(exc).__name__
    atomic(job_path(BASE, job['request_id']), job)


def work(base=BASE, max_seconds=None):
    directory = root(base) / 'queue'; directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'worker.lock').open('a+') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return
        atomic(directory / 'worker.json', {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
        start = time.monotonic()
        while max_seconds is None or time.monotonic() - start < max_seconds:
            pending = []
            for path in sorted((directory / 'jobs').glob('*.json')):
                if path.name.endswith('.request.json'): continue
                job = json.loads(path.read_text())
                if job.get('status') != 'DELIVERED': pending.append(job)
            if not pending:
                atomic(directory / 'worker.json', {'pid': os.getpid(), 'heartbeat_at': datetime.now(timezone.utc).isoformat(), 'pending': 0})
                time.sleep(30)
                continue
            for job in pending:
                try: tick(job, base)
                except Exception as exc:
                    job.update(status='RECOVERY_PENDING', last_error_type=type(exc).__name__,
                               retry_after_epoch=max(time.time() + 300, float(job.get('delivery_retry_after_epoch') or 0)))
                    atomic(job_path(base, job['request_id']), job)
                    delivery_attention(job)
            atomic(directory / 'worker.json', {'pid': os.getpid(), 'heartbeat_at': datetime.now(timezone.utc).isoformat(), 'pending': len(pending)})
            time.sleep(30)


if __name__ == '__main__':
    if sys.argv[1:] != ['--work']: raise SystemExit('Use --work')
    work()
