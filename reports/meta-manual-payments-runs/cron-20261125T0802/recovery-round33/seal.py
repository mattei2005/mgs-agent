"""Seal this round's verified diagnostics without changing queue or business."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from datetime import datetime, timezone

os.umask(0o077)
B = Path(__file__).parent
ROOT = Path('/root/mgs-agent')
KEY = '79cd082a20c22a736307765f'

def load(p):
    return json.loads(Path(p).read_text())

def save(name, value):
    with (B / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

rec = load(B / 'reconciliation.json')
probe = load(B / 'probe-receipt.json')
release = load(B / 'lease-release.json')
authority = load(B / 'authority-readback.json')
cp = ROOT / 'data/meta-manual-payments/digital-trust-workbook-contract.json'
contract = load(cp)
ledger = load(ROOT / 'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
jobs = load('/root/.hermes/profiles/zeus/cron/jobs.json')
job = next(x for x in (jobs if isinstance(jobs, list) else jobs['jobs']) if x['id'] == '2ee720363d7d')
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select * from requests where key=?', (KEY,)).fetchone())
os.kill(int(row['owner'].split(':')[1]), 0)
heartbeat = json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
related = [dict(r) for r in q.execute('select key,state,owner,due,attempts,failures from requests where key=?', ('ce11800d217d22dba6a58dcc',))]
workers = []
worker_names = {'refresh_workbook.py', 'regroup_funding.py', 'refresh_september_invoices.py', 'record_pc1_proof.py', 'read_pc1_billing_history.py', 'read_pc1_accounts_list.py', 'publish_pay_now.py'}
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name) == os.getpid():
        continue
    try:
        argv = (p / 'cmdline').read_bytes().decode(errors='replace').split('\x00')
    except OSError:
        continue
    for arg in argv:
        if Path(arg).name in worker_names:
            workers.append({'pid': int(p.name), 'worker': Path(arg).name})
            break
with (ROOT / 'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(f, fcntl.LOCK_UN)
cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True)
consumer_lines = [s for s in cron.stdout.splitlines() if not s.lstrip().startswith('#') and 'alerts-infra-failed-alert-resolver' in s]
assert consumer_lines
pending = contract['pending_new_account_fields']['D_account_ids']
assert pending == rec['pending_account_ids']
assert set(pending) <= set(contract['account_ids'])
assert not any(ledger.get(k) for k in pending)
assert not workers and not job.get('fire_claim')
assert hashlib.sha256(cp.read_bytes()).hexdigest() == rec['contract_sha256']
assert job['last_dispatch']['scheduled_at'] == rec['last_dispatch_scheduled_at']
assert release['release_exit'] == 0 and not release['readback']['locked']
assert probe['save_dialog_count'] == 1 and probe['input_actions'] == 0
assert all(item['status'] == 200 for item in authority['messages'])
assert authority['current_registry_rodolfo_authorized']
now = datetime.now(timezone.utc).isoformat()
final = {'observed_at': now, 'job_id': job['id'], 'fire_claim': job.get('fire_claim'), 'last_dispatch_scheduled_at': job['last_dispatch']['scheduled_at'], 'next_run_at': job['next_run_at'], 'writer_lock_free': True, 'financial_workers': workers, 'pending_D': pending, 'pending_H_new_account_fields': contract['pending_new_account_fields']['H_account_ids'], 'pending_ledger_entries_present': [], 'queue': {k: row[k] for k in ['state', 'owner', 'attempts', 'failures', 'due', 'lease_until']}, 'queue_owner_alive': True, 'consumer_heartbeat': heartbeat, 'consumer_schedule': ' '.join(consumer_lines[0].split()[:5]), 'related_later_tick_queue': related}
save('final-state.json', final)
evidence = {
    'operation_key': KEY, 'source_key': row['source_key'], 'mode': 'resume_safe',
    'status': 'waiting_resource', 'cause': 'pc1_save_as_dialog_still_open_preserved', 'observed_at': now,
    'authority': {'receipt': str(B / 'authority-readback.json'), 'original_command_message_id': '1563960055504838767', 'current_scope_message_id': '1575022093777637377', 'recovery_authority_message_id': '1569193434189668453', 'all_authority_gets_http_200': True, 'current_registry_authorized': True},
    'reconciliation': {'receipt': str(B / 'reconciliation.json'), 'final_readback': str(B / 'final-state.json'), 'native_contract_hash': rec['native_contract_hash'], 'later_native_tick_receipt': rec['later_native_tick_receipt'], 'later_tick_missing_layers_not_adopted': rec['later_tick_missing_layers_not_adopted'], 'writer_lock_free': True, 'financial_workers': workers, 'completed_financial_layers_replayed': False, 'live_sheet_revalidation_performed': False},
    'scope': {'sheet_id': contract['sheet_id'], 'mode': contract['recurring_scope']['mode'], 'active_account_count': len(contract['account_ids']), 'pending_stage': 'Historical D explicit Paid card instrument proof only', 'pending_account_ids': pending, 'archived_accounts_excluded': True, 'balance_views_enabled': contract['balance_views']['enabled']},
    'surface': {'receipt': str(B / 'probe-receipt.json'), 'approved_chrome': {k: probe['captures']['approved'][k] for k in ['pid', 'window_id']}, 'approved_active_page_pixels': 'Whats new in AdBlock; Meta Business Suite tab inactive', 'save_as_dialog_confirmed_in_pixels': True, 'unrelated_dialog_preserved': True, 'meta_authentication_challenge_demonstrated': False, 'meta_access_revalidated': False, 'auth_ready_claimed': False, 'vision_inspected_images': ['approved.png', 'save-dialog-0.png'], 'input_actions': 0, 'tabs_created': 0, 'tabs_closed': 0, 'lease_free_readback': True, 'lease_receipt': str(B / 'lease-release.json')},
    'continuity': {'queue_owner': row['owner'], 'queue_owner_alive_at_final_verification': True, 'queue_state': row['state'], 'attempts': row['attempts'], 'failures': row['failures'], 'consumer_heartbeat': heartbeat, 'consumer_schedule': final['consumer_schedule'], 'retry_at': None, 'retry_scheduling_owner': 'Existing supervisor consumes this result and applies resource backoff; worker did not mutate queue or dispatch.', 'next_step': 'Reconcile native claim and both occurrence receipts; reacquire lease and inspect original Chrome/dialogs before input. Preserve unrelated Save As and original tabs. Resume only historical D for these five IDs using actual pixels, canonical narrow record_pc1_proof and exact contract pending-fields/readback. H35/D2 remain under ce11800d217d22dba6a58dcc. Do not repeat completed metrics, funding, invoices, H or business delivery; no old hardcoded adapter.'},
    'side_effects': {'sheet_writes': 0, 'meta_writes': 0, 'payments': 0, 'billing_changes': 0, 'cron_changes': 0, 'delivery_messages': 0, 'infrastructure_modified': False, 'local_diagnostic_artifacts_only': True},
    'business_complete': False, 'delivery_complete': False, 'independent_closure_not_claimed': True,
}
save('recovery-evidence.json', evidence)
manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in B.iterdir() if p.is_file() and p.name != 'probe-private.log'}
save('evidence-sha256.json', manifest)
assert all(hashlib.sha256((B / name).read_bytes()).hexdigest() == digest for name, digest in manifest.items())
assert load(B / 'recovery-evidence.json')['scope']['pending_account_ids'] == pending
print(json.dumps({'checkpoint': str(B / 'recovery-evidence.json'), 'status': evidence['status'], 'pending_ids': pending, 'supervisor': row['owner'], 'supervisor_alive': True, 'lease_free_readback': True, 'hash_readback_valid': True, 'business_writes': 0}))
