import json,os,sys,shutil,fcntl,subprocess,re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';now=datetime.now().astimezone().isoformat()
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
def log(n):return[json.loads(l)for l in(B/(n+'.log')).read_text().splitlines()if l.startswith('{')][-1]
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for row in block.get('rowData',[]):
   cs=row.get('values',[])
   if cs and(m:=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))):assert m[1]not in out;out[m[1]]=cs
 return out
def uv(c):return c.get('userEnteredValue',{})
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);c=json.loads((H/'digital-trust-workbook-contract.json').read_text());orig=json.loads((B/'contract-before.json').read_text());jdata=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text());j=next(x for x in(jdata if isinstance(jdata,list)else jdata['jobs'])if x['id']==c['cron_job_id']);jb=json.loads((B/'job-before.json').read_text());assert j['fire_claim']['by']==jb['fire_claim']['by']and j['last_dispatch']==jb['last_dispatch'];assert j['last_dispatch']['scheduled_at']=='2026-11-24T08:02:00-05:00'
 for k in ['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','h_source','month_since','month_until']:assert c[k]==orig[k]
 g.load_env();t=g.service_account_access_token();st,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert st==200;save(B/'partial-workbook-readback.json',after)
 before=json.loads((B/'workbook-before.json').read_text());aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};assert set(aa)==set(bb);other=all(aa[k]==bb[k]for k in aa if k!=c['sheet_id']);assert other
 am=mapping(aa[c['sheet_id']]);bm=mapping(bb[c['sheet_id']]);assert set(am)==set(bm)==set(c['account_ids']);api=log('api');plan=json.loads((Path(api['run_dir'])/'plan.json').read_text());iv=json.loads((Path(log('invoices')['run_dir'])/'invoice-collection.json').read_text());assert iv==json.loads((H/'september-invoice-ledger.json').read_text())
 for p in plan['planned']:
  aid=p['id'];cs=am[aid];assert uv(cs[2])=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key])and plan['collected_at']in cs[col]['note']
  assert cs[3]==bm[aid][3]and cs[7]==bm[aid][7]
  inv=iv['by_account'].get(aid)
  if inv:
   expected=inv['invoice']if Decimal(inv['due'])>0 and inv['status']!='Paid'else None;assert uv(cs[4]).get('stringValue')==expected;assert Decimal(str(uv(cs[5])['numberValue']))==Decimal(inv['due'])
  else:assert not uv(cs[4]);assert uv(cs[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
 lease=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
 r={'status':'waiting_human','business_refresh_complete':False,'reason':'confirmed_meta_passkey_reauthentication','scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':now,'evidence':str(B/'receipt.json'),'accounts':55,'fresh_metrics_count':55,'api_run_dir':api['run_dir'],'api_collected_at':plan['collected_at'],'invoice_run_dir':log('invoices')['run_dir'],'invoice_period':iv['invoice_period'],'invoice_pending':iv['unpaid_in_current_tab'],'invoice_due_usd':iv['tab_total_usd'],'pending_ui':api['pending_ui'],'fresh_h_count':0,'historical_h_preserved_count':40,'h_run_dir':log('h_prepare')['run_dir'],'h_source':c['h_source'],'h_values_and_notes_unchanged':True,'d_values_and_notes_unchanged':True,'source_parity_partial_cgij_ef':True,'other_sheet_data_unchanged':other,'authentication_gate':{'confirmed_by_real_pixel_inspection':True,'screenshot':str(B/'native-result.png'),'domain':'business.facebook.com','path':'/security/twofactor/reauth/','text':"Rodolfo Mattei · Facebook; Confirm it's you with your passkey",'expected_navigation':'https://business.facebook.com/latest/billing_hub/accounts/?business_id=155263197283282','original_approved_chrome_handle_preserved':True,'owned_tabs_retained_at_gate':2,'no_further_inputs_after_gate':True},'structural_validation':log('structural-validation'),'lease_free':True,'payments_executed':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'report_infra_status':'pending_transport_restricted_no_manual_messages','delivery':'cron_final_response_only_exact_auth_notice','next_step':'Human authenticates Meta in same Rodolfo Chrome on PC1; then reconcile current claim/receipts and resume same authorized job without duplicate writer.'};save(B/'receipt.json',r)
 (B/'contract-pre-blocked.json').write_bytes((H/'digital-trust-workbook-contract.json').read_bytes());c['latest_refresh_qualification']=r;c['general_refresh_blocker']={'status':'waiting_human','reason':r['reason'],'evidence':r['evidence'],'at':now};c['pending_card_history']={'status':'waiting_human_meta_passkey','account_ids':[x['account_id']for x in api['pending_ui']],'pending_ui':api['pending_ui'],'evidence':r['evidence'],'next_step':r['next_step']};save(H/'digital-trust-workbook-contract.json',c);assert json.loads((H/'digital-trust-workbook-contract.json').read_text())==c
p=ROOT/'data/infra-inventory.json'
with(ROOT/'data/.meta-manual-inventory.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);d=json.loads(p.read_text());(B/'inventory-pre-blocked.json').write_bytes(p.read_bytes());ident='meta-manual-payments-cron-20261124T0802';entries=d.setdefault('runtime_artifacts',[]);assert not any(x.get('id')==ident for x in entries if isinstance(x,dict));entry={'id':ident,'agent':'zeus','type':'scheduled_financial_refresh','status':'waiting_human','evidence':r['evidence'],'scheduled_at':r['scheduled_at'],'updated_at':now,'verification':{'fresh_metrics':55,'fresh_h':0,'historical_h_preserved':40,'pending_d':len(api['pending_ui']),'source_parity_partial_cgij_ef':True,'other_sheet_data_unchanged':other,'lease_free':True,'payments':0,'billing_changes':0,'cron_changes':0},'report_infra_status':r['report_infra_status']};entries.append(entry);save(p,d);assert[x for x in json.loads(p.read_text())['runtime_artifacts']if x.get('id')==ident]==[entry]
cp=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Refresh recorrente24nov08:02ET mesmas55contas e40H; mesmo workbook/job','--state','waiting_human: passkey Meta confirmada em pixels no Chrome Rodolfo; API55 e invoices atualizadas/readback; H40 historicos preservados; D5 eventos pendentes; lease livre; nenhum pagamento/billing.','--next-step',r['next_step'],'--source',r['evidence']],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
cpd=json.loads((ROOT/'data/agent-checkpoints.json').read_text());assert next(x for x in cpd['checkpoints']if x['id']=='meta-manual-payments-digital-trust')['source']==r['evidence']
event={'at':now,'agent':'zeus','event':'meta_manual_payments_scheduled_refresh_waiting_human','job_id':c['cron_job_id'],'scheduled_at':r['scheduled_at'],'status':'waiting_human','reason':r['reason'],'evidence':r['evidence'],'fresh_metrics':55,'fresh_h':0,'pending_d':len(api['pending_ui']),'payments':0,'billing_changes':0,'report_infra_status':r['report_infra_status']}
with(ROOT/'logs/events-audit.jsonl').open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert json.loads(last)==event
save(B/'closure-state-readback.json',{'status':'blocked_receipt_contract_inventory_checkpoint_audit_readback_pass','evidence':r['evidence'],'lease_free':True,'no_manual_message_sent':True,'report_infra_status':r['report_infra_status']});print(json.dumps({'status':'waiting_human_recorded_validated','fresh_metrics':55,'fresh_h':0,'pending_d':len(api['pending_ui']),'lease_free':True}))
