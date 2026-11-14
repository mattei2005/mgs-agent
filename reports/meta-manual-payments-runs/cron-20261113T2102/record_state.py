"""Persist the verified partial occurrence; no scheduling, payment or delivery."""
import json,sys,hashlib,sqlite3,time,os,tempfile
from pathlib import Path
from datetime import datetime
B=Path('/root/mgs-agent');R=Path(__file__).resolve().parent
r=json.loads((R/'closure-current.json').read_text());assert r['accounts']==55 and r['fresh_metrics_count']==55 and r['fresh_h_count']==0
assert r['other_sheet_data_unchanged'] and r['lease_free']

def load(p):return json.loads(p.read_text())
def save(p,data):
 raw=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
 fd,n=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:f.write(raw)
  os.chmod(n,0o600);os.replace(n,p)
 finally:
  if os.path.exists(n):os.unlink(n)

cp=B/'data/meta-manual-payments/digital-trust-workbook-contract.json';c=load(cp)
assert c['account_ids']==load(R/'contract-before.json')['account_ids'] and c['h_source']=='accounts_list_outstanding_balance'
if c['latest_refresh_qualification'].get('scheduled_at')!=r['scheduled_at']:
 save(R/'qualification-before.json',c['latest_refresh_qualification'])
 c['previous_refresh_qualification']=c['latest_refresh_qualification']
c['latest_refresh_qualification']={**{k:v for k,v in r.items() if k!='historical_blank_d'},'run_dir':str(R),'historical_d_values_revalidated_at_provider':False,'h_values_revalidated_at_provider':False,'evidence':str(R/'closure-current.json')}
c['latest_recovery_attempt']={'scheduled_at':r['scheduled_at'],'status':r['status'],'fresh_metrics_count':55,'fresh_h_count':0,'h_previous_values_and_times_preserved':True,'api_collected_at':r['api_collected_at'],'evidence':str(R/'closure-current.json'),'prior_1402_incident_remains_open':True}
c['pending_card_history']={'status':'waiting_human_meta_passkey_new_events_pending','account_ids':[x['account_id'] for x in r['pending_ui']],'pending_ui':r['pending_ui'],'historical_blank_count':r['historical_blank_d_count'],'evidence':str(R/'closure-current.json')}
c['next_run_at']=r['next_run_at'];save(cp,c)
ref=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/references/recurring-refresh.md');mirror=B/'profiles/zeus-skills/ops/meta-manual-payments-planning/references/recurring-refresh.md';assert ref.read_bytes()==mirror.read_bytes();sha=hashlib.sha256(ref.read_bytes()).hexdigest()
entry={'id':'meta-manual-payments-refresh-cron-20261113T2102','agent':'zeus','type':'scheduled_financial_refresh_and_claim_validation_lesson','status':r['status'],'updated_at':r['verified_at'],'evidence':str(R/'closure-current.json'),'source_thread_id':c['thread_id'],'verification':{'accounts':55,'fresh_metrics':55,'fresh_h':0,'preserved_h':40,'pending_d':len(r['pending_ui']),'historical_blank_d':r['historical_blank_d_count'],'source_parity_cgij_ef':True,'historical_h_d_ledger_parity':True,'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0,'meta_writes':0,'cron_changes':0},'procedural_learning':{'target':str(ref),'sha256':sha,'mirror_equal':True,'summary':'Validate active fire claim by owner and slot; renewable heartbeat at may advance. No writes replayed after validator-only failure.'},'report_infra_status':r['report_infra_status']}
ip=B/'data/infra-inventory.json';i=load(ip);matches=[x for x in i['runtime_artifacts'] if x.get('id')==entry['id']];assert len(matches)<=1
if matches:i['runtime_artifacts'][i['runtime_artifacts'].index(matches[0])]=entry
else:i['runtime_artifacts'].append(entry)
save(ip,i)
# Keep the existing human/decision hold and original occurrence; attach this
# later occurrence as evidence, not completion of the earlier 14:02 delivery.
db=sqlite3.connect('/root/.hermes/shared/automation-continuity/queue.sqlite3',timeout=15,isolation_level=None);db.row_factory=sqlite3.Row;db.execute('BEGIN IMMEDIATE')
try:
 q=db.execute("SELECT * FROM requests WHERE key=?",('e67b9e22a17027e23728d532',)).fetchone();assert q and q['state']=='blocked_decision' and q['owner'] is None
 event={'scheduled_at':r['scheduled_at'],'receipt':str(R/'closure-current.json'),'state_preserved':q['state'],'fresh_metrics':55,'fresh_h':0,'pending_ui':[x['account_id']for x in r['pending_ui']],'original_1402_slot_not_completed':True}
 db.execute('INSERT INTO events(at,request_key,kind,detail) VALUES(?,?,?,?)',(time.time(),q['key'],'later_native_occurrence_partial_verified',json.dumps(event,ensure_ascii=False)))
 obs=q['observation']+'\n\nOcorrência posterior 13/11 21:02: API55 às21:06 e invoices30 USD417864.11 validadas; H40 históricos preservados; passkey Meta novamente comprovada. D recentes agora 3:1414197490675732,1543098427832443,2852476828464907. Não conclui ocorrência14:02. Evidência:'+str(R/'closure-current.json')
 db.execute('UPDATE requests SET updated=?,observation=? WHERE key=? AND state=? AND owner IS NULL',(time.time(),obs,q['key'],q['state']));db.execute('COMMIT')
except BaseException:db.execute('ROLLBACK');raise
with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'at':r['verified_at'],'agent':'zeus','event':'meta_manual_payments_recurring_partial_validated','job_id':c['cron_job_id'],'scheduled_at':r['scheduled_at'],'receipt':str(R/'closure-current.json'),'accounts':55,'h_fresh':0,'d_pending':len(r['pending_ui']),'skill_learning':entry['procedural_learning'],'report_infra_status':r['report_infra_status'],'payments':0,'billing_changes':0,'cron_changes':0},ensure_ascii=False)+'\n')
assert load(cp)['latest_refresh_qualification']['scheduled_at']==r['scheduled_at']
assert sum(x.get('id')==entry['id']for x in load(ip)['runtime_artifacts'])==1
q=db.execute('SELECT state,owner FROM requests WHERE key=?',('e67b9e22a17027e23728d532',)).fetchone();assert q['state']=='blocked_decision' and q['owner'] is None
save(R/'state-readback.json',{'contract_partial_current':True,'inventory_unique':True,'queue_original_human_hold_preserved':True,'skill_sha256':sha,'mirror_equal':True,'report_infra_status':r['report_infra_status']})
print(json.dumps({'status':'partial_state_recorded_readback','report_infra_status':r['report_infra_status'],'no_new_job':True,'skill_mirror_equal':True}))
