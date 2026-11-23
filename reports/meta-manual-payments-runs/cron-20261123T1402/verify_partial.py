import os,sys,json,shutil,re,fcntl,copy,subprocess
from pathlib import Path
from datetime import datetime,date,timedelta
from decimal import Decimal
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments'
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'));import mgs_google_workspace_auth as g
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');sys.path.insert(0,str(S));from refresh_workbook import zone
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());before=json.loads((B/'workbook-before.json').read_text())
def log(n):return [json.loads(s)for s in(B/(n+'.log')).read_text().splitlines()if s.startswith('{')][-1]
def save(n,d):
 p=B/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def uv(v):return v.get('userEnteredValue',{})
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
   vs=row.get('values',[])
   if vs and(m:=re.search(r'^ID da conta: (\d+)\b',vs[0].get('note',''))):assert m[1]not in out;out[m[1]]=(ri,vs)
 return out
initial=log('api');ad=Path(initial['run_dir']);hd=Path(log('h_prepare')['run_dir']);ivd=Path(log('invoices')['run_dir']);plan=json.loads((ad/'plan.json').read_text());inv=json.loads((ivd/'invoice-collection.json').read_text());v=json.loads((hd/'visual-verification.json').read_text());verified=set(v['verified_account_ids']);hl=json.loads((H/'pc1-pay-now-ledger.json').read_text());dl=json.loads((H/'pc1-card-ledger.json').read_text());hp=log('h-publish');struct=log('structural-validation')
assert len(c['account_ids'])==55 and len(c['pay_now_account_ids'])==40 and verified=={'336562339356179'}
assert initial['status']=='updated_metrics_pending_card_history' and len(initial['pending_ui'])==3
assert hp['full_grid_readback'] and hp['accounts']==1 and hp['preserved_accounts']==39
assert json.loads((H/'september-invoice-ledger.json').read_text())==inv
assert struct['status']=='snapshot_readback_pass' and struct['accounts']==55
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);g.load_env();t=g.service_account_access_token();status,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200;save('full-workbook-readback-retry.json',after)
 aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};sid=c['sheet_id'];assert set(aa)==set(bb)
 other=all(aa[k]==bb[k]for k in aa if k!=sid);assert other
 for k in aa:assert aa[k]['properties']==bb[k]['properties']
 am=mapping(aa[sid]);bm=mapping(bb[sid]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id']for p in plan['planned']}
 assert all(am[k][0]==bm[k][0]for k in am)
 assert uv(aa[sid]['data'][0]['rowData'][0]['values'][7])=={'stringValue':c['pay_now_column']}
 blanks=[];dcount=0
 for p in plan['planned']:
  aid=p['id'];ri,cs=am[aid];_,old=bm[aid]
  assert uv(cs[0])=={'stringValue':p['name']}and uv(cs[1])=={'stringValue':p['method']}and uv(cs[2])=={'stringValue':p['default']}
  for col,key in[(6,'average_daily'),(8,'balance'),(9,'month_spend')]:
   assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key]);assert plan['collected_at']in cs[col]['note']and p['timezone']in cs[col]['note']
  today=datetime.fromisoformat(plan['collected_at']).astimezone(zone(p['timezone'])).date();assert p['average_period']=={'since':str(today-timedelta(days=3)),'until':str(today-timedelta(days=1))};assert p['month_period']['since']==c['month_since']and p['month_period']['until']==str(min(today,date.fromisoformat(c['month_until'])))
  assert cs[3]==old[3]
  proof=dl['accounts'].get(aid)
  if not uv(cs[3]):blanks.append({'account_id':aid,'name':p['name'],'reason':'no_charge_located'if proof and proof.get('status')=='no_charge_located'else'no_historical_instrument_proof'})
  else:
   assert proof and proof.get('latest_card');lc=proof['latest_card'];assert lc['status']=='Paid' and Decimal(str(uv(cs[3])['numberValue']))==Decimal(lc['amount']);assert all(str(x)in cs[3].get('note','')for x in[lc['date'],lc['method'],proof['read_at']]);dcount+=1
  if aid in verified:
   h=hl['accounts'][aid];r=json.loads((hd/(aid+'-receipt.json')).read_text());ch=v['accounts_list_checks'][aid]
   assert ch['valid_billing_list'] and ch['business_id']==c['business_id']and ch['row_account_id']==aid and ch['name']==p['name']and ch['balance_label']=='Outstanding balance'and ch['authority_message_id']=='1570815017794674749'
   assert Decimal(str(uv(cs[7])['numberValue']))==Decimal(h['amount'])==Decimal(r['amount'])==Decimal(ch['balance_usd']);assert h['read_at']==r['read_at']and h['read_at']in cs[7]['note']and h['source']in cs[7]['note']and h['source']==c['h_source'];assert Path(h['receipt']).resolve()==(hd/(aid+'-receipt.json')).resolve()
  else:assert cs[7]==old[7]
  iv=inv['by_account'].get(aid)
  if iv:
   expected=iv['invoice']if Decimal(iv['due'])>0 and iv['status']!='Paid'else None;assert uv(cs[4]).get('stringValue')==expected;assert Decimal(str(uv(cs[5])['numberValue']))==Decimal(iv['due'])
  else:assert not uv(cs[4]);assert uv(cs[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
 left=copy.deepcopy(bb[sid]);right=copy.deepcopy(aa[sid]);ars={ri for ri,_ in am.values()};hrs={am[aid][0]for aid in verified}
 for sh in[left,right]:
  for block in sh.get('data',[]):
   for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
    for ci,cell in enumerate(row.get('values',[]),block.get('startColumn',0)):
     allowed=set()
     if ci in[4,5]and ri<=max(ars)+3:allowed|={'userEnteredValue','userEnteredFormat','note'}
     if ri in ars and ci==2:allowed.add('userEnteredValue')
     if(ri in ars or ri==0)and ci in[6,8,9]:allowed|={'userEnteredValue','note'}
     if ri in hrs and ci==7:allowed|={'userEnteredValue','userEnteredFormat','note'}
     if ri not in ars and ci==7 and cell.get('note'):
      assert any(s in cell['note']for s in['Fonte H nas 40 contas de linha;','Soma H das 40 contas de linha;'])
      assert ('1 verificadas nesta publicação, 39 preservadas' in cell['note'] or '1 atualizadas, 39 históricas preservadas' in cell['note'] or '40 verificadas nesta publicação, 0 preservadas' in cell['note'] or '40 atualizadas, 0 históricas preservadas' in cell['note'])
      allowed.add('note')
     for key in['effectiveValue','formattedValue','effectiveFormat']:cell.pop(key,None)
     for key in allowed:cell.pop(key,None)
 assert left==right,'outside_write_masks_changed'
 lease=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in(jobs if isinstance(jobs,list)else jobs['jobs'])if x['id']==c['cron_job_id']);oj=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==oj['fire_claim']['by'] and j['last_dispatch']==oj['last_dispatch'];assert j['schedule']==oj['schedule']and j['enabled']and j['timezone']==oj['timezone'];assert datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
receipt={'status':'partial_provider_technical_error','business_refresh_complete':False,'scheduled_at':j['last_dispatch']['scheduled_at'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'financial-validation.json'),'accounts':55,'groups':struct['groups'],'fresh_metrics_count':55,'api_run_dir':str(ad),'api_collected_at':plan['collected_at'],'invoice_run_dir':str(ivd),'invoice_period':inv['invoice_period'],'invoice_pending':inv['unpaid_in_current_tab'],'invoice_due_usd':inv['tab_total_usd'],'invoice_outside':inv['outside_current_tab'],'fresh_h_count':1,'h_run_dir':str(hd),'h_source':c['h_source'],'h_verified_ids':sorted(verified),'h_pending_ids':sorted(set(c['pay_now_account_ids'])-verified),'h_preserved_historical_count':39,'pending_ui':initial['pending_ui'],'renewed_d_ids':[],'historical_blank_d':blanks,'historical_d_values_ledger_validated':dcount,'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'published_h_source_parity':True,'other_sheet_data_unchanged':other,'other_sheets_count':len(aa)-1,'outside_write_masks_preserved':True,'structural_validation':struct,'lease_free':True,'blocker':'Native Meta Accounts displayed This page is not available right now / technical error after first UIA collection; no authentication gate. Preserved surface-recovery1/surface.png. Stopped inputs without reload or alternate profile.','authentication_gate_confirmed':False,'payments_executed':0,'meta_writes':0,'billing_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'cron_final_response_only','owner':'zeus','resume':'Same existing recurring job; revalidate provider surface and reconcile current ledgers before pending H/D steps. No duplicate job/writer created.'}
save('financial-validation.json',receipt);print(json.dumps({k:receipt[k]for k in['status','accounts','fresh_metrics_count','fresh_h_count','h_preserved_historical_count','invoice_pending','historical_d_values_ledger_validated','other_sheet_data_unchanged','lease_free','next_run_at']},ensure_ascii=False))
