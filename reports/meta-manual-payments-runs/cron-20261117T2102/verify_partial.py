import json,re,sys,subprocess
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from collections import Counter
BASE=Path('/root/mgs-agent');RUN=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'scripts'))
from mgs_finance_continuity import read_workbook,authored
from mgs_automation_continuity import native_contract_hash
load=lambda p:json.loads(Path(p).read_text())
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),'')
def rows(s):
 out={}
 for grid in s.get('data',[]):
  for row in grid.get('rowData',[]):
   cs=row.get('values',[]);m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note','')) if cs else None
   if m:assert m[1] not in out;out[m[1]]=cs
 return out
c=load(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json');p=load(RUN/'progress.json')
api_result=json.loads(p['completed']['api']['stdout']);api=Path(api_result['run_dir']);plan=load(api/'plan.json')
invdir=Path(json.loads(p['completed']['invoices']['stdout'])['run_dir']);inv=load(invdir/'invoice-collection.json');assert inv==load(BASE/'data/meta-manual-payments/september-invoice-ledger.json')
old={s['properties']['sheetId']:s for s in load(RUN/'workbook-before.json')['sheets']};book=read_workbook(c);(RUN/'final-workbook.json').write_text(json.dumps(book,ensure_ascii=False));new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)
other_unchanged=all(authored(old[k])==authored(new[k]) for k in old if k!=c['sheet_id']);assert other_unchanged,'other_tab_changed_preserve_snapshot_and_investigate'
a=rows(new[c['sheet_id']]);b=rows(old[c['sheet_id']]);assert set(a)==set(b)==set(c['account_ids'])=={x['id']for x in plan['planned']};assert len(a)==55
for x in plan['planned']:
 cs=a[x['id']];assert val(cs[2])==x['default'];assert val(cs[0])==x['name'] and val(cs[1])==x['method']
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
  assert Decimal(str(val(cs[col])))==Decimal(x[key]);assert plan['collected_at'] in cs[col]['note']
 local=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(x['timezone'])).date();assert x['average_period']=={'since':str(local-timedelta(days=3)),'until':str(local-timedelta(days=1))};assert x['month_period']=={'since':c['month_since'],'until':str(min(local,datetime.fromisoformat(c['month_until']).date()))}
 invoice=inv['by_account'].get(x['id'])
 if invoice:assert Decimal(str(val(cs[5])))==Decimal(invoice['due']);assert str(val(cs[4]))==(invoice['invoice'] if Decimal(invoice['due'])>0 and invoice['status']!='Paid' else '')
 else:assert val(cs[4])=='' and val(cs[5]) in ('',0)
 for col in (3,7):
  for key in ('userEnteredValue','note','userEnteredFormat','textFormatRuns'):assert cs[col].get(key)==b[x['id']][col].get(key),(x['id'],col,key)
 for col in range(10,max(len(cs),len(b[x['id']]))):assert (cs[col]if col<len(cs)else{})==(b[x['id']][col]if col<len(b[x['id']])else{}),'outside_AJ_changed'
j=next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs']if j['id']==c['cron_job_id']);beforejob=load(RUN/'job-before.json');assert native_contract_hash(j)==native_contract_hash(beforejob);assert j['enabled'] and j['fire_claim']['by']==beforejob['fire_claim']['by'];assert j['last_dispatch']==beforejob['last_dispatch'] and datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
lease=json.loads(subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert lease['ok'] and not lease['locked']
struct=load(RUN/'structural-validation.log');assert struct['status']=='snapshot_readback_pass' and struct['accounts']==55
h=load(BASE/'data/meta-manual-payments/pc1-pay-now-ledger.json')['accounts']
r={'status':'pending_pc1_offline','business_refresh_complete':False,'run_kind':'scheduled_tick','scheduled_at':beforejob['last_dispatch']['scheduled_at'],'job_id':j['id'],'fire_claim':beforejob['fire_claim'],'verified_at':datetime.now().astimezone().isoformat(),'accounts':len(a),'groups':dict(Counter(val(cs[1])for cs in a.values())),'fresh_metrics_count':len(a),'api_collected_at':plan['collected_at'],'api_run_dir':str(api),'invoice_run_dir':str(invdir),'h_run_dir':json.loads(p['completed']['h_prepare']['stdout'])['run_dir'],'fresh_h_count':0,'preserved_h_count':len(c['pay_now_account_ids']),'h_source':c['h_source'],'h_prior_read_at_min':min(h[i]['read_at']for i in c['pay_now_account_ids']),'h_prior_read_at_max':max(h[i]['read_at']for i in c['pay_now_account_ids']),'pending_ui':api_result['pending_ui'],'historical_d_preserved':True,'h_values_notes_original_times_preserved':True,'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'other_sheet_data_unchanged':other_unchanged,'workbook_sheets':len(new),'structural_validation':struct,'invoices':{'period':inv['invoice_period'],'pending':inv['unpaid_in_current_tab'],'due_usd':inv['tab_total_usd'],'outside':inv['outside_current_tab'],'collected_at':inv['collected_at']},'totals_usd':{k:str(sum((Decimal(x[k])for x in plan['planned']),Decimal(0)))for k in ('average_daily','balance','month_spend')},'lease_free':True,'next_run_at':j['next_run_at'],'schedule_unchanged':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'authentication_observed':False,'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'automatic_final_only_short_offline_blocker','run_dir':str(RUN),'evidence':str(RUN/'partial-receipt.json')}
(RUN/'partial-receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in ('structural_validation','pending_ui')},ensure_ascii=False))
