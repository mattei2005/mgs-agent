import os,sys,json,shutil,re,fcntl,subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R));from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';os.umask(0o077)
def load(p):return json.loads(p.read_text())
def save(p,d):
 with p.open('x')as f:json.dump(d,f,ensure_ascii=False,indent=2)
def atomic(p,d):
 tmp=p.with_suffix('.partial-next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p);assert load(p)==d

def log(n):return[json.loads(l)for l in(B/(n+'.log')).read_text().splitlines()if l.startswith('{')][-1]
def mapping(sh):
 out={}
 for block in sh.get('data',[]):
  for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)):
   cells=row.get('values',[])
   if cells and(m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):assert m[1]not in out;out[m[1]]=(ri,cells)
 return out
c=load(H/'digital-trust-workbook-contract.json');baseline=load(B/'contract-before.json');j=next(x for x in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if x['id']==c['cron_job_id']);assert j['last_dispatch']['scheduled_at']=='2026-11-27T21:02:00-05:00'and j['fire_claim']['by']==load(B/'job-before.json')['fire_claim']['by'];assert c['account_ids']==baseline['account_ids']and c['pay_now_account_ids']==baseline['pay_now_account_ids'];assert c['sheet_id']==794137639 and not c['balance_views']['enabled']
api=log('api');ad=Path(api['run_dir']);plan=load(ad/'plan.json');hd=Path(log('h_prepare')['run_dir']);v=load(hd/'visual-verification.json');hl=load(H/'pc1-pay-now-ledger.json');inv=load(Path(log('invoices')['run_dir'])/'invoice-collection.json');pending_h=sorted(set(c['pay_now_account_ids'])-set(v['verified_account_ids']));assert len(v['verified_account_ids'])==32 and len(pending_h)==3
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);g.load_env();token=g.service_account_access_token();st,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert st==200;save(B/'partial-full-workbook-readback.json',after)
 before=load(B/'workbook-before.json');aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};sid=c['sheet_id'];assert set(aa)==set(bb);assert all(aa[k]==bb[k]for k in aa if k!=sid),'other_sheet_changed';assert all(aa[k]['properties']==bb[k]['properties']for k in aa)
 am=mapping(aa[sid]);bm=mapping(bb[sid]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id']for p in plan['planned']}
 for p in plan['planned']:
  aid=p['id'];ri,cs=am[aid];ori,old=bm[aid];assert ri==ori
  assert cs[0]==old[0]and cs[1]==old[1]and cs[3]==old[3]
  assert cs[2]['userEnteredValue']=={'stringValue':p['default']}
  for col,key in[(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(cs[col]['userEnteredValue']['numberValue']))==Decimal(p[key])and plan['collected_at']in cs[col]['note']
  if aid in v['verified_account_ids']:
   h=hl['accounts'][aid];r=load(hd/(aid+'-receipt.json'));check=v['accounts_list_checks'][aid];assert check['row_account_id']==aid and check['business_id']==c['business_id']and check['name']==p['name']and check['balance_label']=='Outstanding balance'
   assert Decimal(str(cs[7]['userEnteredValue']['numberValue']))==Decimal(h['amount'])==Decimal(r['amount'])==Decimal(check['balance_usd']);assert h['read_at']==r['read_at']and h['read_at']in cs[7]['note']and h['source']in cs[7]['note']and h['source']==c['h_source'];assert Path(h['receipt']).resolve()==(hd/(aid+'-receipt.json')).resolve()
  else:assert cs[7]==old[7]
  iv=inv['by_account'].get(aid)
  if iv:
   expected=iv['invoice']if Decimal(iv['due'])>0 and iv['status']!='Paid'else None;assert cs[4].get('userEnteredValue',{}).get('stringValue')==expected;assert Decimal(str(cs[5]['userEnteredValue']['numberValue']))==Decimal(iv['due'])
  else:assert not cs[4].get('userEnteredValue');assert cs[5].get('userEnteredValue',{})==({'numberValue':0}if p['method']=='Linha de crédito'else{})
 lease=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked'];struct=log('structural-validation');assert struct['status']=='snapshot_readback_pass'
 receipt={'status':'blocked_meta_passkey','business_refresh_complete':False,'execution_mode':'scheduled','scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'partial-financial-validation.json'),'accounts':len(c['account_ids']),'fresh_metrics_count':len(plan['planned']),'api_run_dir':str(ad),'api_collected_at':plan['collected_at'],'invoice_run_dir':log('invoices')['run_dir'],'invoice_period':inv['invoice_period'],'invoice_pending':inv['unpaid_in_current_tab'],'invoice_due_usd':inv['tab_total_usd'],'fresh_h_count':len(v['verified_account_ids']),'h_run_dir':str(hd),'verified_h_account_ids':v['verified_account_ids'],'pending_h_account_ids':pending_h,'h_source':c['h_source'],'pending_ui':api['pending_ui'],'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'h_ledger_to_live_sheet_exact':True,'older_h_and_all_d_preserved':True,'other_sheet_data_unchanged':True,'other_sheets_count':len(aa)-1,'structural_validation':struct,'lease_free':True,'auth_evidence':str(B/'surface-auth/surface.png'),'surface_failure_recovery':'Accounts technical error -> one Reload page -> actual Meta passkey gate; no bypass or further input','payments_executed':0,'billing_changes':0,'meta_writes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_due_to_cron_no_manual_delivery','delivery':'cron_auto_final_only'}
 save(B/'partial-financial-validation.json',receipt);save(B/'contract-pre-partial-closure.json',c);c['previous_refresh_qualification']=c.get('latest_refresh_qualification');c['latest_refresh_qualification']=receipt;c['general_refresh_blocker']={'status':'waiting_human','reason':'facebook_passkey_reauthentication_required','evidence':receipt['auth_evidence'],'pending_h_account_ids':pending_h,'pending_d_account_ids':[p['account_id']for p in api['pending_ui']],'same_job_id':c['cron_job_id'],'completed_layers':['funding','invoices','api_metrics','H32_published_readback'],'next_step':'Authenticate Meta in Rodolfo Chrome PC1; resume only remaining H and pending D after exact surface validation; reconcile new API events.'};c['pending_card_history']={'status':'blocked_meta_passkey','account_ids':[p['account_id']for p in api['pending_ui']],'pending_ui':api['pending_ui'],'evidence':receipt['evidence'],'prior_evidence':c.get('pending_card_history',{}).get('evidence')};atomic(H/'digital-trust-workbook-contract.json',c)
ident='meta-manual-payments-cron-20261127T2102';now=receipt['verified_at']
with(ROOT/'data/.meta-manual-inventory.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=ROOT/'data/infra-inventory.json';inventory=load(p);save(B/'inventory-pre-partial-closure.json',inventory);rows=inventory.setdefault('runtime_artifacts',[]);assert not any(isinstance(x,dict)and x.get('id')==ident for x in rows);entry={'id':ident,'agent':'zeus','type':'scheduled_financial_refresh','status':receipt['status'],'scheduled_at':receipt['scheduled_at'],'updated_at':now,'evidence':receipt['evidence'],'verification':{'fresh_metrics':52,'fresh_h':32,'pending_h':pending_h,'pending_d':[x['account_id']for x in api['pending_ui']],'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0},'report_infra_status':receipt['report_infra_status']};rows.append(entry);atomic(p,inventory)
state='Refresh27nov21:02ET parcial:52 métricas API e invoices outubro publicadas;32/35 H pixels+AX+ledger publicados;3H anteriores preservados e2D novos pendentes. Accounts falhou tecnicamente; um Reload abriu gate Meta/passkey real confirmado em pixels.3abas alheias intactas;lease livre;nenhum pagamento/billing.'
nextstep='Aguardar autenticação Meta no mesmo Chrome PC1; preservar mesmo job/cadência e escopo52. Reconciliar esta ocorrência antes de retomada; somente3H faltantes e2D novos, depois API final/validação. REPORT-INFRA pendente por proibição de envio manual no tick.'
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id',c['thread_id'],'--objective','Atualização recorrente autorizada das contas ativas;aguardando autenticação humana','--state',state,'--next-step',nextstep,'--source',receipt['evidence']],capture_output=True,text=True);assert r.returncode==0,r.stderr
assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust')['source']==receipt['evidence']
event={'at':now,'agent':'zeus','event':'meta_manual_payments_scheduled_refresh_auth_blocked','job_id':c['cron_job_id'],'scheduled_at':receipt['scheduled_at'],'evidence':receipt['evidence'],'fresh_metrics':52,'fresh_h':32,'pending_h':pending_h,'pending_ui':api['pending_ui'],'other_sheet_data_unchanged':True,'payments':0,'billing_changes':0,'report_infra_status':receipt['report_infra_status']}
with(ROOT/'logs/events-audit.jsonl').open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert json.loads(last)==event
save(B/'report-infra-pending.json',{'status':receipt['report_infra_status'],'destination':'1498132022634483894','helper':'/root/mgs-agent/scripts/send-report-infra-embed.sh','evidence':receipt['evidence'],'reason':state,'no_manual_message_sent':True})
save(B/'closure-state-readback.json',{'status':'partial_contract_inventory_checkpoint_audit_readback_pass','evidence':receipt['evidence'],'fresh_metrics':52,'fresh_h':32,'pending_h':len(pending_h),'pending_d':len(api['pending_ui']),'auth_gate_visually_confirmed':True,'other_sheets_exact':True,'report_infra_status':receipt['report_infra_status']});print(json.dumps(load(B/'closure-state-readback.json')))
