import sys,json,subprocess,os,tempfile,re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
BASE=Path('/root/mgs-agent');RUN=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'scripts'))
from mgs_finance_continuity import read_workbook,authored
from mgs_automation_continuity import native_contract_hash
load=lambda p:json.loads(Path(p).read_text())
def save(p,d):
 fd,n=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
 with os.fdopen(fd,'w')as f:json.dump(d,f,ensure_ascii=False,indent=2)
 os.chmod(n,0o600);os.replace(n,p)
def rows(s):
 out={}
 for g in s.get('data',[]):
  for r in g.get('rowData',[]):
   cs=r.get('values',[]);m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))if cs else None
   if m:assert m[1]not in out;out[m[1]]=cs
 return out
def val(c):return next(iter(c.get('userEnteredValue',{}).values()),'')
c=load(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json');p=load(RUN/'progress.json');api=json.loads(p['completed']['api']['stdout']);invphase=json.loads(p['completed']['invoices']['stdout']);hp=json.loads(p['completed']['h_prepare']['stdout']);hdir=Path(hp['run_dir']);gate=load(RUN/'h-batch1.log');assert gate['status']=='blocked'and gate['completed']==0 and gate['reason']=='provider_or_auth_gate'
plan=load(Path(api['run_dir'])/'plan.json');inv=load(Path(invphase['run_dir'])/'invoice-collection.json');assert inv==load(BASE/'data/meta-manual-payments/september-invoice-ledger.json')
book=read_workbook(c);save(RUN/'partial-workbook-readback.json',book);old={s['properties']['sheetId']:s for s in load(RUN/'workbook-before.json')['sheets']};new={s['properties']['sheetId']:s for s in book['sheets']};assert set(old)==set(new)
other=all(authored(old[k])==authored(new[k])for k in old if k!=c['sheet_id']);assert other
ar=rows(new[c['sheet_id']]);br=rows(old[c['sheet_id']]);assert set(ar)==set(br)==set(c['account_ids'])=={x['id']for x in plan['planned']}
for x in plan['planned']:
 cs=ar[x['id']];assert val(cs[0])==x['name']and val(cs[1])==x['method']and val(cs[2])==x['default']
 for i,k in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(val(cs[i])))==Decimal(x[k])and plan['collected_at']in cs[i]['note']
 iv=inv['by_account'].get(x['id'])
 if iv:assert Decimal(str(val(cs[5])))==Decimal(iv['due']);assert str(val(cs[4]))==(iv['invoice']if Decimal(iv['due'])>0 and iv['status']!='Paid'else'')
 else:assert val(cs[4])==''and val(cs[5])in('',0)
 for col in (3,7):assert cs[col].get('userEnteredValue',{})==br[x['id']][col].get('userEnteredValue',{})and cs[col].get('note')==br[x['id']][col].get('note'),'D_H_preservation_failed'
