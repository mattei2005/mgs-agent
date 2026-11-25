"""Seal the resource gate and separately reconcile authorized scope drift."""
import os, sys, json, hashlib, sqlite3, subprocess, shutil, importlib.util
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B=Path(__file__).parent
ROOT=Path('/root/mgs-agent')
KEY='ce11800d217d22dba6a58dcc'
def load(p): return json.loads(Path(p).read_text())
def save(n,v):
    with (B/n).open('x') as f: json.dump(v,f,ensure_ascii=False,indent=2)
rec=load(B/'reconciliation.json'); probe=load(B/'probe-receipt.json'); lease=load(B/'lease-release.json')
assert probe['save_dialog_count']==1 and probe['input_actions']==0
assert lease['release_exit']==0 and not lease['readback']['locked']
R=Path(shutil.which('hermes')).resolve().parents[2]; sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'))
from mgs_automation_continuity import native_contract_hash
spec=importlib.util.spec_from_file_location('resolver',ROOT/'scripts/alerts-infra-failed-alert-resolver.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
status,msg=m.discord_api(m.load_token(),'GET','/channels/1563926766286803004/messages/1575252034100138135')
assert status==200 and msg['id']=='1575252034100138135' and msg['channel_id']=='1563926766286803004' and msg['author']['id']=='344196393512075265'
save('concurrent-authority-readback.json',{'status':status,'id':msg['id'],'channel_id':msg['channel_id'],'author_id':msg['author']['id'],'content':msg['content']})
c=load(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json')
added=sorted(set(c['account_ids'])-set(rec['active_ids']));removed=sorted(set(rec['active_ids'])-set(c['account_ids']))
assert added==['1770569568407466'] and not removed
assert c['recurring_scope']['authority_message_id']==msg['id']
assert set(c['pay_now_account_ids'])==set(rec['pending_H_account_ids'])
assert c['sheet_id']==794137639 and c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled']
add_path=ROOT/'reports/meta-manual-payments-runs/add1-1575252034100138135/receipt.json'; add=load(add_path)
assert add['status']=='added_one_verified' and add['source_message_id']==msg['id'] and add['account_id']==added[0]
hl=load(ROOT/'data/meta-manual-payments/pc1-pay-now-ledger.json').get('accounts',{})
dl=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json').get('accounts',{})
hproof={k:{z:v for z,v in hl.get(k,{}).items() if z in ['read_at','source','amount','receipt']}for k in rec['pending_H_account_ids']}
dproof={k:{z:v for z,v in dl.get(k,{}).items() if z in ['read_at','source','receipt','verified_at']}for k in rec['pending_recent_D_account_ids']}
slot=datetime.fromisoformat(rec['scheduled_at'])
assert all(datetime.fromisoformat(v['read_at'])<slot for v in [*hproof.values(),*dproof.values()])
prep=Path(rec['h_prepare']); receipts=sorted(str(p)for p in prep.glob('*-receipt.json'))
vm=load(prep/'visual-verification.json')if(prep/'visual-verification.json').exists()else{}
assert not receipts and not vm.get('verified_account_ids',[])
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json');j=next(x for x in(jobs if isinstance(jobs,list)else jobs['jobs'])if x['id']=='2ee720363d7d')
assert not j.get('fire_claim') and j['last_dispatch']['scheduled_at']==rec['scheduled_at']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone());assert row['state']=='running' and row['owner']==rec['queue_owner'];os.kill(int(row['owner'].split(':')[1]),0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True)
consumers=[s for s in cron.stdout.splitlines()if not s.lstrip().startswith('#')and'alerts-infra-failed-alert-resolver'in s];assert len(consumers)==1
scope={'classification':'authorized_concurrent_change_reconciled_by_native_human_GET_and_exact_receipt','authority_message_id':msg['id'],'authority_readback':str(B/'concurrent-authority-readback.json'),'added_account_ids':added,'removed_account_ids':removed,'original_occurrence_account_ids':rec['active_ids'],'live_account_ids':c['account_ids'],'live_account_count':len(c['account_ids']),'h_set_unchanged':True,'receipt':str(add_path),'receipt_sha256':hashlib.sha256(add_path.read_bytes()).hexdigest(),'receipt_claims_old51_exact_preserved':add['old51_exact_preserved'],'independent_live_sheet_validation_this_round':False,'new_account_not_adopted_into_this_occurrence':True,'original_seal_guard_failure_preserved':str(B/'seal-private.log'),'next_step':'Supervisor reconciles authorized scope/row shift and current native hash before any future business retry; do not restore original51 or replay completed layers.'}
e={'observed_at':datetime.now(timezone.utc).isoformat(),'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_native_save_as_dialog_still_open','scheduled_at':rec['scheduled_at'],'original_native_contract_hash':rec['native_contract_hash'],'current_native_contract_hash':native_contract_hash(j),'authority_receipt':str(B/'authority-readback.json'),'original_command_context':str(B/'original-command-context.json'),'pending_H_account_ids':rec['pending_H_account_ids'],'pending_recent_D_account_ids':rec['pending_recent_D_account_ids'],'historical_D_separate_request':'79cd082a20c22a736307765f','historical_D_not_adopted':rec['historical_D_not_adopted'],'completed_financial_layers_preserved':rec['completed_layers'],'h_prepare':str(prep),'H_current_ledger_proofs':hproof,'D_current_ledger_proofs':dproof,'concurrent_scope_reconciliation':scope,'surface':{'approved_active_page':'Meta Business Suite / Billing & payments / Accounts','balance_header':'Outstanding balance','business_id_visible_in_pixels':'155263197283282','rodolfo_profile_present_in_ax':'Rodolfo'in(B/'approved-elements.json').read_text(),'native_save_as_dialog_open_pixels':True,'dialog_origin_not_established_by_pixels':True,'authentication_gate_proved':False,'dialog_preserved':True,'screenshots_inspected':[str(B/'approved.png'),str(B/'save-dialog-0.png')]},'input_actions':0,'tabs_created':0,'tabs_closed':0,'business_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'infrastructure_changes':0,'gateway_restarts':0,'completed_layers_replayed':False,'live_sheet_revalidation_performed':False,'lease_free_readback':True,'queue_owner':row['owner'],'queue_owner_alive':True,'queue_state_at_seal':row['state'],'consumer_heartbeat':hb,'consumer_schedule':' '.join(consumers[0].split()[:5]),'queue_transition_owner':'existing supervisor; no direct queue write','next_step':'Supervisor applies resource backoff and reconciles authorized concurrent inclusion. Revalidate original Chrome without dismissing unrelated Save As dialog. Preserve original occurrence H35/D2, historical D5 separate executor, completed layers and all later authorized writes. Canonical final API reconcile and independent validation/delivery only after missing-stage recovery.'}
save('recovery-evidence.json',e)
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in B.iterdir()if p.is_file()and not p.name.endswith('.log')}
save('evidence-sha256.json',manifest)
assert all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in load(B/'evidence-sha256.json').items())
assert load(B/'recovery-evidence.json')['source_key']==row['source_key']
print(json.dumps({'status':e['status'],'checkpoint':str(B/'recovery-evidence.json'),'pending_H_count':len(hproof),'pending_D':list(dproof),'lease_free':True,'hashes_verified':True,'owner_alive':True,'authorized_concurrent_added_ids':added,'current_native_hash':e['current_native_contract_hash'],'consumer_schedule':e['consumer_schedule'],'business_writes':0},ensure_ascii=False))
