import os,sys,json,shutil,re,fcntl,subprocess
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timedelta,date
os.umask(0o077)
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';B=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'));import mgs_google_workspace_auth as g
sys.path.insert(0,'/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts');from refresh_workbook import zone

def load(p):return json.loads(p.read_text())
def save(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def atomic(p,d):
 tmp=p.with_suffix('.closure-next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p);assert load(p)==d
def log(n):return [json.loads(x) for x in (B/(n+'.log')).read_text().splitlines() if x.startswith('{')][-1]
def mapping(sh):
 out={}
 for b in sh.get('data',[]):
  for ri,row in enumerate(b.get('rowData',[]),b.get('startRow',0)):
   cs=row.get('values',[])
   if cs and (m:=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))):
    assert m[1] not in out;out[m[1]]=(ri,cs)
 return out
c=load(H/'digital-trust-workbook-contract.json');bc=load(B/'contract-before.json')
j=next(x for x in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs'] if x['id']==c['cron_job_id']);bj=load(B/'job-before.json')
assert j['last_dispatch']==bj['last_dispatch'] and j['fire_claim']['by']==bj['fire_claim']['by']
assert j['last_dispatch']['scheduled_at']=='2026-11-28T08:02:00-05:00'
assert j['enabled'] and j['schedule']==bj['schedule'] and j['timezone']==bj['timezone'] and datetime.fromisoformat(j['next_run_at'])>datetime.now().astimezone()
assert c['account_ids']==bc['account_ids'] and c['pay_now_account_ids']==bc['pay_now_account_ids'] and c['sheet_id']==794137639 and c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled']
a=log('api');ad=Path(a['run_dir']);plan=load(ad/'plan.json');inv=load(Path(log('invoices')['run_dir'])/'invoice-collection.json');hd=Path(log('h_prepare')['run_dir'])
assert {x['account_id'] for x in load(hd/'targets.json')}==set(c['pay_now_account_ids'])
assert load(H/'september-invoice-ledger.json')==inv
with (H/'writer.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);g.load_env();token=g.service_account_access_token()
 st,after=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert st==200;save(B/'partial-full-workbook-readback.json',after)
 before=load(B/'workbook-before.json');aa={s['properties']['sheetId']:s for s in after['sheets']};bb={s['properties']['sheetId']:s for s in before['sheets']};sid=c['sheet_id']
 assert set(aa)==set(bb) and all(aa[k]==bb[k] for k in aa if k!=sid),'other_sheet_changed'
 assert all(aa[k]['properties']==bb[k]['properties'] for k in aa)
 am=mapping(aa[sid]);bm=mapping(bb[sid]);assert set(am)==set(bm)==set(c['account_ids'])=={p['id'] for p in plan['planned']}
 for p in plan['planned']:
  aid=p['id'];ri,cs=am[aid];ori,old=bm[aid];assert ri==ori and cs[0]==old[0] and cs[1]==old[1] and cs[3]==old[3] and cs[7]==old[7]
  assert cs[2]['userEnteredValue']=={'stringValue':p['default']}
  for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(cs[col]['userEnteredValue']['numberValue']))==Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
  today=datetime.fromisoformat(plan['collected_at']).astimezone(zone(p['timezone'])).date()
  assert p['average_period']=={'since':str(today-timedelta(days=3)),'until':str(today-timedelta(days=1))}
  assert p['month_period']=={'since':c['month_since'],'until':str(min(today,date.fromisoformat(c['month_until'])))}
  iv=inv['by_account'].get(aid)
  if iv:
   expected=iv['invoice'] if Decimal(iv['due'])>0 and iv['status']!='Paid' else None
   assert cs[4].get('userEnteredValue',{}).get('stringValue')==expected and Decimal(str(cs[5]['userEnteredValue']['numberValue']))==Decimal(iv['due'])
  else:assert not cs[4].get('userEnteredValue') and cs[5].get('userEnteredValue',{})==({'numberValue':0} if p['method']=='Linha de crédito' else {})
lease=load(B/'surface.json')
ls=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not ls['locked']
struct=log('structural-validation');assert struct['status']=='snapshot_readback_pass'
receipt={'status':'blocked_meta_passkey','business_refresh_complete':False,'execution_mode':'scheduled','scheduled_at':j['last_dispatch']['scheduled_at'],'fire_claim_by':j['fire_claim']['by'],'verified_at':datetime.now().astimezone().isoformat(),'evidence':str(B/'partial-financial-validation.json'),'accounts':len(c['account_ids']),'fresh_metrics_count':len(plan['planned']),'api_run_dir':str(ad),'api_collected_at':plan['collected_at'],'invoice_run_dir':log('invoices')['run_dir'],'invoice_period':inv['invoice_period'],'invoice_pending':inv['unpaid_in_current_tab'],'invoice_due_usd':inv['tab_total_usd'],'fresh_h_count':0,'h_run_dir':str(hd),'pending_h_account_ids':c['pay_now_account_ids'],'pending_ui':a['pending_ui'],'source_parity_cgij':True,'invoice_source_to_live_sheet_exact':True,'all_h_and_d_preserved':True,'other_sheet_data_unchanged':True,'other_sheets_count':len(aa)-1,'structural_validation':struct,'lease_free':True,'auth_evidence':str(B/'surface.png'),'auth_verified_in_pixels':True,'auth_verified_in_ax':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_due_to_cron_no_manual_delivery','delivery':'cron_auto_final_only'}
save(B/'partial-financial-validation.json',receipt);save(B/'contract-pre-closure.json',c)
c['previous_refresh_qualification']=c.get('latest_refresh_qualification');c['latest_refresh_qualification']=receipt
c['general_refresh_blocker']={'status':'waiting_human','reason':'facebook_passkey_reauthentication_required','evidence':receipt['auth_evidence'],'pending_h_account_ids':c['pay_now_account_ids'],'pending_d_account_ids':[p['account_id'] for p in a['pending_ui']],'same_job_id':c['cron_job_id'],'completed_layers':['funding','invoices','api_metrics'],'next_step':'Authenticate Meta in same Rodolfo Chrome PC1; resume H and current D with original evidence times preserved, then API reconciliation and independent validation.'}
c['pending_card_history']={'status':'blocked_meta_passkey','account_ids':[p['account_id'] for p in a['pending_ui']],'pending_ui':a['pending_ui'],'evidence':receipt['evidence'],'prior_evidence':c.get('pending_card_history',{}).get('evidence')};atomic(H/'digital-trust-workbook-contract.json',c)
ident='meta-manual-payments-cron-20261128T0802'
with (ROOT/'data/.meta-manual-inventory.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=ROOT/'data/infra-inventory.json';inventory=load(p);save(B/'inventory-pre-closure.json',inventory);rows=inventory.setdefault('runtime_artifacts',[]);assert not any(isinstance(x,dict) and x.get('id')==ident for x in rows)
 rows.append({'id':ident,'agent':'zeus','type':'scheduled_financial_refresh','status':receipt['status'],'scheduled_at':receipt['scheduled_at'],'updated_at':receipt['verified_at'],'evidence':receipt['evidence'],'verification':{'fresh_metrics':len(plan['planned']),'fresh_h':0,'pending_h':len(c['pay_now_account_ids']),'pending_d':len(a['pending_ui']),'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0},'report_infra_status':receipt['report_infra_status']});atomic(p,inventory)
state=f"Refresh28nov08:02ET parcial: {len(plan['planned'])} métricas API e invoices outubro atualizadas; H/D preservados. Gate real Meta/passkey confirmado no mesmo Chrome Rodolfo em pixels+AX. {len(a['pending_ui'])} D atuais pendentes, {len(c['pay_now_account_ids'])} H sem leitura nova; três abas congeladas intactas;lease livre;nenhum pagamento/billing."
nxt='Aguardar autenticação humana da Meta no Chrome PC1; manter job/cadência/escopo; reconciliar recibos antes de retomar H/D e API final. REPORT-INFRA pendente por restrição de entrega manual neste tick.'
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id',c['thread_id'],'--objective','Atualização financeira recorrente ativa; bloqueio humano Meta/passkey','--state',state,'--next-step',nxt,'--source',receipt['evidence']],capture_output=True,text=True);assert r.returncode==0
assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints'] if x.get('id')=='meta-manual-payments-digital-trust')['source']==receipt['evidence']
event={'at':receipt['verified_at'],'agent':'zeus','event':'meta_manual_payments_scheduled_refresh_auth_blocked','job_id':c['cron_job_id'],'scheduled_at':receipt['scheduled_at'],'evidence':receipt['evidence'],'fresh_metrics':len(plan['planned']),'fresh_h':0,'pending_h':c['pay_now_account_ids'],'pending_ui':a['pending_ui'],'other_sheet_data_unchanged':True,'payments':0,'billing_changes':0,'report_infra_status':receipt['report_infra_status']}
with (ROOT/'logs/events-audit.jsonl').open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert json.loads(last)==event
save(B/'report-infra-pending.json',{'status':receipt['report_infra_status'],'destination':'1498132022634483894','helper':str(ROOT/'scripts/send-report-infra-embed.sh'),'evidence':receipt['evidence'],'reason':state,'no_manual_message_sent':True})
closure={'status':'partial_contract_inventory_checkpoint_audit_readback_pass','evidence':receipt['evidence'],'fresh_metrics':len(plan['planned']),'fresh_h':0,'pending_h':len(c['pay_now_account_ids']),'pending_d':len(a['pending_ui']),'auth_gate_visually_confirmed':True,'other_sheets_exact':True,'report_infra_status':receipt['report_infra_status']}
save(B/'closure-state-readback.json',closure);print(json.dumps(closure))
