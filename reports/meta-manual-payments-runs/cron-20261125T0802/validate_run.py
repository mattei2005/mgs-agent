import os,sys,json,shutil,fcntl,re,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
launcher=shutil.which('hermes');assert launcher;R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments'
def save(p,d):
 assert not p.exists(),'immutable_exists_'+p.name;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
def log(n):return [json.loads(l)for l in(B/(n+'.log')).read_text().splitlines()if l.startswith('{')][-1]
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for row in block.get('rowData',[]):
   cells=row.get('values',[])
   if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):
    assert m[1]not in out;out[m[1]]=cells
 return out
def uv(c):return c.get('userEnteredValue',{})
with(H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);c=json.loads((H/'digital-trust-workbook-contract.json').read_text());original=json.loads((B/'contract-before.json').read_text());jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in jobs['jobs'] if x['id']==c['cron_job_id']);jb=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==jb['fire_claim']['by'] and j['last_dispatch']==jb['last_dispatch'];assert j['last_dispatch']['scheduled_at']=='2026-11-25T08:02:00-05:00'
 for k in ['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','h_source','month_since','month_until','recurring_scope','balance_views']:
  assert (set(c[k])==set(original[k]) and len(c[k])==len(original[k])) if k in ['account_ids','pay_now_account_ids'] else c[k]==original[k],k
 assert c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled'];assert not set(c['account_ids'])&set(c['archived_account_ids']);g.load_env();t=g.service_account_access_token();st,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert st==200;save(B/'final-workbook-readback.json',after)
 before=json.loads((B/'workbook-before.json').read_text());aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};assert set(aa)==set(bb);other={str(k):aa[k]==bb[k]for k in aa if k!=c['sheet_id']};assert all(other.values()),'frozen_sheet_changed';am=mapping(aa[c['sheet_id']]);assert set(am)==set(c['account_ids']) and len(am)==len(c['account_ids'])
 api=log('api_final1');assert api['status']=='updated_validated' and not api['pending_ui'];plan=json.loads((Path(api['run_dir'])/'plan.json').read_text());iv=json.loads((Path(log('invoices')['run_dir'])/'invoice-collection.json').read_text());assert iv==json.loads((H/'september-invoice-ledger.json').read_text());hl=json.loads((H/'pc1-pay-now-ledger.json').read_text());dl=json.loads((H/'pc1-card-ledger.json').read_text());hdir=Path((B/'h_run_dir').read_text());checks=json.loads((hdir/'visual-verification.json').read_text());assert set(checks['verified_account_ids'])==set(c['pay_now_account_ids']);assert set(hl['fresh_account_ids'])==set(c['pay_now_account_ids']);blank=[];h_times={};renewed=[]
 for p in plan['planned']:
  aid=p['id'];cs=am[aid];assert uv(cs[2])=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
  local=datetime.fromisoformat(plan['collected_at']).astimezone(__import__('zoneinfo').ZoneInfo(p['timezone']));today=local.date();assert p['month_period']['since']==c['month_since'] and p['month_period']['until']==min(today,__import__('datetime').date.fromisoformat(c['month_until'])).isoformat();assert p['average_period']['since']==(today-__import__('datetime').timedelta(days=3)).isoformat() and p['average_period']['until']==(today-__import__('datetime').timedelta(days=1)).isoformat()
  inv=iv['by_account'].get(aid)
  if inv:
   expected=inv['invoice']if Decimal(inv['due'])>0 and inv['status']!='Paid'else None;assert uv(cs[4]).get('stringValue')==expected;assert Decimal(str(uv(cs[5])['numberValue']))==Decimal(inv['due'])
  else:assert not uv(cs[4]);assert uv(cs[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
  if aid in c['pay_now_account_ids']:
   hr=hl['accounts'][aid];raw=json.loads(Path(hr['receipt']).read_text());check=checks['accounts_list_checks'][aid];assert Decimal(str(uv(cs[7])['numberValue']))==Decimal(hr['amount'])==Decimal(check['balance_usd'])==Decimal(raw['amount']);assert hr['source']==raw['source']==c['h_source'];assert hr['read_at']==raw['read_at'] and hr['read_at']in cs[7]['note'];assert check['business_id']==c['business_id'] and check['row_account_id']==aid and check['name']==p['name'] and check['balance_label']=='Outstanding balance';h_times[aid]=hr['read_at']
  proof=dl['accounts'].get(aid)
  if proof:
   card=proof.get('latest_card')
   if card:assert Decimal(str(uv(cs[3])['numberValue']))==Decimal(card['amount']) and proof['read_at']in cs[3]['note'] and card['method']in cs[3]['note']
   else:assert not uv(cs[3]) and proof['status']=='no_charge_located'
  if not uv(cs[3]):blank.append({'account_id':aid,'name':p['name'],'reason':proof['status']if proof else'no_historical_instrument_proof'})
  if (B/('proof_'+aid+'.log')).exists():
   r=log('proof_'+aid);assert r['status']=='pc1_proof_recorded_and_sheet_readback_pass';renewed.append(aid)
 assert set(p['id']for p in plan['planned'])==set(c['account_ids']);assert not set(renewed)-set(c['account_ids']);assert log('structural-final')['status']=='snapshot_readback_pass'
 lease=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked'];cleanup=log('cleanup');assert cleanup['original_tabs']==cleanup['final_tabs'] and cleanup['closed_owned_tabs']==2
 r={'status':'completed_validated_with_historical_gaps','business_refresh_complete':True,'scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'receipt.json'),'accounts':len(am),'groups':log('structural-final')['groups'],'fresh_metrics_count':len(plan['planned']),'api_run_dir':api['run_dir'],'validated_metrics_at':plan['collected_at'],'fresh_h_count':len(h_times),'h_read_times':h_times,'h_run_dir':str(hdir),'h_source':c['h_source'],'pending_ui':[],'D_verified_published_ids':sorted(renewed),'historical_blank_d':blank,'pending_new_historical_d':[i for i in c['pending_new_account_fields']['D_account_ids']if i not in renewed],'invoices':{'period':iv['invoice_period'],'pending':iv['unpaid_in_current_tab'],'due_usd':iv['tab_total_usd'],'source_run_dir':log('invoices')['run_dir']},'average_periods':sorted({tuple(p['average_period'][k]for k in ['since','until'])for p in plan['planned']}),'month_periods':sorted({tuple(p['month_period'][k]for k in ['since','until'])for p in plan['planned']}),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_source_to_live_sheet_and_note_exact':True,'d_existing_ledger_to_live_sheet_exact':True,'h_original_collection_times_preserved':True,'other_sheet_data_unchanged':True,'frozen_sheet_full_equality':other,'archived_accounts_not_collected':len(c['archived_account_ids']),'structural_validation':log('structural-final'),'lease_free':True,'original_tabs_preserved':True,'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_transport_restricted_no_manual_messages','historical_line_history_attempt':{'account_id':'1542257646409395','result':'unverified_navigation','diagnosis':'Background link returned unchanged page; foreground action refused exact HWND because separate Chrome Save As dialog was foreground. No auth gate. Unrelated dialog left untouched; no historical instrument fabricated.','evidence':str(B/'d-full-pixel/1542257646409395-action-failure.json'),'screenshot':str(B/'foreground-conflict.png'),'scope':'historical gaps, no current generic-payment pending_ui events'},'delivery':'cron_final_response_only'}
 assert datetime.fromisoformat(r['next_run_at'])>datetime.now().astimezone();save(B/'receipt.json',r);print(json.dumps({'status':r['status'],'accounts':len(am),'fresh_h':len(h_times),'renewed_d_proofs':len(renewed),'historical_blank_d':len(blank),'no_charge_located':[x['name']for x in blank if x['reason']=='no_charge_located'],'pending_new_historical_d':r['pending_new_historical_d'],'frozen_sheets_unchanged':other,'periods':[r['average_periods'],r['month_periods']],'invoices':r['invoices'],'lease_free':True}))
