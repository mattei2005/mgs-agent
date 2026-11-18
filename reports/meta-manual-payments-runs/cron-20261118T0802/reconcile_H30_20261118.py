"""Read-only recovery evidence validation; no business writes or delivery."""
import sys, json, os, re, sqlite3, hashlib, fcntl
from pathlib import Path
from datetime import datetime
from decimal import Decimal
sys.path.insert(0, '/root/mgs-agent/scripts')
sys.path.insert(0, '/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
import publish_pay_now as publisher
from mgs_finance_continuity import read_workbook
from mgs_automation_continuity import native_contract_hash
B = Path(__file__).parent
H = Path('/root/mgs-agent/data/meta-manual-payments')
c = json.loads((H/'digital-trust-workbook-contract.json').read_text())
j = next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id'] == '2ee720363d7d')
assert j['enabled'] and j.get('fire_claim') is None
assert native_contract_hash(j) == '825a7653aa8782fbbe23c0d2167eac26cfe36f00bad778f0146d9f746bffd921'
assert len(set(c['account_ids'])) == 55
R = Path('/root/mgs-agent/reports/meta-manual-payments-runs/pay-now-20261118T080600211382')
v = json.loads((R/'visual-verification.json').read_text())
ts = json.loads((R/'targets.json').read_text())
assert len(v['verified_account_ids']) == len(set(v['verified_account_ids'])) == 30
assert set(v['verified_account_ids']) == set(v['accounts_list_checks'])
entries = {}
for t in ts:
    aid = t['account_id']
    if aid not in v['verified_account_ids']: continue
    rp = R/(aid+'-receipt.json')
    entries[aid] = publisher.verified_entry(json.loads(rp.read_text()), t, c, v, rp)
previous = json.loads((B/'recovery-progress-H12-20261118T0935.json').read_text())
published = set(previous['H_recovery']['verified_h_ids'])
assert published <= entries.keys()
ledger = json.loads((H/'pc1-pay-now-ledger.json').read_text())
with (H/'writer.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    book = read_workbook(c)
    fcntl.flock(lock, fcntl.LOCK_UN)
rows = next(s for s in book['sheets'] if s['properties']['sheetId'] == c['sheet_id'])['data'][0]['rowData']
byid = {}
for row in rows:
    cells = row.get('values', [])
    if cells and (m := re.search(r'^ID da conta: (\d+)\b', cells[0].get('note',''))): byid[m[1]] = cells
assert set(byid) == set(c['account_ids'])
for aid in published:
    e = entries[aid]
    assert ledger['accounts'][aid]['receipt'] == e['receipt']
    assert Decimal(str(byid[aid][7]['userEnteredValue']['numberValue'])) == Decimal(e['amount'])
    assert e['read_at'] in byid[aid][7]['note'] and e['receipt'] in byid[aid][7]['note']
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
own = dict(q.execute('select key,state,owner,lease_until,due,attempts,failures from requests where key=?', ('ebaa2482101e0f4757c25454',)).fetchone())
assert own['state'] == 'running'
os.kill(int(own['owner'].split(':')[1]), 0)
lockfile = Path('/root/.hermes/shared/locks/pc1-computer-use.json')
assert not lockfile.exists(), 'pc1_not_free'
pending = [a for a in c['pay_now_account_ids'] if a not in entries]
now = datetime.now().astimezone().isoformat()
result = {'continuity_key':own['key'], 'source_key':'native:zeus:2ee720363d7d:20261118T0802', 'mode':'resume_safe', 'state':'partial_H30_verified_H12_published', 'verified_at':now, 'business_refresh_complete':False, 'delivery_pending':True, 'h_run_dir':str(R), 'canonical_evidence_validation_pass':True, 'scope_accounts':55, 'h_targets':40, 'h_verified_count':len(entries), 'h_published_readback_count':len(published), 'h_new_verified_unpublished_count':len(set(entries)-published), 'verified_h_ids':sorted(entries), 'published_h_ids':sorted(published), 'verified_unpublished_h_ids':sorted(set(entries)-published), 'pending_account_ids_H':pending, 'pending_account_ids_D':previous['pending_account_ids_D'], 'pending_layers':['H10_missing_Accounts_reads','publish_only_missing_verified_H_without_replaying_H12','D7_historical_instrument_verification','final_API_reconciliation_and_full_validation','canonical_occurrence_adapter_and_idempotent_delivery_GET'], 'authority_revalidated_GET':['1569193434189668453','1563960345826037821','1570799435502588027','1570815017794674749'], 'preceding_context_GET':['1570814427081736268','1570790402829586575'], 'native_contract_hash':native_contract_hash(j), 'ownership':own, 'supervisor_alive':True, 'queue_mutated_by_worker':False, 'next_retry_at':None, 'next_retry_owner':'Current supervisor after result consumption', 'pc1_lease_free':True, 'auth_gate_observed':False, 'same_Chrome_profile_BM_verified':True, 'mutations':{'new_receipts_and_visual_checks':18,'sheet_writes':0,'meta_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'gateway_restarts':0,'business_messages':0,'infra_code_config_data_changes':0}, 'resume_instructions':'Same H run. Skip all30 existing receipts; collect only pending10. Existing12 H were published09:33 and independently GET-verified this round. New18 are pixel-verified and canonical verified_entry validated but NOT published. Before publication reconcile current ledger, later writes and exact row/notes perID; publish only missing evidence via canonical worker without replaying H12 or overwriting newer evidence. Preserve earlier occurrence separately. Current publisher --verified-only replays all manifest entries: do not blindly apply cumulative30. Then D7, finalAPI, strict55 parity and canonical occurrence adapter/delivery. No funding/invoice replay.', 'evidence_manifest_sha256':hashlib.sha256((R/'visual-verification.json').read_bytes()).hexdigest()}
p = B/('recovery-progress-H30-'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
assert not p.exists()
p.write_text(json.dumps(result, ensure_ascii=False, indent=2)); os.chmod(p,0o600)
assert json.loads(p.read_text()) == result
print(json.dumps({'status':'partial_checkpoint_validated','checkpoint':str(p),'verified_H':len(entries),'published_H_independent_GET':len(published),'new_verified_unpublished_H':18,'pending_H_ids':pending,'pending_D_count':len(result['pending_account_ids_D']),'lease_free':True,'supervisor_alive':True,'sheet_writes':0}, ensure_ascii=False))
