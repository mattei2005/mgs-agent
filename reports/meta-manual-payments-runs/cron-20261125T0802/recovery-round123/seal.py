"""Seal actual probe-only evidence; no financial or queue writes."""
import fcntl
import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

B = Path(__file__).parent
ROOT = Path('/root/mgs-agent')
KEY = '79cd082a20c22a736307765f'
os.umask(0o077)

def load(p):
    return json.loads(Path(p).read_text())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(name, value):
    with (B / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

rec = load(B / 'reconciliation.json')
probe = load(B / 'retry-probe-receipt.json')
release = load(B / 'retry-lease-release.json')
assert not probe['errors'] and probe['save_dialog_count'] == 1
assert release['release_exit'] == 0 and not release['readback']['locked']
assert sha(ROOT / 'data/meta-manual-payments/digital-trust-workbook-contract.json') == rec['contract_sha256']
ledger = load(ROOT / 'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
assert all(not ledger.get(k) for k in rec['pending_account_ids'])
with (ROOT / 'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(f, fcntl.LOCK_UN)
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select key,state,cause,owner,attempts,failures,due,lease_until from requests where key=?', (KEY,)).fetchone())
assert row['owner'] == rec['queue']['owner']
os.kill(int(row['owner'].split(':')[1]), 0)
hb = json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
schedule = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True)
schedules = [l for l in schedule.stdout.splitlines() if 'alerts-infra-failed-alert-resolver.py' in l and not l.lstrip().startswith('#')]
assert len(schedules) == 1 and schedules[0].startswith('2-57/5 * * * * ')
now = datetime.now(timezone.utc)
n = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
while n.minute not in range(2, 58, 5):
    n += timedelta(minutes=1)
later = load(rec['later_native_tick_receipt'])
assert sha(rec['later_native_tick_receipt']) == rec['later_native_tick_receipt_sha256']
assert later['scheduled_at'] == '2026-11-26T08:02:00-05:00'
related_keys = [x['key'] for x in rec['later_tick_queue']] + ['6373afb33275674610c06b6a', 'ce11800d217d22dba6a58dcc']
related = [dict(q.execute('select key,state,cause,owner,attempts,failures from requests where key=?', (key,)).fetchone()) for key in related_keys]
visual = {
    'inspected_with': 'vision_analyze',
    'authentication_gate_on_approved_surface': True,
    'authentication_gate_text': 'Confirm it’s you with your passkey',
    'profile_visible': 'Rodolfo Mattei · Facebook',
    'expected_business_id_in_encoded_destination': '155263197283282',
    'billing_accounts_access_confirmed': False,
    'historical_D_access_confirmed': False,
    'page_error_visible': False,
    'native_save_as_dialog_confirmed': True,
    'dialog_preserved': True,
    'browser_tabs_visible': 6,
    'no_tab_mutation_by_this_probe': True,
    'captures': probe['captures'],
    'basis': 'Both current screenshots inspected by vision_analyze. Approved Chrome visibly displays passkey reauthentication, not Accounts. AX confirms Rodolfo and the passkey fallback description. Save As remains independently open.',
}
save('visual-verification.json', visual)
final = {
    'observed_at': now.isoformat(), 'queue': row, 'owner_alive': True,
    'heartbeat': hb, 'consumer_schedule': '2-57/5 * * * *',
    'next_scheduled_consumer_check_utc': n.isoformat(),
    'retry_time_not_guaranteed': True,
    'writer_lock_free': True, 'lease_free_readback': True,
    'contract_unchanged_from_preflight': True,
    'pending_ledger_entries_still_absent': True,
    'later_tick_queues': related,
    'latest_native_receipt': rec['later_native_tick_receipt'],
    'latest_native_status': later['status'],
    'latest_native_claim_reconciled_no_replay': True,
}
save('final-state.json', final)
evidence = {
    'operation_key': KEY,
    'source_key': 'native:zeus:2ee720363d7d:20261125T0802:historical-d',
    'mode': 'probe_only', 'status': 'waiting_human',
    'cause': 'meta_passkey_authentication_required',
    'secondary_resource_gate': 'pc1_save_as_dialog_present_preserved',
    'observed_at': now.isoformat(),
    'authority_receipt': str(B / 'authority-readback.json'),
    'reconciliation_receipt': str(B / 'reconciliation.json'),
    'sheet_readback': str(B / 'sheet-readback.json'),
    'final_readback': str(B / 'final-state.json'),
    'native_contract_hash': rec['native_contract_hash'],
    'scope': {
        'sheet_id': 794137639, 'active_account_count': rec['active_account_count'],
        'exact_live_ids_verified': rec['exact_live_ids_verified'],
        'pending_account_ids': rec['pending_account_ids'],
        'pending_stage': 'D historical explicit Paid card instrument proofs ONLY',
        'new_account_D_separate_not_adopted': '1770569568407466',
        'archived_accounts_excluded': True,
    },
    'visual_readback': visual, 'continuity': final,
    'side_effects': {
        'input_actions': 0, 'tabs_created': 0, 'tabs_closed': 0,
        'sheet_writes': 0, 'meta_writes': 0, 'payments': 0,
        'billing_changes': 0, 'cron_changes': 0,
        'business_delivery_messages': 0, 'queue_mutations': 0,
        'canonical_infrastructure_modified': False,
        'local_diagnostic_artifacts_only': True,
    },
    'auth_ready': False,
    'auth_ready_reason_not_emitted': 'Explicit passkey reauthentication challenge is visible in the approved Rodolfo Chrome; Save As also persists. No positive target-access proof.',
    'next_step': 'Human authenticates Meta in approved Chrome PC1 and resolves the unrelated Save As dialog locally without automation dismissing it. Existing supervisor retains ownership/backoff and must read-only revalidate same surface/dialogs. Only after both gates clear, reconcile later native receipts and collect the same five historical D proofs. No replay of completed financial layers or duplicate delivery; other occurrences remain independent.',
    'public_auth_notice': 'Não consegui concluir. Você precisa autenticar a Meta no Chrome do PC1.',
    'public_auth_notice_send_by_this_probe': False,
    'business_complete': False, 'delivery_complete': False,
    'independent_closure_not_claimed': True,
}
save('recovery-evidence.json', evidence)
hashes = {p.name: sha(p) for p in sorted(B.iterdir()) if p.is_file() and p.name != 'evidence-sha256.json'}
save('evidence-sha256.json', hashes)
assert all(sha(B / name) == h for name, h in load(B / 'evidence-sha256.json').items())
print(json.dumps({'checkpoint': str(B / 'recovery-evidence.json'), 'status': evidence['status'], 'cause': evidence['cause'], 'mode': evidence['mode'], 'hashes_verified': True, 'lease_free': True, 'owner_alive': True, 'pending_D_ids': rec['pending_account_ids'], 'next_scheduled_consumer_check_utc': n.isoformat(), 'auth_ready': False}))
