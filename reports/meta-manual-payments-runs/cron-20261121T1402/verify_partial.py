import os,sys,json,shutil,re,subprocess,fcntl,copy
from pathlib import Path
from datetime import datetime
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');C=H/'digital-trust-workbook-contract.json'
c=json.loads(C.read_text());before=json.loads((B/'workbook-before.json').read_text())
def log(name):return [json.loads(s) for s in (B/(name+'.log')).read_text().splitlines() if s.startswith('{')][-1]
def save(name,d):
 p=B/name;assert not p.exists(),'immutable_exists_'+name;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def uv(v):return v.get('userEnteredValue',{})
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
   vs=row.get('values',[])
   if vs and (m:=re.search(r'^ID da conta: (\d+)\b',vs[0].get('note',''))):
    assert m[1] not in out;out[m[1]]=(ri,vs)
 return out
api_dir=Path(log('api')['run_dir']);inv_dir=Path(log('invoices')['run_dir']);h_dir=Path(log('h_prepare')['run_dir'])
plan=json.loads((api_dir/'plan.json').read_text());api=json.loads((api_dir/'receipt.json').read_text());inv=json.loads((inv_dir/'invoice-collection.json').read_text());hl=json.loads((H/'pc1-pay-now-ledger.json').read_text());dl=json.loads((H/'pc1-card-ledger.json').read_text())
assert api['status']=='updated_metrics_pending_card_history' and api['accounts']==55 and api['full_grid_exact_readback']
assert set(x['account_id']for x in json.loads((h_dir/'targets.json').read_text()))==set(c['pay_now_account_ids'])
assert len(c['account_ids'])==55 and len(c['pay_now_account_ids'])==40
assert json.loads((H/'september-invoice-ledger.json').read_text())==inv
struct=log('structural-validation');assert struct['status']=='snapshot_readback_pass'
with (H/'writer.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 g.load_env();t=g.service_account_access_token();status,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save('partial-workbook-readback.json',after)
 aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};sid=c['sheet_id'];assert set(aa)==set(bb)
 other_unchanged=all(aa[k]==bb[k] for k in aa if k!=sid)
 assert other_unchanged,'other_sheet_data_changed'
 for k in aa:assert aa[k]['properties']==bb[k]['properties'],'sheet_properties_changed'
 am=mapping(aa[sid]);bm=mapping(bb[sid]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id']for p in plan['planned']}
 assert all(am[k][0]==bm[k][0]for k in am),'account_row_changed'
 blank=[];countd=0
 for p in plan['planned']:
  aid=p['id'];ri,v=am[aid];ori,old=bm[aid]
  assert uv(v[0])=={'stringValue':p['name']} and uv(v[1])=={'stringValue':p['method']}
  assert uv(v[2])=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
   assert Decimal(str(uv(v[col])['numberValue']))==Decimal(p[key]),'cgij_mismatch_'+aid
   assert plan['collected_at']in v[col]['note'] and p['timezone']in v[col]['note']
  for col in [0,1,3,7]:assert v[col]==old[col],'preserved_cell_changed_'+aid+'_'+str(col)
  proof=dl['accounts'].get(aid)
  if not uv(v[3]):
   assert not proof or proof.get('status')=='no_charge_located' or not proof.get('latest_card')
   blank.append({'account_id':aid,'name':p['name'],'reason':'no_charge_located'if proof and proof.get('status')=='no_charge_located'else'no_historical_instrument_proof'})
  else:
   assert proof and proof.get('latest_card') and proof['latest_card']['status']=='Paid';lc=proof['latest_card']
   assert Decimal(str(uv(v[3])['numberValue']))==Decimal(lc['amount'])
   assert all(str(x)in v[3].get('note','')for x in [lc['date'],lc['method'],proof['read_at']]);countd+=1
  if aid in c['pay_now_account_ids']:
   h=hl['accounts'][aid];assert Decimal(str(uv(v[7])['numberValue']))==Decimal(h['amount'])
   assert h['read_at']in v[7].get('note','')and h['source']in v[7].get('note','')and h['source']==c['h_source']
   assert Path(h['receipt']).exists()and Path(h['screenshot']).exists()
  iv=inv['by_account'].get(aid)
  if iv:
   expected=iv['invoice']if Decimal(iv['due'])>0 and iv['status']!='Paid'else None
   assert uv(v[4]).get('stringValue')==expected
   assert Decimal(str(uv(v[5])['numberValue']))==Decimal(iv['due'])
  else:
   assert not uv(v[4])
   assert uv(v[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
 # Strict authored preservation outside this execution's exact write masks.
 left=copy.deepcopy(bb[sid]);right=copy.deepcopy(aa[sid]);account_rows={ri for ri,_ in am.values()}
 for sh in [left,right]:
  for block in sh.get('data',[]):
   for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
    for ci,cell in enumerate(row.get('values',[]),block.get('startColumn',0)):
     allowed=set()
     if ci in [4,5] and ri<=max(account_rows)+3:allowed|={'userEnteredValue','userEnteredFormat','note'}
     if ri in account_rows and ci==2:allowed.add('userEnteredValue')
     if (ri in account_rows or ri==0)and ci in [6,8,9]:allowed|={'userEnteredValue','note'}
     for key in ['effectiveValue','formattedValue','effectiveFormat']:cell.pop(key,None)
     for key in allowed:cell.pop(key,None)
 assert left==right,'outside_authored_write_masks_changed'
 lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 jd=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in (jd if isinstance(jd,list)else jd['jobs'])if x['id']==c['cron_job_id']);oldj=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==oldj['fire_claim']['by']and j['last_dispatch']==oldj['last_dispatch']
 assert j['schedule']==oldj['schedule']and j['timezone']==oldj['timezone']and j['enabled'];assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
 receipt={'status':'partial_validated_blocked_provider','business_refresh_complete':False,'scheduled_at':j['last_dispatch']['scheduled_at'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'partial-validation.json'),'accounts':55,'groups':struct['groups'],'fresh_metrics_count':55,'api_run_dir':str(api_dir),'api_collected_at':plan['collected_at'],'invoice_run_dir':str(inv_dir),'invoice_period':inv['invoice_period'],'invoice_pending':inv['unpaid_in_current_tab'],'invoice_due_usd':inv['tab_total_usd'],'invoice_outside':inv['outside_current_tab'],'fresh_h_count':0,'preserved_h_count':40,'preserved_h_ids':c['pay_now_account_ids'],'h_run_dir':str(h_dir),'h_source':c['h_source'],'h_values_notes_original_times_preserved':True,'pending_ui':api['pending_ui'],'historical_blank_d':blank,'historical_d_values_ledger_validated':countd,'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'h_ledger_to_live_sheet_exact':True,'d_values_notes_preserved':True,'other_sheet_data_unchanged':other_unchanged,'other_sheets_count':len(aa)-1,'outside_write_masks_preserved':True,'structural_validation':struct,'lease_free':True,'average_periods':sorted({(p['average_period']['since'],p['average_period']['until'])for p in plan['planned']}),'month_periods':sorted({(p['month_period']['since'],p['month_period']['until'])for p in plan['planned']}),'blocker':{'reason':'Meta This page is not available right now; technical error visible','evidence':str(B/'surface.png'),'authentication_gate':False,'inputs_stopped':True,'inputs':0,'reloads':0,'billing_changes':0},'browser_tabs_preserved':True,'browser_tab_exact_parity':'no input or tab mutation issued; exact initial AX and pixels retained','payments_executed':0,'meta_writes':0,'billing_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'cron_final_response_only','totals_usd':{k:str(sum((Decimal(p[k])for p in plan['planned']),Decimal(0)))for k in ['average_daily','balance','month_spend']}}
 save('partial-validation.json',receipt)
 print(json.dumps({'status':receipt['status'],'accounts':55,'h_fresh':0,'h_preserved':40,'pending_ui':len(api['pending_ui']),'historical_blank_d':len(blank),'other_sheet_data_unchanged':other_unchanged,'outside_write_masks_preserved':True,'lease_free':True,'next_run_at':j['next_run_at']}))
