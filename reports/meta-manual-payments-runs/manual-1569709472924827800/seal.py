import os,json,fcntl,subprocess,sys
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent.resolve();H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
cl=load(B/'closure-current.json');assert cl['fresh_metrics_count']==47 and cl['fresh_h_count']==36 and cl['other_sheet_data_unchanged'] and not cl['pending_ui']
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['month_since']=='2026-11-01'and c['month_until']=='2026-11-30'and c['payments_authorized']is False
 if not(B/'contract-before-seal.json').exists():save(B/'contract-before-seal.json',c)
 c['latest_refresh_qualification']=cl;c['pending_card_history']={'status':'no_new_events_pending_historical_gaps_qualified','account_ids':[],'pending_ui':[],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json')};c['next_run_at']=cl['next_existing_run_at'];save(H/'digital-trust-workbook-contract.json',c)
ID='meta-manual-payments-refresh-manual-1569709472924827800'
with (ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(items)if isinstance(x,dict)and x.get('id')==ID];assert len(matches)<=1
 entry={'agent':'zeus','id':ID,'evidence':str(B/'closure-current.json'),'status':cl['status'],'type':'authorized_financial_refresh_after_human_auth','updated_at':cl['verified_at'],'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':36,'pending_d':0,'historical_blank_d':35,'card_proofs_updated':6,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0}}
 if matches:items[matches[0]]=entry
 else:items.append(entry)
 save(ROOT/'data/infra-inventory.json',d)
state=f"Recuperacao manual1569709472924827800 integral validada:47IDs(11cartao36linha);metricas {cl['validated_metrics_at']};saldo USD{cl['totals_usd']['balance']};gasto novembro USD{cl['totals_usd']['month_spend']} inclui10novparcial;media7–9nov USD{cl['totals_usd']['average_daily']}.H36/36Accounts lidas08:49–09:08Eastern USD{cl['h_sum_usd']},horasindividuais preservadas.6provasDrenovadas(4iniciais+Eggbev03/OpenzedFinanzasES02 eventosdurantecoleta);pending_ui vazio.35lacunasDhistoricas qualificadas.29invoices outubro USD{cl['invoice_due_usd']},externaUSD161.18excluida.IDs/links/notas/moedas/totais/outrasabasPASS.6abasoriginais preservadas;lease livre;zero pagamentos/billing/MetaWrite/cronchange.REPORT-INFRA {cl['report_infra_status']}."
nextstep=f"Nenhuma acao humana.Continuar mesmo job2ee720363d7d em {cl['next_existing_run_at']},mesmas47contas eperiodosaprovados;35lacunasDhistoricas naosaozero nempendenciasnovas.Preservar tempos de provas anteriores.Nao duplicar writer/job."
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',str(B/'closure-current.json')],capture_output=True,text=True);assert r.returncode==0 and json.loads(r.stdout)['status']=='ok'
cp=next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust');assert cp['source']==str(B/'closure-current.json')and cp['state'].casefold()==state.casefold()
line={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_manual_refresh_validated','source_message_id':'1569709472924827800','source_thread':'1563926766286803004','accounts':47,'fresh_h':36,'pending_ui':[],'historical_d_blank_count':35,'card_proofs_updated':6,'receipt':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'owner':'zeus'}
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==line
save(B/'seal-receipt.json',{'status':'completed_sealed','contract_checkpoint_inventory_audit_readback':True,'report_infra_status':cl['report_infra_status'],'receipt':str(B/'closure-current.json'),'next_existing_run_at':cl['next_existing_run_at'],'no_new_job':True})
print(json.dumps(load(B/'seal-receipt.json'),ensure_ascii=False))
