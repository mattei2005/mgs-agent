import json,re,sys,subprocess,copy
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
from collections import Counter
from zoneinfo import ZoneInfo
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
c=load(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json');p=load(RUN/'progress.json');final=load(RUN/'api-final.log');assert final['status']=='updated_validated' and final['pending_ui']==[]
api=Path(final['run_dir']);invdir=Path(json.loads(p['completed']['invoices']['stdout'])['run_dir']);hdir=Path(json.loads(p['completed']['h_prepare']['stdout'])['run_dir']);plan=load(api/'plan.json');inv=load(invdir/'invoice-collection.json');assert inv==load(BASE/'data/meta-manual-payments/september-invoice-ledger.json')
old={s['properties']['sheetId']:s for s in load(RUN/'workbook-before.json')['sheets']};book=read_workbook(c);(RUN/'final-workbook.json').write_text(json.dumps(book,ensure_ascii=False));new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)
other_unchanged=all(authored(old[k])==authored(new[k]) for k in old if k!=c['sheet_id']);assert other_unchanged,'other_tab_changed_preserve_snapshot_and_investigate'
a=rows(new[c['sheet_id']]);b=rows(old[c['sheet_id']]);assert set(a)==set(b)==set(c['account_ids'])=={x['id']for x in plan['planned']};assert len(a)==55 and not plan['pending_ui']
for x in plan['planned']:
 cs=a[x['id']];assert val(cs[2])==x['default'];assert val(cs[0])==x['name'] and val(cs[1])==x['method']
 for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(val(cs[col])))==Decimal(x[key]);assert plan['collected_at'] in cs[col]['note']
 local=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(x['timezone'])).date();assert x['average_period']=={'since':str(local-timedelta(days=3)),'until':str(local-timedelta(days=1))};assert x['month_period']=={'since':c['month_since'],'until':str(min(local,datetime.fromisoformat(c['month_until']).date()))}
 invoice=inv['by_account'].get(x['id'])
 if invoice:assert Decimal(str(val(cs[5])))==Decimal(invoice['due']);assert str(val(cs[4]))==(invoice['invoice'] if Decimal(invoice['due'])>0 and invoice['status']!='Paid' else '')
 else:assert val(cs[4])=='' and val(cs[5]) in ('',0)
 for col in range(10,max(len(cs),len(b[x['id']]))):assert (cs[col]if col<len(cs)else{})==(b[x['id']][col]if col<len(b[x['id']])else{}),'outside_AJ_changed'
h=load(BASE/'data/meta-manual-payments/pc1-pay-now-ledger.json')['accounts'];d=load(BASE/'data/meta-manual-payments/pc1-card-ledger.json')['accounts'];visual=load(hdir/'visual-verification.json');assert set(visual['verified_account_ids'])==set(c['pay_now_account_ids']) and len(visual['verified_account_ids'])==40
ht=[];blanks=[];renewed=[]
for aid,cs in a.items():
 if aid in c['pay_now_account_ids']:
  e=h[aid];rec=load(hdir/(aid+'-receipt.json'));vc=visual['accounts_list_checks'][aid];assert e['source']==rec['source']=='accounts_list_outstanding_balance' and e['visual_account_verified'];assert Decimal(str(val(cs[7])))==Decimal(e['amount'])==Decimal(rec['amount'])==Decimal(vc['balance_usd']);assert e['read_at']==rec['read_at'];assert all(t in cs[7]['note'] for t in (e['source'],e['read_at'],'1570815017794674749'));assert vc['balance_label']=='Outstanding balance' and vc['authority_message_id']=='1570815017794674749' and vc['row_account_id']==aid and vc['name']==val(cs[0]) and vc['business_id']==c['business_id'];ht.append(e['read_at'])
 if val(cs[3])=='':blanks.append({'account_id':aid,'name':val(cs[0]),'reason':d.get(aid,{}).get('status','no_historical_instrument_proof')})
 else:
  e=d[aid];lc=e['latest_card'];assert e['status']=='verified_card' and lc['status']=='Paid';assert Decimal(str(val(cs[3])))==Decimal(lc['amount']);assert all(t in cs[3]['note']for t in (e['read_at'],lc['date'],lc['method']))
  proof=RUN/('proof-'+aid+'.log')
  if proof.exists():assert load(proof)['status']=='pc1_proof_recorded_and_sheet_readback_pass';renewed.append(aid)
expected_pending={x['account_id']for x in json.loads(p['completed']['api']['stdout'])['pending_ui']};assert set(renewed)==expected_pending and len(renewed)==7
j=next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs']if j['id']==c['cron_job_id']);beforejob=load(RUN/'job-before.json');assert native_contract_hash(j)==native_contract_hash(beforejob);assert j['enabled'] and j['fire_claim']['by']==beforejob['fire_claim']['by'];assert j['last_dispatch']==beforejob['last_dispatch'] and datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
lease=json.loads(subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert lease['ok'] and not lease['locked']
struct=load(RUN/'structural-validation.log');assert struct['status']=='snapshot_readback_pass' and struct['accounts']==55
assert len(book['sheets'])==2
receipt={'status':'completed_validated','run_kind':'scheduled_tick','scheduled_at':beforejob['last_dispatch']['scheduled_at'],'job_id':j['id'],'fire_claim':beforejob['fire_claim'],'dispatch_context':beforejob['last_dispatch'],'verified_at':datetime.now().astimezone().isoformat(),'accounts':len(a),'groups':dict(Counter(val(cs[1])for cs in a.values())),'fresh_metrics_count':len(a),'api_collected_at':plan['collected_at'],'fresh_h_count':len(ht),'preserved_h_count':0,'h_read_at_min':min(ht),'h_read_at_max':max(ht),'h_source':'accounts_list_outstanding_balance','h_header':c['schema']['H'],'h_run_dir':str(hdir),'api_run_dir':str(api),'invoice_run_dir':str(invdir),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_source_to_live_sheet_and_note_exact':True,'d_ledger_to_live_sheet_exact':True,'h_original_collection_times_preserved':True,'other_sheet_data_unchanged':other_unchanged,'workbook_sheets':len(new),'average_periods':sorted({json.dumps(x['average_period'],sort_keys=True)for x in plan['planned']}),'month_periods':sorted({json.dumps(x['month_period'],sort_keys=True)for x in plan['planned']}),'pending_ui':plan['pending_ui'],'renewed_d_account_ids':renewed,'historical_blank_d_count':len(blanks),'historical_blank_d':blanks,'invoices':{'period':inv['invoice_period'],'pending':inv['unpaid_in_current_tab'],'due_usd':inv['tab_total_usd'],'outside':inv['outside_current_tab'],'collected_at':inv['collected_at']},'totals_usd':{k:str(sum((Decimal(x[k])for x in plan['planned']),Decimal(0)))for k in ('average_daily','balance','month_spend')},'h_total_usd':str(sum((Decimal(h[aid]['amount'])for aid in c['pay_now_account_ids']),Decimal(0))),'lease_free':True,'next_run_at':j['next_run_at'],'schedule_unchanged':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending_cron_delivery_only_no_direct_send','business_refresh_complete':True,'structural_validation_pass':True,'delivery':'automatic_final_only_not_yet_delivered','historical_incident_not_closed_by_later_occurrence':True,'evidence':str(RUN/'closure-current.json'),'run_dir':str(RUN)}
(RUN/'closure-current.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in receipt.items()if k!='historical_blank_d'},ensure_ascii=False))
