import os,json,fcntl,subprocess,sys,hashlib,shutil
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent.resolve();H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
cl=load(B/'closure-current.json');assert cl['fresh_metrics_count']==47 and cl['fresh_h_count']==36 and cl['other_sheet_data_unchanged']
assert [x['account_id']for x in cl['pending_ui']]==['1290644206529750'] and cl['card_proofs_updated']==9
block={'status':'waiting_human','kind':'meta_billing_surface_redirect_and_search_input_unconfirmed','owner':'zeus','account_id':'1290644206529750','name':'OpenzedFinanzas-ES-CC-ES-02','read_at':datetime.now().astimezone().isoformat(),'cause_confirmed':'Legacy details and Accounts routes redirected to new Business Suite list. Exact authorized business_id retained; different context asset_id. Search stayed blank despite fresh-bounds background and foreground attempts. Authentication gate not observed.','cause_unproven':'Internal provider routing/focus mechanism and access to this individual account not established.','ui_attempts_stopped_after':5,'new_authentication_required_not_proven':True,'next_step':'Owner opens Billing/payment activity for exact OpenzedFinanzas-ES-CC-ES-02 ID1290644206529750 in existing Rodolfo Chrome. Zeus validates that surface, resumes only D and final API reconciliation; no new payment, billing or scope.','evidence':str(B/'closure-current.json'),'resume_via_existing_job':'2ee720363d7d','next_existing_run_at':cl['next_existing_run_at']}
cl['blocker']=block;cl['operational_learning']={'skill':'meta-manual-payments-planning','references':['references/accounts-list-search.md','references/recurring-refresh.md'],'summary':'New Billing Suite redirect is not logout; blank search is unconfirmed input; optional inline AX capture persisted without elements_file.'};save(B/'closure-current.json',cl)
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['month_since']=='2026-11-01'and c['month_until']=='2026-11-30'and c['payments_authorized']is False
 if not(B/'contract-before-seal.json').exists():save(B/'contract-before-seal.json',c)
 c['latest_refresh_qualification']=cl;c['pending_card_history']={'status':'one_new_event_pending_ui_surface_handoff','account_ids':['1290644206529750'],'pending_ui':cl['pending_ui'],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json')};c['general_refresh_blocker']=block;c['next_run_at']=cl['next_existing_run_at'];save(H/'digital-trust-workbook-contract.json',c)
# Synchronize only the two exact skill references authored by this task.
base=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning');mirror=ROOT/'profiles/zeus-skills/ops/meta-manual-payments-planning';hashes={}
for rel in cl['operational_learning']['references']:
 src=base/rel;dst=mirror/rel
 if src.read_bytes()!=dst.read_bytes():
  shutil.copy2(dst,B/('mirror-before-'+Path(rel).name));shutil.copy2(src,dst)
 assert src.read_bytes()==dst.read_bytes();hashes[rel]=hashlib.sha256(src.read_bytes()).hexdigest()
save(B/'learning-readback.json',{'skill':'meta-manual-payments-planning','mirrors_exact':True,'sha256':hashes})
ID='meta-manual-payments-refresh-manual-1570280845757915227'
with (ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(items)if isinstance(x,dict)and x.get('id')==ID];assert len(matches)<=1
 entry={'agent':'zeus','id':ID,'evidence':str(B/'closure-current.json'),'status':cl['status'],'type':'authorized_financial_refresh_after_human_auth','updated_at':cl['verified_at'],'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':36,'pending_d':1,'historical_blank_d':35,'card_proofs_updated':9,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0},'learning_readback':str(B/'learning-readback.json')}
 if matches:items[matches[0]]=entry
 else:items.append(entry)
 save(ROOT/'data/infra-inventory.json',d)
state=f"Manual1570280845757915227 parcial validado:47IDs11cartao36linha;metricas{cl['validated_metrics_at']};saldoUSD{cl['totals_usd']['balance']};novembroUSD{cl['totals_usd']['month_spend']}dia parcial;mediaUSD{cl['totals_usd']['average_daily']}08–10nov37contas/09–11nov10contas(fusos).H36/36Accounts22:40–23:00EasternUSD{cl['h_sum_usd']};9Drenovadas,1eventoD1290644206529750pendente.PC1online,autenticacaoMeta confirmada;bloqueioagoraUIlegacyredirecionanovaSuiteeSearchpermanecevazio,semgateAuth;5tentativasfalhas,inputsinterrompidos.35lacunasDhistoricasqualificadas.29invoicesoutubroUSD{cl['invoice_due_usd']},externaUSD161.18excluida.IDs/links/notas/moedas/totais/outraabaPASS;6abasoriginaispreservadas,lease livre;zero pagamento/billing/MetaWrite/cronchange.REPORT-INFRApendente."
nextstep=block['next_step']+' Same existing next tick '+cl['next_existing_run_at']+'; no new job. Do not claim old offline/2FA blocker remains. Pending D never authorizes extra billing actions.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',str(B/'closure-current.json')],capture_output=True,text=True);assert r.returncode==0 and json.loads(r.stdout)['status']=='ok'
cp=next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust');assert cp['source']==str(B/'closure-current.json')and cp['state'].casefold()==state.casefold()
line={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_manual_refresh_partial_validated','source_message_id':'1570280845757915227','source_thread':'1563926766286803004','accounts':47,'fresh_h':36,'pending_ui':cl['pending_ui'],'historical_d_blank_count':35,'card_proofs_updated':9,'receipt':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'learning_readback':str(B/'learning-readback.json'),'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'owner':'zeus'}
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==line
save(B/'seal-receipt.json',{'status':'partial_validated_sealed_one_ui_handoff','contract_checkpoint_inventory_audit_readback':True,'report_infra_status':cl['report_infra_status'],'receipt':str(B/'closure-current.json'),'next_existing_run_at':cl['next_existing_run_at'],'no_new_job':True,'learning_mirrors_exact':True})
print(json.dumps(load(B/'seal-receipt.json'),ensure_ascii=False))
