"""Delivery-only adapter for the frozen Digital Trust recovery.

Never recollects Meta/PC1 or writes Sheets. Independent observation requires
exact live workbook parity and GET of the persisted, frozen source-thread report.
"""
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import time

from mgs_automation_continuity import native_contract_hash
from mgs_dtr_continuity import atomic

BASE = Path('/root/mgs-agent')
KEY = '9f77ed97faf39eb7de4ba1b3'
JOB = '2ee720363d7d'
SOURCE = 'native:zeus:' + JOB
THREAD = '1563926766286803004'
HASH = 'c65030328baacc9d414c5d3346f1a31a98a24fede8e56d2a4523d5561366f682'
RUN = Path('reports/meta-manual-payments-runs/cron-20261108T2102')


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scope(job):
    return (job.get('id') == JOB and job.get('enabled') is True
            and job.get('state') not in ('paused', 'completed')
            and not job.get('fire_claim') and native_contract_hash(job) == HASH)


def authored(sheet):
    # Ignore volatile effective values/formatting, not authored formulas or notes.
    result = {k: v for k, v in sheet.items() if k != 'data'}
    result['data'] = []
    for grid in sheet.get('data', []):
        rows = []
        for row in grid.get('rowData', []):
            cells = [{k: v for k, v in cell.items() if k in (
                'userEnteredValue', 'note', 'userEnteredFormat', 'textFormatRuns')}
                for cell in row.get('values', [])]
            while cells and not cells[-1]:
                cells.pop()
            rows.append({'values': cells} if cells else {})
        while rows and not rows[-1]:
            rows.pop()
        result['data'].append({'rowData': rows})
    return result


def read_workbook(contract):
    import mgs_google_workspace_auth as g
    import os
    g.load_env()
    selectors = ('ARES_DRIVE_AUTH_MODE', 'MGS_DRIVE_AUTH_PRIMARY',
                 'MGS_GOOGLE_SHEETS_AUTH_MODE', 'MGS_META_APP_ROLES_GOOGLE_AUTH_MODE')
    if not all(os.getenv(k) == 'service_account' for k in selectors):
        raise ValueError('Google corporate authentication selectors mismatch')
    sa = g.load_service_account()
    if (sa['client_email'], sa['project_id']) != (
            'mgsagent@mgs-core-prod.iam.gserviceaccount.com', 'mgs-core-prod'):
        raise ValueError('Google corporate identity mismatch')
    token = g.service_account_access_token()
    code, book = g.api_json('GET', 'https://sheets.googleapis.com/v4/spreadsheets/'
                           + contract['spreadsheet_id'] + '?includeGridData=true',
                           token, quota_project='mgs-core-prod')
    if code != 200:
        raise ValueError('Live workbook read unavailable: HTTP ' + str(code))
    return book


def validate(base=BASE, reader=read_workbook):
    root = base / RUN
    receipt = load(root / 'recovery-financial-validation.json')
    contract = load(base / 'data/meta-manual-payments/digital-trust-workbook-contract.json')
    if (receipt['continuity_key'] != KEY or receipt['accounts'] != 47
            or receipt['fresh_metrics_count'] != 47 or receipt['fresh_h_count'] != 36
            or receipt['pending_ui'] or contract['thread_id'] != THREAD
            or contract['business_id'] != '155263197283282'
            or contract['spreadsheet_id'] != '1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU'
            or contract['sheet_id'] != 271321738):
        raise ValueError('Frozen financial recovery scope incomplete')
    for name in ('source_to_live_sheet_cgij_exact', 'invoice_source_to_live_sheet_ef_exact',
                 'h_source_to_live_sheet_and_note_exact', 'd_ledger_to_live_sheet_exact',
                 'h_original_collection_times_preserved', 'other_sheet_data_unchanged'):
        if receipt.get(name) is not True:
            raise ValueError('Financial validation gate missing: ' + name)
    if any(receipt.get(k) != 0 for k in ('payments_executed', 'billing_changes', 'meta_writes', 'cron_changes')):
        raise ValueError('Recovery safety gate mismatch')
    frozen = load(root / 'recovery-final-workbook-0114.json')
    live = reader(contract)
    before = {s['properties']['sheetId']: s for s in frozen['sheets']}
    after = {s['properties']['sheetId']: s for s in live['sheets']}
    if set(before) != set(after) or any(authored(before[k]) != authored(after[k]) for k in before):
        raise ValueError('Live workbook changed from validated financial snapshot; no replay')
    ids = []
    for grid in after[contract['sheet_id']].get('data', []):
        for row in grid.get('rowData', []):
            cells = row.get('values', [])
            match = re.search(r'^ID da conta: (\d+)\b', cells[0].get('note', '')) if cells else None
            if match:
                ids.append(match[1])
            # Effective calculated monetary values must also match, not just formulas.
    if len(ids) != 47 or len(set(ids)) != 47 or set(ids) != set(contract['account_ids']):
        raise ValueError('Live authorized account set mismatch')
    for old_grid, new_grid in zip(before[contract['sheet_id']]['data'], after[contract['sheet_id']]['data']):
        for old_row, new_row in zip(old_grid.get('rowData', []), new_grid.get('rowData', [])):
            for old_cell, new_cell in zip(old_row.get('values', []), new_row.get('values', [])):
                if old_cell.get('effectiveValue') != new_cell.get('effectiveValue'):
                    raise ValueError('Live calculated financial value mismatch')
    return receipt, contract