lease=load('/root/mgs-agent/data/meta-manual-payments/pc1-computer-use-lock.json')if False else json.loads(subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert lease['ok']and not lease['locked']
j=next(x for x in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs']if x['id']==c['cron_job_id']);jb=load(RUN/'job-before.json');assert native_contract_hash(j)==native_contract_hash(jb)and j['fire_claim']['by']==jb['fire_claim']['by']and j['last_dispatch']==jb['last_dispatch']
now=datetime.now().astimezone().isoformat();pending=api['pending_ui'];r={'status':'blocked_meta_authentication','business_refresh_complete':False,'run_kind':'scheduled_tick','scheduled_at':jb['last_dispatch']['scheduled_at'],'job_id':j['id'],'fire_claim':jb['fire_claim'],'verified_at':now,'accounts':len(ar),'fresh_metrics_count':len(ar),'api_collected_at':plan['collected_at'],'api_run_dir':api['run_dir'],'invoice_run_dir':invphase['run_dir'],'h_run_dir':str(hdir),'fresh_h_count':0,'preserved_h_count':len(c['pay_now_account_ids']),'h_source':'accounts_list_outstanding_balance','pending_ui':pending,'historical_d_preserved':True,'h_values_notes_original_times_preserved':True,'source_to_live_sheet_cgij_exact':True,'invoice_source_to_live_sheet_ef_exact':True,'other_sheet_data_unchanged':other,'structural_validation':load(RUN/'structural-validation.log'),'gate':{'kind':'meta_authenticator_app_2fa_reauthentication','correct_chrome_pid':22596,'correct_window_id':131572,'profile_rodolfo_ax':True,'business_id':c['business_id'],'screenshot':gate['screenshot'],'visually_verified':True,'message':'Confirm it’s you with your authenticator app; Enter the 6-digit code','no_bypass_or_auth_input':True},'lease_free':True,'payments_executed':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'next_run_at':j['next_run_at'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','delivery':'automatic_final_only_exact_auth_message','evidence':str(RUN/'blocked-receipt.json'),'run_dir':str(RUN)};save(RUN/'blocked-receipt.json',r)
save(RUN/'qualification-before.json',c['latest_refresh_qualification']);c['previous_refresh_qualification']=c['latest_refresh_qualification'];c['latest_refresh_qualification']=r;c['pending_card_history']={'status':'blocked_meta_authentication','account_ids':[x['account_id']for x in pending],'pending_ui':pending,'evidence':r['evidence']};c['next_run_at']=j['next_run_at'];save(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json',c)
id='meta-manual-payments-scheduled-20261117T0802';ip=BASE/'data/infra-inventory.json';inventory=load(ip);assert not any(x.get('id')==id for x in inventory['runtime_artifacts']);inventory['runtime_artifacts'].append({'id':id,'agent':'zeus','type':'scheduled_financial_refresh','status':r['status'],'updated_at':now,'source_thread_id':c['thread_id'],'evidence':r['evidence'],'verification':{'accounts':55,'fresh_metrics':55,'fresh_h':0,'preserved_h':40,'pending_d_events':len(pending),'other_sheet_data_unchanged':other,'lease_free':True,'payments':0,'billing_changes':0},'report_infra_status':r['report_infra_status']});save(ip,inventory)
state='Bloqueio Meta 2FA confirmado em pixels no mesmo Chrome Rodolfo/PC1 e BM autorizada. API55 e invoices outubro atualizados e reconciliados por ID;H40 preservados com horários históricos;'+str(len(pending))+' pendênciasD atuais preservadas. Outra aba intacta e lease livre. Nenhum pagamento/billing;nenhum bypass. Recibo '+r['evidence']
q=subprocess.run([sys.executable,str(BASE/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id',c['thread_id'],'--objective','Refresh financeiro recorrente55IDs/H40 de17/11 08:02Eastern,mesmojob e contrato.','--state',state,'--next-step','Rodolfo autentica Meta no Chrome PC1;depois conferir ownership e superfície e retomar o mesmo pedido,sem writer/job paralelo. Preservar backup e writes independentes. Recorrência existente inalterada;gate humano bloqueia UI. REPORT-INFRA administrativo pendente por restrição explícita de envio.','--source',r['evidence']],capture_output=True,text=True,check=True);save(RUN/'checkpoint-result.json',json.loads(q.stdout))
with (BASE/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps({'at':now,'agent':'zeus','event':'meta_manual_payments_scheduled_blocked_authentication','job_id':j['id'],'scheduled_at':r['scheduled_at'],'receipt':r['evidence'],'accounts':55,'fresh_h':0,'preserved_h':40,'pending_d_events':len(pending),'payments':0,'billing_changes':0,'cron_changes':0,'report_infra_status':r['report_infra_status']},ensure_ascii=False)+'\n')
assert load(BASE/'data/meta-manual-payments/digital-trust-workbook-contract.json')['latest_refresh_qualification']['evidence']==r['evidence'];assert sum(x.get('id')==id for x in load(ip)['runtime_artifacts'])==1
ck=next(x for x in load(BASE/'data/agent-checkpoints.json')['checkpoints']if x['id']=='meta-manual-payments-digital-trust');assert ck['source']==r['evidence']
p.update(status=r['status'],blocked_receipt=r['evidence'],human_authentication_required=True,business_refresh_complete=False);save(RUN/'progress.json',p)
print(json.dumps({'status':'blocked_receipt_recorded_and_readback','fresh_metrics':55,'fresh_h':0,'preserved_h':40,'pending_d_events':len(pending),'other_sheet_unchanged':other,'lease_free':True,'checkpoint_current':True,'inventory_unique':True,'no_direct_delivery':True}))
