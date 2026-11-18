"""Read-only independent verification and durable partial checkpoint."""
import json,sys,re,os,sqlite3,fcntl,copy,hashlib,shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime
sys.path[:0]=['/root/mgs-agent/scripts','/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts']
from mgs_finance_continuity import read_workbook,authored
from mgs_automation_continuity import native_contract_hash
from publish_pay_now import verified_entry,save
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');R=B.parent/'pay-now-20261118T080600211382';delta=B/'H-unpublished28'
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());prev=json.loads((B/'recovery-progress-H30-20261118T100337.json').read_text())
j=next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id']=='2ee720363d7d')
assert j['enabled'] and not j.get('fire_claim') and native_contract_hash(j)==prev['native_contract_hash']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
own=dict(q.execute('select key,state,owner,lease_until,due,attempts,failures from requests where key=?',(prev['continuity_key'],)).fetchone());assert own['state']=='running';os.kill(int(own['owner'].split(':')[1]),0)
v=json.loads((R/'visual-verification.json').read_text());ts=json.loads((R/'targets.json').read_text());entries={t['account_id']:verified_entry(json.loads((R/(t['account_id']+'-receipt.json')).read_text()),t,c,v,R/(t['account_id']+'-receipt.json')) for t in ts}
assert set(entries)==set(v['verified_account_ids'])==set(c['pay_now_account_ids']) and len(entries)==40
with (H/'writer.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);book=read_workbook(c);ledger=json.loads((H/'pc1-pay-now-ledger.json').read_text());dledger=json.loads((H/'pc1-card-ledger.json').read_text())
rows=next(s for s in book['sheets'] if s['properties']['sheetId']==c['sheet_id'])['data'][0]['rowData']
def index(rows):
 out={}
 for row in rows:
  cells=row.get('values',[])
  if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):out[m[1]]=cells
 return out
byid=index(rows);assert len(byid)==55 and set(byid)==set(c['account_ids'])
for aid,e in entries.items():
 l=ledger['accounts'][aid];cell=byid[aid][7]
 assert l['amount']==e['amount'] and l['source']==e['source'] and l['read_at']==e['read_at']
 assert Path(l['receipt']).resolve()==Path(e['receipt']).resolve()
 assert Decimal(str(cell['userEnteredValue']['numberValue']))==Decimal(e['amount']) and e['read_at'] in cell['note'] and l['receipt'] in cell['note'] and e['source'] in cell['note']
before=json.loads((B/'recovery-before-H28-delta.json').read_text());oldsh={s['properties']['sheetId']:s for s in before['sheets']};newsh={s['properties']['sheetId']:s for s in book['sheets']};assert oldsh.keys()==newsh.keys()
for sid in oldsh:
 if sid!=c['sheet_id']:assert authored(oldsh[sid])==authored(newsh[sid]),'other_sheet_changed'
oldby=index(oldsh[c['sheet_id']]['data'][0]['rowData'])
for aid in prev['published_h_ids']:assert authored({'data':[{'rowData':[{'values':[oldby[aid][7]]}]}]})==authored({'data':[{'rowData':[{'values':[byid[aid][7]]}]}]}),'H12_replayed'
done=['1062446663435585','2323706575049143']
for aid in done:
 d=dledger['accounts'][aid];last=d['latest_card'];cell=byid[aid][3]
 assert Decimal(str(cell['userEnteredValue']['numberValue']))==Decimal(last['amount'])
 assert last['method'] in cell['note'] and last['date'] in cell['note'] and d['read_at'] in cell['note']
 rp=Path(d['receipt']);rec=json.loads(rp.read_text())
 # Preserve the actual captured image and AX in the same protected evidence dir.
 for field,name in [('screenshot','capture.png'),('elements_path','elements.json')]:
  src=Path(rec[field]) if rec.get(field) else None
  if src and src.exists():shutil.copy2(src,rp.parent/name);os.chmod(rp.parent/name,0o600)
assert not Path('/root/.hermes/shared/locks/pc1-computer-use.json').exists()
now=datetime.now().astimezone().isoformat();snap=B/'recovery-after-H40-D2.json';save(snap,book)
result={'continuity_key':prev['continuity_key'],'source_key':prev['source_key'],'state':'partial_H40_published_D2_verified','mode':'resume_safe','verified_at':now,'business_refresh_complete':False,'delivery_pending':True,'h_run_dir':str(R),'h_delta_publication_dir':str(delta),'scope_accounts':55,'h_targets':40,'h_verified_count':40,'h_published_readback_count':40,'h_previous12_cells_exact_preserved':True,'verified_h_ids':sorted(entries),'published_h_ids':sorted(entries),'pending_account_ids_H':[],'D_verified_published_this_round':done,'pending_account_ids_D':[a for a in prev['pending_account_ids_D'] if a not in done],'pending_layers':['D5_historical_instrument_verification','final_API_reconciliation_and_full_validation','canonical_occurrence_adapter_and_idempotent_delivery_GET'],'canonical_H_evidence_validation_pass':True,'source_to_sheet_H40_exact':True,'D2_source_to_sheet_exact':True,'other_sheet_authored_data_unchanged_this_round':True,'snapshot':str(snap),'native_contract_hash':native_contract_hash(j),'ownership':own,'supervisor_alive':True,'queue_mutated_by_worker':False,'next_retry_owner':'Current supervisor after result consumption','pc1_lease_free':True,'auth_gate_observed':False,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'gateway_restarts':0,'business_messages':0,'infra_code_config_changes':0,'report_infra_status':'previous occurrence administrative report remains pending separately','resume_instructions':'Do not recollect or republish H: all40 independently GET-verified, previous12 untouched. Canonical --verified-only published only28 missing via evidence subset/symlinks; original full40 manifest retained. D2 verified and written with canonical recorder; skip both unless finalAPI exposes genuinely newer events. Resolve pendingD5 only, then canonical finalAPI, structural/full source parity and occurrence-specific canonical delivery adapter. No funding/invoice replay, no cron mutation. Preserve earlier occurrences separately.'}
p=B/('recovery-progress-H40-D2-'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json');assert not p.exists();save(p,result);assert json.loads(p.read_text())==result
print(json.dumps({'status':'partial_checkpoint_validated','checkpoint':str(p),'H_verified_published':40,'H12_untouched':True,'D_new_verified_published':2,'pending_D':result['pending_account_ids_D'],'other_sheet_preserved_this_round':True,'lease_free':True,'supervisor_alive':True}))