def render(receipt, contract):
    times = sorted(datetime.fromisoformat(t) for t in receipt['h_read_times'].values())
    return ("Atualização de 08/11 às 21h02 recuperada e validada.\n\n"
            "47/47 contas: 11 no cartão e 36 na linha. Métricas renovadas em 09/11 às 01h14 Eastern.\n"
            f"H: 36/36 saldos da lista Accounts, lidos entre {times[0]:%d/%m %Hh%M} e {times[-1]:%d/%m %Hh%M} Eastern; horários preservados, sem republicação. Não são valores de modal.\n"
            "Média diária: 06–08/11 completos. Gasto de novembro: 01–09/11, incluindo o dia local parcial.\n"
            "Invoices de outubro: 29 pendentes, US$ 417.702,93. Outra invoice de US$ 161,18 permanece fora das 47 contas e dos totais.\n\n"
            "D: pendências recentes resolvidas; nenhuma em pending_ui. Permanecem 35 campos históricos vazios: 34 sem prova do instrumento e Growpowerhub-US-SHEIN-EN-04-G004 sem cobrança localizada. Vazio não significa zero.\n\n"
            "IDs, grupos, fontes, links, notas, fórmulas e totais conferidos; outra aba preservada. Nenhum pagamento ou alteração de billing, orçamento ou cadência.\n\n"
            'https://docs.google.com/spreadsheets/d/' + contract['spreadsheet_id']
            + '/edit#gid=' + str(contract['sheet_id']))


def resume(job, *, base=BASE, reader=read_workbook, transport=None, verify_only=False):
    if not scope(job):
        raise ValueError('Original job changed, paused, active or unavailable; no delivery')
    root = base / RUN
    with (root / 'financial-delivery.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt, contract = validate(base, reader)
        path = root / 'financial-delivery.json'
        if path.exists():
            state = load(path)
            if state['snapshot_sha256'] != sha(root / 'recovery-final-workbook-0114.json'):
                raise ValueError('Frozen delivery snapshot drift')
        else:
            if verify_only:
                raise ValueError('Source-thread business delivery not yet registered')
            state = {'continuity_key': KEY, 'status': 'PENDING', 'channel_id': THREAD,
                     'snapshot_sha256': sha(root / 'recovery-final-workbook-0114.json'),
                     'payload': {'content': render(receipt, contract), 'embeds': [],
                                 'allowed_mentions': {'parse': [], 'users': [], 'roles': [], 'replied_user': False},
                                 'nonce': KEY, 'enforce_nonce': True}, 'message_id': None}
            atomic(path, state)
        if state['channel_id'] != THREAD or state['continuity_key'] != KEY:
            raise ValueError('Delivery target mismatch')
        if verify_only and not state.get('message_id'):
            raise ValueError('No accepted business report to GET-verify')
        if state.get('post_started') and not state.get('message_id'):
            # A lost POST response is ambiguous: never send a second report.
            from mgs_alert_transport import request, collection_url
            messages = request('GET', collection_url(THREAD) + '?limit=100')
            matches = [m for m in messages if str(m.get('nonce')) == KEY and m.get('content') == state['payload']['content']]
            if len(matches) != 1:
                raise ValueError('Ambiguous prior POST; preserve pending delivery without repost')
            state['message_id'] = str(matches[0]['id'])
            atomic(path, state)
        if transport is None:
            from mgs_alert_transport import post_verified
            transport = post_verified
        if not state.get('message_id'):
            state['post_started'] = time.time()
            atomic(path, state)
        def accepted(mid):
            state['message_id'] = mid
            atomic(path, state)
        mid = transport(state['payload'], channel=THREAD, prior_id=state.get('message_id'), on_created=accepted)
        state.update(message_id=mid, status='GET_VERIFIED', verified_at=time.time())
        atomic(path, state)
        return {'status': 'OK', 'verified': True, 'target': SOURCE,
                'receipt': str(path), 'at': state['verified_at'],
                'message_id': mid, 'source': {'kind': 'native', 'profile': 'zeus',
                'job_id': JOB, 'thread_id': THREAD, 'contract_hash': HASH}}


def observation(job, *, base=BASE):
    try:
        if not scope(job) or not (base / RUN / 'financial-delivery.json').exists():
            return None
        receipt = load(base / RUN / 'recovery-financial-validation.json')
        # Never certify a different, later scheduled slot using this recovery.
        last = datetime.fromisoformat(job['last_run_at']).timestamp()
        if last > datetime.fromisoformat(receipt['validated_metrics_at']).timestamp():
            return None
        return resume(job, base=base, verify_only=True)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        return None
