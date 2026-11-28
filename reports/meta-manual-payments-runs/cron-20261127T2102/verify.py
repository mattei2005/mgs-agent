import os,sys,json,shutil,re,subprocess,fcntl,copy
from pathlib import Path
from datetime import datetime,timedelta,date
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');sys.path.insert(0,str(S));from refresh_workbook import zone
B=Path('/root/mgs-agent/reports/meta-manual-payments-runs/cron-20261127T2102');H=Path('/root/mgs-agent/data/meta-manual-payments');c=json.loads((H/'digital-trust-workbook-contract.json').read_text());before=json.loads((B/'workbook-before.json').read_text())
def log(n):return [json.loads(s)for s in(B/(n+'.log')).read_text().splitlines()if s.startswith('{')][-1]
def save(n,d):
 p=B/n;assert not p.exists(),'immutable_exists_'+n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def uv(v):return v.get('userEnteredValue',{})
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
   vs=row.get('values',[])
   if vs and(m:=re.search(r'^ID da conta: (\d+)\b',vs[0].get('note',''))):assert m[1]not in out;out[m[1]]=(ri,vs)
 return out
api_dir=Path(log('api-final')['run_dir']);inv_dir=Path(log('invoices')['run_dir']);hd=Path(log('h_prepare')['run_dir']);plan=json.loads((api_dir/'plan.json').read_text());api=json.loads((api_dir/'receipt.json').read_text());inv=json.loads((inv_dir/'invoice-collection.json').read_text());hl=json.loads((H/'pc1-pay-now-ledger.json').read_text());dl=json.loads((H/'pc1-card-ledger.json').read_text());v=json.loads((hd/'visual-verification.json').read_text());initial=log('api');struct=log('structural-validation');hp=log('h-publish');current_renewed={p['account_id']for p in initial['pending_ui']};historical_renewed=set();renewed=current_renewed|historical_renewed
assert api['status']=='updated_validated'and api['accounts']==len(c['account_ids']) and api['full_grid_exact_readback']and api['pending_ui']==[]
assert set(v['verified_account_ids'])==set(c['pay_now_account_ids'])and len(v['verified_account_ids'])==len(c['pay_now_account_ids']) and hp['accounts']==len(c['pay_now_account_ids']) and hp['full_grid_readback']
assert set(x['account_id']for x in json.loads((hd/'targets.json').read_text()))==set(c['pay_now_account_ids'])
assert json.loads((H/'september-invoice-ledger.json').read_text())==inv
assert struct['status']=='snapshot_readback_pass'and struct['accounts']==len(c['account_ids'])
proof_logs={json.loads(p.read_text().splitlines()[-1])['account_id']:json.loads(p.read_text().splitlines()[-1])for p in B.glob('d*-publish.log')}
assert set(proof_logs)==renewed
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);g.load_env();t=g.service_account_access_token();status,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save('full-workbook-readback.json',after)
 aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};sid=c['sheet_id'];assert set(aa)==set(bb)
 other_unchanged=all(aa[k]==bb[k]for k in aa if k!=sid);assert other_unchanged,'other_sheet_data_changed'
 for k in aa:assert aa[k]['properties']==bb[k]['properties'],'sheet_properties_changed'
 am=mapping(aa[sid]);bm=mapping(bb[sid]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id']for p in plan['planned']}
 assert all(am[k][0]==bm[k][0]for k in am),'account_row_changed'
 assert uv(aa[sid]['data'][0]['rowData'][0]['values'][7])=={'stringValue':c['pay_now_column']}
 blanks=[];countd=0
 for p in plan['planned']:
  aid=p['id'];ri,cs=am[aid];ori,old=bm[aid]
  assert uv(cs[0])=={'stringValue':p['name']}and uv(cs[1])=={'stringValue':p['method']}and uv(cs[2])=={'stringValue':p['default']}
  for col,key in[(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
   assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key]),'cgij_mismatch_'+aid
   assert plan['collected_at']in cs[col]['note']and p['timezone']in cs[col]['note']
  today=datetime.fromisoformat(plan['collected_at']).astimezone(zone(p['timezone'])).date();assert p['average_period']=={'since':str(today-timedelta(days=3)),'until':str(today-timedelta(days=1))}
  assert p['month_period']['since']==c['month_since']and p['month_period']['until']==str(min(today,date.fromisoformat(c['month_until'])))
  proof=dl['accounts'].get(aid)
  if not uv(cs[3]):
   assert not proof or proof.get('status')=='no_charge_located'or not proof.get('latest_card');blanks.append({'account_id':aid,'name':p['name'],'reason':'no_charge_located'if proof and proof.get('status')=='no_charge_located'else'no_historical_instrument_proof'})
  else:
   assert proof and proof.get('latest_card')and proof['latest_card']['status']=='Paid';lc=proof['latest_card'];assert Decimal(str(uv(cs[3])['numberValue']))==Decimal(lc['amount']);assert all(str(x)in cs[3].get('note','')for x in[lc['date'],lc['method'],proof['read_at']]);countd+=1
  if aid in renewed:
   assert proof and Path(proof['receipt']).resolve()==((B/'historical-card-history/full-period' if aid in historical_renewed else B/'card-history'/('empty-viewport/' if aid=='1770569568407466' else ''))/(aid+'-receipt.json')).resolve();assert proof_logs[aid]['status']=='pc1_proof_recorded_and_sheet_readback_pass'
  else:assert cs[3]==old[3],'historical_d_unexpected_change_'+aid
  if aid in c['pay_now_account_ids']:
   h=hl['accounts'][aid];r=json.loads((hd/(aid+'-receipt.json')).read_text());check=v['accounts_list_checks'][aid];assert check['balance_label']=='Outstanding balance'and check['authority_message_id']=='1570815017794674749'
   assert check['business_id']==c['business_id']and check['row_account_id']==aid and check['name']==p['name']and check['valid_billing_list']is True
   assert Decimal(str(uv(cs[7])['numberValue']))==Decimal(h['amount'])==Decimal(r['amount'])==Decimal(check['balance_usd']);assert h['read_at']==r['read_at']and h['read_at']in cs[7].get('note','')and h['source']in cs[7].get('note','')and h['source']==c['h_source'];assert Path(h['receipt']).resolve()==(hd/(aid+'-receipt.json')).resolve()and Path(h['screenshot']).exists()
  else:assert cs[7]==old[7]
  iv=inv['by_account'].get(aid)
  if iv:
   expected=iv['invoice']if Decimal(iv['due'])>0 and iv['status']!='Paid'else None;assert uv(cs[4]).get('stringValue')==expected;assert Decimal(str(uv(cs[5])['numberValue']))==Decimal(iv['due'])
  else:assert not uv(cs[4]);assert uv(cs[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
 left=copy.deepcopy(bb[sid]);right=copy.deepcopy(aa[sid]);account_rows={ri for ri,_ in am.values()};renewed_rows={am[aid][0]for aid in renewed}
 # Exact non-target authored parity; monetary subtotal/formula cells are independently checked by native validator.
 for sh in[left,right]:
  for block in sh.get('data',[]):
   for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
    for ci,cell in enumerate(row.get('values',[]),block.get('startColumn',0)):
     allowed=set()
     if ci in[4,5]and ri<=max(account_rows)+3:allowed|={'userEnteredValue','userEnteredFormat','note'}
     if ri in account_rows and ci==2:allowed.add('userEnteredValue')
     if(ri in account_rows or ri==0)and ci in[6,8,9]:allowed|={'userEnteredValue','note'}
     if ri in renewed_rows and ci==3:allowed|={'userEnteredValue','userEnteredFormat','note'}
     if ci==7:allowed|={'userEnteredValue','userEnteredFormat','note'}
     for key in['effectiveValue','formattedValue','effectiveFormat']:cell.pop(key,None)
     for key in allowed:cell.pop(key,None)
 assert left==right,'outside_authored_write_masks_changed'
 lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 jd=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in(jd if isinstance(jd,list)else jd['jobs'])if x['id']==c['cron_job_id']);oldj=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==oldj['fire_claim']['by'] and j['last_dispatch']==oldj['last_dispatch'] and j['last_dispatch']['scheduled_at']=='2026-11-27T21:02:00-05:00';assert j['schedule']==oldj['schedule']and j['timezone']==oldj['timezone']and j['enabled'];assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
 def tabs(full):return[e.get('label','').split(' - Memory usage')[0]for e in full.get('elements',[])if e.get('role')=='TabItem'and e.get('bounds',[0,99999])[1]<50]
 original=tabs(json.loads((B/'surface-elements.json').read_text()));assert len(original)>0;assert tabs(json.loads((B/'surface-final/surface-elements.json').read_text()))==original,'final_browser_tabs_changed'
 for aid in renewed:
  for suffix in ['before','after']:
   d=json.loads(((B/'historical-card-history/full-period' if aid in historical_renewed else B/'card-history'/('empty-viewport/' if aid=='1770569568407466' else ''))/(aid+'-tabs-'+suffix+'.json')).read_text());assert tabs(d)==original,'original_browser_tabs_changed'
 receipt={'status':'completed_validated','business_refresh_complete':True,'execution_mode':'scheduled','scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'financial-validation.json'),'accounts':len(c['account_ids']),'groups':struct['groups'],'fresh_metrics_count':len(c['account_ids']),'api_run_dir':str(api_dir),'api_collected_at':plan['collected_at'],'invoice_run_dir':str(inv_dir),'invoice_period':inv['invoice_period'],'invoice_pending':inv['unpaid_in_current_tab'],'invoice_due_usd':inv['tab_total_usd'],'invoice_outside':inv['outside_current_tab'],'fresh_h_count':len(c['pay_now_account_ids']),'h_run_dir':str(hd),'h_source':c['h_source'],'h_usd':hp['sum_usd'],'h_times':sorted({hl['accounts'][i]['read_at']for i in c['pay_now_account_ids']}),'pending_ui':[],'renewed_d_ids':sorted(renewed),'renewed_d_count':len(renewed),'current_d_event_count':len(current_renewed),'historical_d_selected_period_empty_ids':sorted(historical_renewed),'historical_blank_d':blanks,'historical_d_values_ledger_validated':countd,'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'h_ledger_to_live_sheet_exact':True,'other_sheet_data_unchanged':other_unchanged,'other_sheets_count':len(aa)-1,'outside_write_masks_preserved':True,'structural_validation':struct,'lease_free':True,'average_periods':sorted({(p['average_period']['since'],p['average_period']['until'])for p in plan['planned']}),'month_periods':sorted({(p['month_period']['since'],p['month_period']['until'])for p in plan['planned']}),'browser_tabs_preserved':True,'browser_tabs_original_count':len(original),'payments_executed':0,'meta_writes':0,'billing_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending','delivery':'cron_auto_final_only','report_infra_delivery_constraint':'no_manual_sends_this_tick','totals_usd':{k:str(sum((Decimal(p[k])for p in plan['planned']),Decimal(0)))for k in['average_daily','balance','month_spend']}}
 save('financial-validation.json',receipt);print(json.dumps({k:v for k,v in receipt.items()if k not in['historical_blank_d','h_times','structural_validation']},ensure_ascii=False));print('historical_d_blanks',len(blanks))
