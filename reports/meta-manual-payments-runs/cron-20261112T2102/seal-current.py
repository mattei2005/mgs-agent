import os,json,fcntl,subprocess,sys
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent.resolve();H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
cl=load(B/'closure-current.json');assert cl['fresh_metrics_count']==47 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and cl['other_sheet_data_unchanged']
assert len(cl['pending_ui'])==7 and cl['card_proofs_updated']==0
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['month_since']=='2026-11-01'and c['month_until']=='2026-11-30'and c['payments_authorized']is False
 assert not(B/'contract-before-seal.json').exists();save(B/'contract-before-seal.json',c)
 previous={x['account_id']for x in c['latest_refresh_qualification']['pending_ui']};cl['new_pending_d_account_ids']=sorted({x['account_id']for x in cl['pending_ui']}-previous);cl['prior_pending_d_count']=len(previous)
 save(B/'closure-current.json',cl)
 c['latest_refresh_qualification']=cl;c['pending_card_history']={'status':'events_pending_ui_route','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json')};c['general_refresh_blocker']=cl['blocker'];c['next_run_at']=cl['next_existing_run_at'];save(H/'digital-trust-workbook-contract.json',c)
ID='meta-manual-payments-refresh-cron-20261112T2102'
with (ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);assert not any(isinstance(x,dict)and x.get('id')==ID for x in items)
 entry={'agent':'zeus','id':ID,'evidence':str(B/'closure-current.json'),'status':cl['status'],'type':'scheduled_financial_refresh','updated_at':cl['verified_at'],'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':0,'preserved_h':36,'pending_d':len(cl['pending_ui']),'historical_blank_d':cl['historical_d_blank_count'],'card_proofs_updated':0,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0}}
 items.append(entry);save(ROOT/'data/infra-inventory.json',d)
state=f"Cron12nov21:02 parcial validado:47IDs; grupos={cl['groups']};metricas={cl['validated_metrics_at']};saldoUSD{cl['totals_usd']['balance']};novembroUSD{cl['totals_usd']['month_spend']}dia parcial;mediaUSD{cl['totals_usd']['average_daily']};periodosmedia={cl['average_period']};H0/36novas,36preservadasde{cl['h_read_at_min']}a{cl['h_read_at_max']};{len(cl['pending_ui'])}eventosDpendentes,{len(cl['new_pending_d_account_ids'])}novosdesde14:02;{cl['historical_d_blank_count']}lacunasDhistoricasqualificadas.UI atual conferida em pixels:Outstandingbalance,naoCurrentbalance.Semgateauth/nativo;nenhuminput/reload/perfilalternativo,naorepetircollectorlegadoouinventarequivalencia.RotahistoricaDnaoretestadaporbloqueioproviderconhecido.{cl['visible_invoice_numbers']}invoicesoutubroUSD{cl['invoice_due_usd']};externaUSD161.18excluida.IDs/links/notas/moedas/totais/outraabaPASS;lease livre;zero pagamento/billing/MetaWrite/cronchange.REPORT-INFRApendente:cronproibeenviomanual."
nextstep=cl['blocker']['next_step']+' Existing next tick '+cl['next_existing_run_at']+'; no new job. Provider redesign is not authentication failure. Validate metric semantics before H; keep missing historical D explicit and never classify generic events as card.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',str(B/'closure-current.json')],capture_output=True,text=True);assert r.returncode==0 and json.loads(r.stdout)['status']=='ok'
cp=next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust');assert cp['source']==str(B/'closure-current.json')and cp['state'].casefold()==state.casefold()
line={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_cron_refresh_partial_validated','scheduled_at':cl['scheduled_at'],'execution_id':cl['execution_id'],'source_thread':'1563926766286803004','accounts':47,'fresh_h':0,'preserved_h':36,'pending_ui':cl['pending_ui'],'new_pending_d_account_ids':cl['new_pending_d_account_ids'],'historical_d_blank_count':cl['historical_d_blank_count'],'card_proofs_updated':0,'receipt':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'owner':'zeus'}
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==line
save(B/'report-infra-pending.json',{'status':'pending','reason':'Scheduled run explicitly forbids direct send; final report delivered by native job.','subsystem':'meta-manual-payments-digital-trust','scope':'same47IDs;API47fresh;H36preserved;D7pending;no payments/billing','evidence':str(B/'closure-current.json'),'no_send_performed':True})
assert load(H/'digital-trust-workbook-contract.json')['latest_refresh_qualification']==load(B/'closure-current.json')
assert sum(1 for x in load(ROOT/'data/infra-inventory.json')['runtime_artifacts']if isinstance(x,dict)and x.get('id')==ID)==1
save(B/'seal-receipt.json',{'status':'partial_validated_sealed_provider_ui_blocker','contract_checkpoint_inventory_audit_readback':True,'report_infra_status':cl['report_infra_status'],'receipt':str(B/'closure-current.json'),'next_existing_run_at':cl['next_existing_run_at'],'no_new_job':True})
print(json.dumps(load(B/'seal-receipt.json'),ensure_ascii=False))
