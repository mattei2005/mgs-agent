"""Read-only recovery reconciliation; records local evidence only."""
import os, sys, json, re, sqlite3, hashlib, fcntl
from pathlib import Path
from datetime import datetime
from decimal import Decimal
sys.path.insert(0, '/root/mgs-agent/scripts')
sys.path.insert(0, '/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
import publish_pay_now as publisher
from mgs_finance_continuity import read_workbook, RECOVERIES
from mgs_automation_continuity import native_contract_hash
B = Path(__file__).parent
H = Path('/root/mgs-agent/data/meta-manual-payments')
KEY = 'd32ee972e0e2f228f2105773'
old = json.loads((B/'recovery-progress-20261118T094857.json').read_text())
c = json.loads((H/'digital-trust-workbook-contract.json').read_text())
j = next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id'] == '2ee720363d7d')
assert j['enabled'] and not j.get('fire_claim')
assert native_contract_hash(j) == old['contract_hash']
assert set(c['account_ids']) and len(set(c['account_ids'])) == 55
assert len(set(c['pay_now_account_ids'])) == 40
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
own = dict(q.execute('select key,state,owner,lease_until,due,attempts,failures from requests where key=?', (KEY,)).fetchone())
assert own['state'] == 'running'
os.kill(int(own['owner'].split(':')[1]), 0)
later_owner = dict(q.execute('select key,state,owner,due from requests where key=?', ('ebaa2482101e0f4757c25454',)).fetchone())
assert later_owner['state'] != 'running'
entries_by_run = {}
hashes = {}
for run in (Path(old['h_run_dir']), Path(old['current_H_ledger']['run_dir'])):
    v = json.loads((run/'visual-verification.json').read_text())
    targets = json.loads((run/'targets.json').read_text())
    assert set(v['verified_account_ids']) == set(v['accounts_list_checks'])
    entries = {}
    for t in targets:
        aid = t['account_id']
        if aid not in v['verified_account_ids']:
            continue
        rp = run/(aid+'-receipt.json')
        entries[aid] = publisher.verified_entry(json.loads(rp.read_text()), t, c, v, rp)
        hashes[str(rp)] = hashlib.sha256(rp.read_bytes()).hexdigest()
    entries_by_run[str(run)] = entries
own_entries = entries_by_run[old['h_run_dir']]
assert set(own_entries) == set(old['verified_account_ids_H'])
latest = {}
for entries in entries_by_run.values():
    for aid, e in entries.items():
        if aid not in latest or datetime.fromisoformat(e['read_at']) > datetime.fromisoformat(latest[aid]['read_at']):
            latest[aid] = e
ledger = json.loads((H/'pc1-pay-now-ledger.json').read_text())
with (H/'writer.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    book = read_workbook(c)
    fcntl.flock(lock, fcntl.LOCK_UN)
rows = next(s for s in book['sheets'] if s['properties']['sheetId'] == c['sheet_id'])['data'][0]['rowData']
byid = {}
for row in rows:
    cells = row.get('values', [])
    if cells and (m := re.search(r'^ID da conta: (\d+)\b', cells[0].get('note', ''))):
        byid[m[1]] = cells
assert set(byid) == set(c['account_ids'])
for aid in ledger['fresh_account_ids']:
    e = ledger['accounts'][aid]
    assert Decimal(str(byid[aid][7]['userEnteredValue']['numberValue'])) == Decimal(e['amount'])
    assert e['read_at'] in byid[aid][7]['note'] and e['receipt'] in byid[aid][7]['note']
chrome = json.loads((B/'recovery-surface-1012-elements.json').read_text())
native = json.loads((B/'native-capture-1013-elements.json').read_text())
cl = [e.get('label', '') for e in chrome.get('elements', [])]
nl = [e.get('label', '') for e in native.get('elements', [])]
assert 'Rodolfo' in cl
assert 'Windows Security' in nl and 'Passkey for accounts.meta.com' in nl
assert not Path('/root/.hermes/shared/locks/pc1-computer-use.json').exists()
now = datetime.now().astimezone().isoformat()
result = {
    'continuity_key': KEY, 'source_key': old['source_key'], 'mode': 'resume_safe',
    'state': 'waiting_human_native_passkey_dialog', 'verified_at': now,
    'business_refresh_complete': False, 'delivery_pending': True,
    'original_occurrence_scope_preserved': True,
    'authority_live_GET_revalidated': ['1569193434189668453', '1563960345826037821', '1570799435502588027', '1570815017794674749'],
    'context_proposal_live_GET': '1570814427081736268',
    'native_contract_hash': native_contract_hash(j),
    'ownership': own, 'supervisor_alive': True, 'later_occurrence_owner': later_owner,
    'h_run_dir': old['h_run_dir'], 'own_H_verified_count': len(own_entries),
    'own_verified_H_ids': sorted(own_entries),
    'pending_account_ids_H': [a for a in c['pay_now_account_ids'] if a not in own_entries],
    'pending_account_ids_D': old['pending_account_ids_D'],
    'cross_occurrence_evidence_reconciled': {
        'qualification': 'Existing canonical verified receipts only, no collection/publication in this round. Not completion or merging of distinct occurrences.',
        'run_counts': {r: len(e) for r, e in entries_by_run.items()},
        'union_verified_count': len(latest),
        'freshest_verified_evidence_by_id': latest,
        'missing_any_verified_evidence_ids': [a for a in c['pay_now_account_ids'] if a not in latest],
        'receipt_sha256': hashes,
        'required_before_resume': 'Reconcile exact source and read_at per ID; preserve newer published evidence. Do not blindly replay own pending16 if later same-scope evidence is reusable.'
    },
    'sheets_GET_readback': {'authorized_accounts': len(byid), 'published_H_count': len(ledger['fresh_account_ids']), 'published_H_values_notes_times_exact': True},
    'human_gate': {
        'kind': 'native_windows_security_passkey', 'domain': 'accounts.meta.com',
        'native_pid': 26172, 'native_window_id': 66778,
        'native_screenshot': str(B/'native-capture-1013.png'),
        'native_elements': str(B/'native-capture-1013-elements.json'),
        'native_pixels_inspected': True,
        'chrome_pid': 18704, 'chrome_window_id': 983880,
        'chrome_screenshot': str(B/'recovery-surface-1012.png'),
        'chrome_elements': str(B/'recovery-surface-1012-elements.json'),
        'chrome_pixels_inspected': True, 'profile_Rodolfo_AX': True,
        'accounts_business_id_pixels': '155263197283282',
        'Accounts_page_still_rendered': True,
        'global_facebook_logout_not_proven': True,
        'browser_binding_not_changed': True,
        'recommendation': 'Human concludes or closes active native Windows Security passkey dialog on PC1; then probe_only exact Chrome/native surfaces, without inputs or bypass, before any authorized resume.'
    },
    'completed_layers_preserved': old['completed_layers_preserved'],
    'pending_layers': ['H_remaining_or_reconciled_freshest_evidence_publication', 'D5_instrument_verification', 'final_API_reconciliation', 'full_source_to_live_validation', 'canonical_occurrence_adapter_and_idempotent_delivery_GET'],
    'canonical_delivery_adapter_registered': KEY in RECOVERIES,
    'pc1_lease_free': True,
    'queue_mutated_by_worker': False,
    'next_action_owner': 'Existing supervisor after consuming this result; waiting_human and read-only probe_only. No business retry while native dialog remains.',
    'retry_at': None,
    'mutations': {'sheet_writes': 0, 'meta_writes': 0, 'payments': 0, 'billing_changes': 0, 'cron_changes': 0, 'gateway_restarts': 0, 'business_messages': 0, 'infra_code_config_data_changes': 0},
    'previous_checkpoint': str(B/'recovery-progress-20261118T094857.json')
}
p = B/('recovery-gate-'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
assert not p.exists()
p.write_text(json.dumps(result, ensure_ascii=False, indent=2)); os.chmod(p, 0o600)
assert json.loads(p.read_text()) == result
for name in ['recovery-surface-1012.png', 'recovery-surface-1012-elements.json', 'native-capture-1013.png', 'native-capture-1013-elements.json']:
    os.chmod(B/name, 0o600)
print(json.dumps({'status': result['state'], 'checkpoint': str(p), 'own_verified_H': len(own_entries), 'reconciled_union_H': len(latest), 'missing_any_H': result['cross_occurrence_evidence_reconciled']['missing_any_verified_evidence_ids'], 'published_H_GET_verified': len(ledger['fresh_account_ids']), 'pending_D': len(old['pending_account_ids_D']), 'pc1_lease_free': True, 'supervisor_alive': True, 'writes': 0}, ensure_ascii=False))
