"""Reconcile H evidence and prepare only unpublished IDs for canonical publisher."""
import json, sys, os, fcntl, re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
sys.path.insert(0,'/root/mgs-agent/scripts')
sys.path.insert(0,'/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
from mgs_finance_continuity import read_workbook
from mgs_automation_continuity import native_contract_hash
from publish_pay_now import verified_entry,save
H=Path('/root/mgs-agent/data/meta-manual-payments')
B=Path(__file__).parent
R=B.parent/'pay-now-20261118T080600211382'
c=json.loads((H/'digital-trust-workbook-contract.json').read_text())
j=next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id']=='2ee720363d7d')
assert j['enabled'] and not j.get('fire_claim') and native_contract_hash(j)=='825a7653aa8782fbbe23c0d2167eac26cfe36f00bad778f0146d9f746bffd921'
v=json.loads((R/'visual-verification.json').read_text())
ts=json.loads((R/'targets.json').read_text())
assert set(v['verified_account_ids'])==set(v['accounts_list_checks'])==set(c['pay_now_account_ids']) and len(v['verified_account_ids'])==40
entries={t['account_id']:verified_entry(json.loads((R/(t['account_id']+'-receipt.json')).read_text()),t,c,v,R/(t['account_id']+'-receipt.json')) for t in ts}
prev=json.loads((B/'recovery-progress-H30-20261118T100337.json').read_text())
published=set(prev['published_h_ids']); missing=set(entries)-published
assert len(published)==12 and len(missing)==28
with (H/'writer.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 book=read_workbook(c)
 ledger=json.loads((H/'pc1-pay-now-ledger.json').read_text())
 rows=next(s for s in book['sheets'] if s['properties']['sheetId']==c['sheet_id'])['data'][0]['rowData']
 byid={}
 for row in rows:
  cells=row.get('values',[])
  if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):byid[m[1]]=cells
 assert set(byid)==set(c['account_ids']) and len(byid)==55
 for aid,e in entries.items():
  old=ledger['accounts'][aid]; cell=byid[aid][7]
  assert Decimal(str(cell['userEnteredValue']['numberValue']))==Decimal(old['amount'])
  assert old['read_at'] in cell['note'] and old['receipt'] in cell['note']
  if aid in published:assert old==e
  else:assert datetime.fromisoformat(old['read_at']) < datetime.fromisoformat(e['read_at']), 'newer_or_already_published_evidence'
 delta=B/'H-unpublished28'
 assert not delta.exists(),'delta_already_exists_reconcile_receipts_before_retry'
 delta.mkdir(mode=0o700)
 save(delta/'targets.json',ts)
 save(delta/'visual-verification.json',{'continuity_key':v['continuity_key'],'verified_account_ids':sorted(missing),'accounts_list_checks':{a:v['accounts_list_checks'][a] for a in missing}})
 save(delta/'source-lineage.json',{'source_run':str(R),'excluded_already_published_ids':sorted(published),'missing_ids':sorted(missing),'no_recollection':True,'canonical_publisher_required':True})
 for aid in missing:(delta/(aid+'-receipt.json')).symlink_to(R/(aid+'-receipt.json'))
 save(B/'recovery-before-H28-delta.json',book)
 save(delta/'prior-ledger-reconciled.json',ledger)
 print(json.dumps({'status':'delta_prepared','verified_H':40,'already_published_excluded':12,'unpublished_H':28,'delta_dir':str(delta),'sheet_writes':0}))
