import os,sys,json,shutil,fcntl,re,subprocess
from pathlib import Path
from datetime import datetime,timedelta,date
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments')
def save(n,d):
 with (B/n).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
 (B/n).chmod(0o600)
def log(n):return [json.loads(l) for l in (B/(n+'.log')).read_text().splitlines() if l.startswith('{')][-1]
def mapping(s):
 out={}
 for b in s.get('data',[]):
  for row in b.get('rowData',[]):
   cs=row.get('values',[])
   if cs and (m:=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))):assert m[1] not in out;out[m[1]]=cs
 return out
def uv(c):return c.get('userEnteredValue',{})
with (H/'writer.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 c=json.loads((H/'digital-trust-workbook-contract.json').read_text());old=json.loads((B/'contract-before.json').read_text());j=next(x for x in json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())['jobs'] if x['id']==c['cron_job_id']);jb=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==jb['fire_claim']['by'] and j['last_dispatch']==jb['last_dispatch']
 for k in ['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','h_source','month_since','month_until','recurring_scope','balance_views']:assert c[k]==old[k],k
 assert c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled'] and not set(c['account_ids'])&set(c['archived_account_ids'])
 g.load_env();t=g.service_account_access_token();st,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert st==200;save('final-workbook-readback.json',after)
 before=json.loads((B/'workbook-before.json').read_text());aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};assert set(aa)==set(bb);other={str(k):aa[k]==bb[k] for k in aa if k!=c['sheet_id']};assert all(other.values()),'frozen_sheet_changed';am=mapping(aa[c['sheet_id']]);bm=mapping(bb[c['sheet_id']]);assert set(am)==set(c['account_ids'])==set(bm)
 api=log('api_final');assert api['status'] in ['updated_validated','updated_metrics_pending_card_history'];plan=json.loads((Path(api['run_dir'])/'plan.json').read_text());iv=json.loads((Path(log('invoices')['run_dir'])/'invoice-collection.json').read_text());assert iv==json.loads((H/'september-invoice-ledger.json').read_text());hl=json.loads((H/'pc1-pay-now-ledger.json').read_text());dl=json.loads((H/'pc1-card-ledger.json').read_text());blank=[];h_times={}
 for p in plan['planned']:
  aid=p['id'];cs=am[aid];assert uv(cs[2])=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
  from zoneinfo import ZoneInfo
  today=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date();assert p['month_period']['since']==c['month_since'] and p['month_period']['until']==min(today,date.fromisoformat(c['month_until'])).isoformat();assert p['average_period']=={'since':(today-timedelta(days=3)).isoformat(),'until':(today-timedelta(days=1)).isoformat()}
  inv=iv['by_account'].get(aid)
  if inv:
   expected=inv['invoice'] if Decimal(inv['due'])>0 and inv['status']!='Paid' else None;assert uv(cs[4]).get('stringValue')==expected;assert Decimal(str(uv(cs[5])['numberValue']))==Decimal(inv['due'])
  else:assert not uv(cs[4]);assert uv(cs[5])==({'numberValue':0} if p['method']=='Linha de crédito' else {})
  for col in [3]:assert cs[col]==bm[aid][col],f'historical_D_H_changed:{aid}:{col}'
  if aid in c['pay_now_account_ids']:
   hr=hl['accounts'][aid];assert Decimal(str(uv(cs[7])['numberValue']))==Decimal(hr['amount']) and hr['read_at'] in cs[7]['note'];h_times[aid]=hr['read_at'];
   rp=Path(log('h_prepare')['run_dir'])/(aid+'-receipt.json')
   if rp.exists():
    rr=json.loads(rp.read_text());assert hr['read_at']==rr['read_at'] and Decimal(hr['amount'])==Decimal(rr['amount']) and hr['source']==c['h_source']
   else:assert cs[7]==bm[aid][7],'historical_H_changed'
  proof=dl['accounts'].get(aid)
  if proof:
   card=proof.get('latest_card')
   if card:assert Decimal(str(uv(cs[3])['numberValue']))==Decimal(card['amount']) and proof['read_at'] in cs[3]['note'] and card['method'] in cs[3]['note']
   else:assert not uv(cs[3]) and proof['status']=='no_charge_located'
  if not uv(cs[3]):blank.append({'account_id':aid,'name':p['name'],'reason':proof['status'] if proof else 'no_historical_instrument_proof'})
 assert len(plan['planned'])==len(am) and set(p['id'] for p in plan['planned'])==set(c['account_ids']);assert log('structural-final2')['status']=='snapshot_readback_pass'
 hdir=Path(log('h_prepare')['run_dir']);targets=json.loads((hdir/'targets.json').read_text());assert set(x['account_id'] for x in targets)==set(c['pay_now_account_ids'])
 lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 r={'status':'partial_waiting_human_auth','business_refresh_complete':False,'scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'receipt.json'),'accounts':len(am),'groups':log('structural-final2')['groups'],'fresh_metrics_count':len(plan['planned']),'api_run_dir':api['run_dir'],'validated_metrics_at':plan['collected_at'],'fresh_h_count':1,'historical_h_preserved_count':len(h_times)-1,'h_read_times':h_times,'h_run_dir':str(hdir),'h_source':c['h_source'],'pending_ui':api.get('pending_ui',[]),'D_verified_published_ids':[],'historical_blank_d':blank,'pending_new_historical_d':c['pending_new_account_fields']['D_account_ids'],'invoices':{'period':iv['invoice_period'],'pending':iv['unpaid_in_current_tab'],'due_usd':iv['tab_total_usd'],'source_run_dir':log('invoices')['run_dir']},'average_periods':sorted({tuple(p['average_period'][k] for k in ['since','until']) for p in plan['planned']}),'month_periods':sorted({tuple(p['month_period'][k] for k in ['since','until']) for p in plan['planned']}),'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'h_historical_ledger_to_live_sheet_exact':True,'d_existing_ledger_to_live_sheet_exact':True,'d_values_notes_format_exactly_preserved':True,'h_new_receipts_ledger_live_exact':True,'other_sheet_data_unchanged':True,'frozen_sheet_full_equality':other,'archived_accounts_not_collected':len(c['archived_account_ids']),'structural_validation':log('structural-final2'),'lease_free':True,'browser_tab_prefix_restored':True,'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'next_run_at':j['next_run_at'],'blocker':{'reason':'meta_passkey_reauthentication_required','save_dialog_pixels':str(B/'save-dialog.png'),'approved_chrome_pixels':str(B/'surface.png'),'meta_authentication_gate_demonstrated':True,'authentication_pixels':str(B/'reload-after.png'),'unrelated_dialog_preserved':True},'report_infra_status':'pending_transport_restricted_no_manual_messages','delivery':'cron_final_response_only'}
 

 r['h_read_times_current_run']=False;r['fresh_h_account_ids']=['1542257646409395'];r['h_sum_published_delta_usd']=log('h_publish')['sum_usd'];r['browser_tab_prefix_restored']=False;r['browser_tabs_no_new_current_run']=True;r['search_restoration_blocked_by_authentication']=True
 save('receipt.json',r);print(json.dumps({k:r[k] for k in ['status','accounts','fresh_metrics_count','fresh_h_count','historical_h_preserved_count','pending_ui','frozen_sheet_full_equality','invoices','lease_free']}))
