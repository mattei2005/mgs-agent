"""Occurrence-specific source parity verifier; no business mutation."""
import sys,json,re,fcntl,os,subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timedelta
from collections import Counter
sys.path[:0]=['/root/mgs-agent/scripts','/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts']
from mgs_finance_continuity import read_workbook,authored
from mgs_automation_continuity import native_contract_hash
from refresh_workbook import zone
from publish_pay_now import verified_entry,save
B=Path(__file__).parent; HOME=Path('/root/mgs-agent/data/meta-manual-payments')
load=lambda p:json.loads(Path(p).read_text())
def value(c): return next(iter(c.get('userEnteredValue',{}).values()),'')
def index(sheet):
 out={}
 for g in sheet.get('data',[]):
  for row in g.get('rowData',[]):
   cs=row.get('values',[]);m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note','')) if cs else None
   if m: assert m[1] not in out;out[m[1]]=cs
 return out
c=load(HOME/'digital-trust-workbook-contract.json'); j=next(x for x in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if x['id']=='2ee720363d7d')
key='ebaa2482101e0f4757c25454';ch='825a7653aa8782fbbe23c0d2167eac26cfe36f00bad778f0146d9f746bffd921'
assert j['enabled'] and not j.get('fire_claim') and native_contract_hash(j)==ch
assert j['last_dispatch']['scheduled_at']=='2026-11-18T08:02:00-05:00'
assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
x=json.loads(load(B/'recovery-final-api-20261118T1111.json')['stdout']);assert x['status']=='updated_validated' and not x['pending_ui']
api=Path(x['run_dir']);plan=load(api/'plan.json');ar=load(api/'receipt.json');assert ar['full_grid_exact_readback'] and not ar['pending_ui']
p=load(B/'progress.json');invr=Path(json.loads(p['completed']['invoices']['stdout'])['run_dir']);inv=load(invr/'invoice-collection.json');assert inv==load(HOME/'september-invoice-ledger.json')
hdir=B.parent/'pay-now-20261118T080600211382';manifest=load(hdir/'visual-verification.json')
entries={t['account_id']:verified_entry(load(hdir/(t['account_id']+'-receipt.json')),t,c,manifest,hdir/(t['account_id']+'-receipt.json')) for t in load(hdir/'targets.json')}
assert set(entries)==set(c['pay_now_account_ids']) and len(entries)==40
with (HOME/'writer.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);book=read_workbook(c)
 old={s['properties']['sheetId']:s for s in load(B/'workbook-before.json')['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)
 assert all(authored(old[k])==authored(new[k]) for k in old if k!=c['sheet_id']),'other_sheet_data_changed'
 a=index(new[c['sheet_id']]);before=index(old[c['sheet_id']]);assert set(a)==set(before)==set(c['account_ids'])=={v['id'] for v in plan['planned']} and len(a)==55
 h=load(HOME/'pc1-pay-now-ledger.json')['accounts'];d=load(HOME/'pc1-card-ledger.json')['accounts'];blanks=[]
 for v in plan['planned']:
  aid=v['id'];cs=a[aid];assert value(cs[0])==v['name'] and value(cs[1])==v['method'] and value(cs[2])==v['default']
  assert cs[0].get('note')==before[aid][0].get('note') and cs[0].get('userEnteredFormat')==before[aid][0].get('userEnteredFormat')
  for col,k in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(value(cs[col])))==Decimal(v[k]) and plan['collected_at'] in cs[col]['note']
  local=datetime.fromisoformat(plan['collected_at']).astimezone(zone(v['timezone'])).date()
  assert v['average_period']=={'since':str(local-timedelta(days=3)),'until':str(local-timedelta(days=1))}
  assert v['month_period']=={'since':c['month_since'],'until':str(min(local,datetime.fromisoformat(c['month_until']).date()))}
  iv=inv['by_account'].get(aid)
  if iv:assert Decimal(str(value(cs[5])))==Decimal(iv['due']) and str(value(cs[4]))==(iv['invoice'] if Decimal(iv['due'])>0 and iv['status']!='Paid' else '')
  else:assert value(cs[4])=='' and value(cs[5]) in ('',0)
  if aid in entries:
   e=entries[aid];l=h[aid];assert all(l[k]==e[k] for k in ('amount','source','read_at')) and Path(l['receipt']).resolve()==Path(e['receipt']).resolve()
   assert Decimal(str(value(cs[7])))==Decimal(e['amount']) and all(str(l[k]) in cs[7]['note'] for k in ('read_at','source','receipt'))
  if value(cs[3])=='':blanks.append({'account_id':aid,'name':value(cs[0]),'reason':d.get(aid,{}).get('status','no_historical_instrument_proof')})
  else:
   e=d[aid];latest=e['latest_card'];assert Decimal(str(value(cs[3])))==Decimal(latest['amount']) and all(str(vv) in cs[3]['note'] for vv in [latest['method'],latest['date'],e['read_at']])
  assert cs[10:]==before[aid][10:]
 D=load(B/'recovery-progress-H40-D8-20261118T1057.json')['D_verified_published_ids']
 for aid in D:
  e=d[aid];assert Path(e['screenshot']).is_file() and Path(e['receipt']).is_file() and e['read_at']>= '2026-11-18'
  rec=load(e['receipt']);assert rec['account_requested']==aid and rec['status']=='read' and e['ui_url_account_id_verified']
 # No H write in this round: exact authored cells match the earlier H40 snapshot.
 prior=index(next(s for s in load(B/'recovery-after-H40-D2.json')['sheets'] if s['properties']['sheetId']==c['sheet_id']))
 for aid in entries:
  for field in ('userEnteredValue','note','userEnteredFormat','textFormatRuns'):assert a[aid][7].get(field)==prior[aid][7].get(field)
 struct=subprocess.run([sys.executable,str(B.parent/'cron-20261115T0802/launch.py'),'/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/validate_workbook_readonly.py','--spreadsheet-id',c['spreadsheet_id'],'--sheet-id',str(c['sheet_id']),'--business-id',c['business_id']],capture_output=True,text=True,timeout=90)
 assert struct.returncode==0;sv=json.loads(struct.stdout);assert sv['status']=='snapshot_readback_pass' and sv['accounts']==55
 save(B/'recovery-structural-final.json',sv)
 snap=B/'recovery-final-workbook.json';assert not snap.exists();save(snap,book)
 lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 r={'continuity_key':key,'source_key':'native:zeus:2ee720363d7d:20261118T0802','status':'financial_validation_pass_delivery_pending','business_refresh_complete':True,'accounts':55,'fresh_metrics_count':55,'fresh_h_count':40,'groups':dict(Counter(value(cs[1]) for cs in a.values())),'pending_ui':[],'validated_metrics_at':plan['collected_at'],'verified_at':datetime.now().astimezone().isoformat(),'scheduled_at':'2026-11-18T08:02:00-05:00','native_contract_hash':ch,'api_run_dir':str(api),'invoice_run_dir':str(invr),'h_run_dir':str(hdir),'h_read_times':{aid:h[aid]['read_at'] for aid in entries},'D_verified_published_ids':D,'historical_blank_d':blanks,'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_source_to_live_sheet_and_note_exact':True,'d_ledger_to_live_sheet_exact':True,'h_original_collection_times_preserved':True,'other_sheet_data_unchanged':True,'h_no_republication_this_round':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'lease_free':True,'snapshot':str(snap),'structural_validation':sv,'invoices':{'period':inv['invoice_period'],'pending':inv['unpaid_in_current_tab'],'due_usd':inv['tab_total_usd'],'outside':inv['outside_current_tab'],'collected_at':inv['collected_at']},'average_periods':sorted({(v['average_period']['since'],v['average_period']['until']) for v in plan['planned']}),'month_periods':sorted({(v['month_period']['since'],v['month_period']['until']) for v in plan['planned']}),'totals_usd':{k:str(sum((Decimal(v[k]) for v in plan['planned']),Decimal(0))) for k in ('average_daily','balance','month_spend')}}
 save(B/'recovery-financial-validation.json',r)
 print(json.dumps({'status':r['status'],'accounts':55,'H':40,'D_renewed':len(D),'pending_ui':[],'historical_D_blanks':len(blanks),'other_sheet_preserved':True,'receipt':str(B/'recovery-financial-validation.json')}))
