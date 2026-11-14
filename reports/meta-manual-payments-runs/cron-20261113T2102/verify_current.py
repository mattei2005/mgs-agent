"""Read-only verification of the current occurrence, with historical UI kept distinct."""
import json,re,sys,subprocess
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
from collections import Counter
from zoneinfo import ZoneInfo
BASE=Path('/root/mgs-agent'); RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'scripts'))
from mgs_finance_continuity import read_workbook,authored
from mgs_automation_continuity import native_contract_hash

def load(p):return json.loads(Path(p).read_text())
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),'')
def rows(s):
 out={}
 for grid in s.get('data',[]):
  for row in grid.get('rowData',[]):
   cs=row.get('values',[]);m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note','')) if cs else None
   if m:assert m[1] not in out;out[m[1]]=cs
 return out
c=load(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json');p=load(RUN/'progress.json')
api=Path(json.loads(p['completed']['api']['stdout'])['run_dir']);invdir=Path(json.loads(p['completed']['invoices']['stdout'])['run_dir']);hdir=Path(json.loads(p['completed']['h_prepare']['stdout'])['run_dir'])
plan=load(api/'plan.json');inv=load(invdir/'invoice-collection.json');assert inv==load(BASE/'data/meta-manual-payments/september-invoice-ledger.json')
old={s['properties']['sheetId']:s for s in load(RUN/'workbook-before.json')['sheets']};book=read_workbook(c);(RUN/'final-workbook.json').write_text(json.dumps(book,ensure_ascii=False));new={s['properties']['sheetId']:s for s in book['sheets']}
assert set(old)==set(new)
other_unchanged=all(authored(old[k])==authored(new[k]) for k in old if k!=c['sheet_id'])
a=rows(new[c['sheet_id']]);b=rows(old[c['sheet_id']]);assert set(a)==set(b)==set(c['account_ids'])=={x['id'] for x in plan['planned']};assert len(a)==55
for x in plan['planned']:
 cs=a[x['id']];assert val(cs[2])==x['default'];assert val(cs[0])==x['name'] and val(cs[1])==x['method']
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert Decimal(str(val(cs[col])))==Decimal(x[key]);assert plan['collected_at'] in cs[col]['note']
 local=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(x['timezone'])).date()
 assert x['average_period']=={'since':str(local-timedelta(days=3)),'until':str(local-timedelta(days=1))}
 assert x['month_period']=={'since':c['month_since'],'until':str(min(local,datetime.fromisoformat(c['month_until']).date()))}
 for col in (3,7):
  for k in ('userEnteredValue','note','userEnteredFormat','textFormatRuns'):assert cs[col].get(k)==b[x['id']][col].get(k),(x['id'],col,k)
 invoice=inv['by_account'].get(x['id'])
 if invoice:
  assert Decimal(str(val(cs[5])))==Decimal(invoice['due'])
  assert str(val(cs[4]))==(invoice['invoice'] if Decimal(invoice['due'])>0 and invoice['status']!='Paid' else '')
 else:assert val(cs[4])=='' and val(cs[5]) in ('',0)
h=load(BASE/'data/meta-manual-payments/pc1-pay-now-ledger.json')['accounts'];d=load(BASE/'data/meta-manual-payments/pc1-card-ledger.json')['accounts'];ht=[];blanks=[]
for aid,cs in a.items():
 if aid in c['pay_now_account_ids']:
  e=h[aid];assert e['source']=='accounts_list_outstanding_balance' and e['visual_account_verified'];assert Decimal(str(val(cs[7])))==Decimal(e['amount']);assert all(t in cs[7]['note'] for t in (e['source'],e['read_at'],'1570815017794674749'));ht.append(e['read_at'])
 if val(cs[3])=='':blanks.append({'account_id':aid,'name':val(cs[0]),'reason':d.get(aid,{}).get('status','no_historical_instrument_proof')})
 else:
  e=d[aid];lc=e['latest_card'];assert e['status']=='verified_card' and lc['status']=='Paid';assert Decimal(str(val(cs[3])))==Decimal(lc['amount']);assert all(t in cs[3]['note'] for t in (e['read_at'],lc['date'],lc['method']))
j=next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if j['id']==c['cron_job_id']);beforejob=load(RUN/'job-before.json');assert native_contract_hash(j)==native_contract_hash(beforejob);assert j['enabled'] and j['fire_claim']['by']==beforejob['fire_claim']['by'] and datetime.fromisoformat(j['fire_claim']['at'])>=datetime.fromisoformat(beforejob['fire_claim']['at']);assert j['last_dispatch']['scheduled_at']==p['scheduled_at'];assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
lease=json.loads(subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert lease['ok'] and not lease['locked']
receipt={'status':'partial_validated_waiting_human_meta_passkey','scheduled_at':p['scheduled_at'],'job_id':j['id'],'verified_at':datetime.now().astimezone().isoformat(),'accounts':len(a),'groups':dict(Counter(val(cs[1]) for cs in a.values())),'fresh_metrics_count':len(a),'api_collected_at':plan['collected_at'],'fresh_h_count':0,'preserved_h_count':len(ht),'h_read_at_min':min(ht),'h_read_at_max':max(ht),'h_source':'accounts_list_outstanding_balance','h_header':val(new[c['sheet_id']]['data'][0]['rowData'][0]['values'][7]),'h_run_dir':str(hdir),'api_run_dir':str(api),'invoice_run_dir':str(invdir),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_historical_ledger_and_notes_exact':True,'d_historical_ledger_and_notes_exact':True,'h_and_d_preserved_exact':True,'other_sheet_data_unchanged':other_unchanged,'workbook_sheets':len(new),'average_periods':sorted({json.dumps(x['average_period'],sort_keys=True) for x in plan['planned']}),'month_periods':sorted({json.dumps(x['month_period'],sort_keys=True) for x in plan['planned']}),'pending_ui':plan['pending_ui'],'historical_blank_d_count':len(blanks),'historical_blank_d':blanks,'invoices':{'period':inv['invoice_period'],'pending':inv['unpaid_in_current_tab'],'due_usd':inv['tab_total_usd'],'outside':inv['outside_current_tab'],'collected_at':inv['collected_at']},'totals_usd':{k:str(sum((Decimal(x[k]) for x in plan['planned']),Decimal(0))) for k in ('average_daily','balance','month_spend')},'lease_free':True,'auth_gate':'Meta Confirm it\'s you with your passkey; business.facebook.com/security/twofactor/reauth/; blocked.png inspected','next_run_at':j['next_run_at'],'schedule_unchanged':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending_cron_delivery_only_no_direct_send','business_refresh_complete':False}
(RUN/'closure-current.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in receipt.items() if k!='historical_blank_d'},ensure_ascii=False))
