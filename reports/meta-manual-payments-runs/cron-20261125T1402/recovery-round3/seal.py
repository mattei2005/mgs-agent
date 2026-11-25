"""Seal observed resource contention; leave queue transitions to supervisor."""
import os, sys, json, hashlib, sqlite3, subprocess, shutil, importlib.util
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B = Path(__file__).parent
ROOT = Path('/root/mgs-agent')
KEY = 'ce11800d217d22dba6a58dcc'
def load(p):
    return json.loads(Path(p).read_text())
def save(n, value):
    with (B / n).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
rec = load(B / 'reconciliation.json')
probe = load(B / 'probe-receipt.json')
lease = load(B / 'lease-release.json')
assert probe['save_dialog_count'] == 1 and probe['input_actions'] == 0
assert lease['release_exit'] == 0 and not lease['readback']['locked']
R = Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0, str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
spec = importlib.util.spec_from_file_location('resolver', ROOT / 'scripts/alerts-infra-failed-alert-resolver.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
status, msg = m.discord_api(m.load_token(), 'GET', '/channels/1563926766286803004/messages/1563960022252392459')
assert status == 200 and msg['id'] == '1563960022252392459'
assert msg['channel_id'] == '1563926766286803004' and msg['author']['id'] == '1496296175014252634'
save('original-command-context.json', {'status': status, 'id': msg['id'], 'channel_id': msg['channel_id'], 'author_id': msg['author']['id'], 'content': msg['content']})
c = load(ROOT / 'data/meta-manual-payments/digital-trust-workbook-contract.json')
hl = load(ROOT / 'data/meta-manual-payments/pc1-pay-now-ledger.json').get('accounts', {})
dl = load(ROOT / 'data/meta-manual-payments/pc1-card-ledger.json').get('accounts', {})
hproof = {k: {z: v for z, v in hl.get(k, {}).items() if z in ['read_at', 'source', 'amount', 'receipt']} for k in rec['pending_H_account_ids']}
dproof = {k: {z: v for z, v in dl.get(k, {}).items() if z in ['read_at', 'source', 'receipt', 'verified_at']} for k in rec['pending_recent_D_account_ids']}
prep = Path(rec['h_prepare'])
receipts = sorted(str(p) for p in prep.glob('*-receipt.json'))
vm = load(prep / 'visual-verification.json') if (prep / 'visual-verification.json').exists() else {}
assert not receipts and not vm.get('verified_account_ids', []), 'new H progress requires reconciliation'
slot = datetime.fromisoformat(rec['scheduled_at'])
assert all(datetime.fromisoformat(p['read_at']) < slot for p in hproof.values())
assert all(datetime.fromisoformat(p['read_at']) < slot for p in dproof.values())
jobs = load('/root/.hermes/profiles/zeus/cron/jobs.json')
j = next(x for x in (jobs if isinstance(jobs, list) else jobs['jobs']) if x['id'] == '2ee720363d7d')
assert not j.get('fire_claim') and j['last_dispatch']['scheduled_at'] == rec['scheduled_at']
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select * from requests where key=?', (KEY,)).fetchone())
assert row['state'] == 'running' and row['owner'] == rec['queue_owner']
os.kill(int(row['owner'].split(':')[1]), 0)
hb = json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True)
consumers = [x for x in cron.stdout.splitlines() if not x.lstrip().startswith('#') and 'alerts-infra-failed-alert-resolver' in x]
assert len(consumers) == 1
surface = {'approved_active_page': 'Whats new in AdBlock', 'meta_business_suite_tab_inactive_visible': True, 'meta_billing_tab_identity_not_established_by_pixels': True, 'human_save_as_dialog_open_pixels': True, 'authentication_gate_proved': False, 'auth_ready_proved': False, 'dialog_preserved': True, 'screenshots_inspected': [str(B / 'approved.png'), str(B / 'save-dialog-0.png')]}
e = {'observed_at': datetime.now(timezone.utc).isoformat(), 'operation_key': KEY, 'source_key': rec['source_key'], 'mode': 'resume_safe', 'status': 'waiting_resource', 'cause': 'pc1_human_save_as_dialog_still_open', 'scheduled_at': rec['scheduled_at'], 'native_contract_hash': rec['native_contract_hash'], 'authority_receipt': str(B / 'authority-readback.json'), 'original_command_context': str(B / 'original-command-context.json'), 'active_account_ids': c['account_ids'], 'pending_H_account_ids': rec['pending_H_account_ids'], 'pending_recent_D_account_ids': rec['pending_recent_D_account_ids'], 'historical_D_separate_request': '79cd082a20c22a736307765f', 'historical_D_not_adopted': rec['historical_D_not_adopted'], 'completed_financial_layers_preserved': rec['completed_layers'], 'h_prepare': str(prep), 'h_prepare_existing_receipts': receipts, 'h_prepare_verified_ids': vm.get('verified_account_ids', []), 'H_current_ledger_proofs': hproof, 'D_current_ledger_proofs': dproof, 'later_native_tick_observed': False, 'surface': surface, 'input_actions': 0, 'tabs_created': 0, 'tabs_closed': 0, 'business_writes': 0, 'payments': 0, 'billing_changes': 0, 'cron_changes': 0, 'infrastructure_changes': 0, 'gateway_restarts': 0, 'completed_layers_replayed': False, 'live_sheet_revalidation_performed': False, 'lease_free_readback': True, 'queue_owner': row['owner'], 'queue_owner_alive': True, 'queue_state_at_seal': row['state'], 'consumer_heartbeat': hb, 'consumer_schedule': ' '.join(consumers[0].split()[:5]), 'queue_transition_owner': 'existing supervisor; no direct queue write', 'next_step': 'Supervisor applies resource backoff. Revalidate original Chrome and human dialog without dismissing it, reconcile claim and latest H/D ledgers, then collect only missing H35 and current D2. Preserve completed layers and separate historical D5 executor. Canonical exact-occurrence delivery only after recovery and independent validation.'}
save('recovery-evidence.json', e)
manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in B.iterdir() if p.is_file() and p.name not in ['probe-private.log', 'seal-private.log']}
save('evidence-sha256.json', manifest)
assert all(hashlib.sha256((B / n).read_bytes()).hexdigest() == h for n, h in load(B / 'evidence-sha256.json').items())
assert load(B / 'recovery-evidence.json')['source_key'] == row['source_key']
print(json.dumps({'status': e['status'], 'checkpoint': str(B / 'recovery-evidence.json'), 'pending_H_count': len(hproof), 'pending_D': list(dproof), 'lease_free': True, 'hashes_verified': True, 'consumer_schedule': e['consumer_schedule'], 'queue_owner_alive': True, 'business_writes': 0}, ensure_ascii=False))
