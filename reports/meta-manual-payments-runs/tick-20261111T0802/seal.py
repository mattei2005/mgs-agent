import os,json,fcntl,subprocess,sys
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent.resolve();H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
cl=load(B/'closure-current.json');assert cl['status']=='partial_validated_pc1_offline' and cl['fresh_metrics_count']==47 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and cl['other_sheet_data_unchanged']
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['month_since']=='2026-11-01'and c['month_until']=='2026-11-30'and c['payments_authorized']is False
 if not(B/'contract-before-seal.json').exists():save(B/'contract-before-seal.json',c)
 c['latest_refresh_qualification']=cl
 c['pending_card_history']={'status':'waiting_pc1_connectivity_previous_2fa_not_revalidated','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json')}
 c['next_run_at']=cl['next_existing_run_at']
 c['general_refresh_blocker']={'status':'waiting_human','kind':'pc1_private_network_offline','read_at':cl['verified_at'],'pending_stages':['accounts_list_H_36','new_card_history_events_10','final_API_reconciliation'],'evidence':str(B/'closure-current.json'),'owner':'zeus','no_bypass':True,'previous_2fa_gate_not_cleared':True}
 save(H/'digital-trust-workbook-contract.json',c)
ID='meta-manual-payments-refresh-tick-20261111T0802'
with (ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(items)if isinstance(x,dict)and x.get('id')==ID];assert len(matches)<=1
 entry={'agent':'zeus','id':ID,'evidence':str(B/'closure-current.json'),'status':cl['status'],'type':'authorized_scheduled_financial_refresh','updated_at':cl['verified_at'],'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':0,'preserved_h':36,'pending_d':len(cl['pending_ui']),'historical_blank_d':cl['historical_d_blank_count'],'card_proofs_updated':0,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0}}
 if matches:items[matches[0]]=entry
 else:items.append(entry)
 save(ROOT/'data/infra-inventory.json',d)
state=f"Tick 2026-11-11 08:02 Eastern PARCIAL validado:47IDs(11cartao36linha),funding/invoices/C/G/I/J publicados;metricas {cl['validated_metrics_at']};saldo USD{cl['totals_usd']['balance']};J novembro USD{cl['totals_usd']['month_spend']},1-11nov dia parcial;G USD{cl['totals_usd']['average_daily']},8-10nov completos por fuso. PC1 Online=false no Tailscale e SSH timeout repetido apos backoff;ultimo LastSeen2026-11-11T07:00:00.1Z. Nenhuma captura/input/aba aberta nesta rodada;autenticacao Meta atual nao inspecionada e gate2FA anterior nao declarado resolvido. H0/36frescos,36preservados com horas originais {cl['h_read_at_min']} a {cl['h_read_at_max']}.10eventos genericos aguardam instrumento;12D anteriores preservados,35D vazios historicos(34sem prova+Growpowerhub-US-SHEIN-EN-04-G004 sem cobranca localizada).29invoices outubro USD{cl['invoice_due_usd']};externaUSD161.18excluida. IDs/links/notas/moedas/formulas/totais/outrasabasPASS;lease livre;zero pagamento/MetaWrite/billing/cronchange. REPORT-INFRA pendente por entrega exclusiva do cron."
nextstep=f"Zeus mantem pedido aberto. Restaurar conectividade privada do PC1 e validar mesma janelaChrome/BM155263197283282;2FA anterior exige prova positiva do alvo antes de liberar. Sem credenciais/codigos em chat ou bypass. Mesmo job existente proximo tick {cl['next_existing_run_at']};nao criar outrojob/writer. Reconciliar dispatch/writes/recibos;retomar36H e10eventosD pendentes,reconciliarAPI final e validar sem repetir fases publicadas. Conectividade, autenticacao e recuperacao de H/D ainda nao comprovadas."
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',str(B/'closure-current.json')],capture_output=True,text=True);assert r.returncode==0 and json.loads(r.stdout)['status']=='ok'
cp=next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust');assert cp['source']==str(B/'closure-current.json')and cp['state'].casefold()==state.casefold()
line={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_scheduled_refresh_partial_pc1_offline','job_id':cl['job_id'],'execution_id':cl['execution_id'],'scheduled_at':cl['scheduled_at'],'source_thread':'1563926766286803004','accounts':47,'fresh_h':0,'preserved_h':36,'pending_ui':cl['pending_ui'],'historical_d_blank_count':cl['historical_d_blank_count'],'card_proofs_updated':0,'receipt':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'owner':'zeus','state':'waiting_pc1_connectivity'}
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==line
save(B/'seal-receipt.json',{'status':'partial_sealed_pc1_offline','contract_checkpoint_inventory_audit_readback':True,'report_infra_status':cl['report_infra_status'],'receipt':str(B/'closure-current.json'),'next_existing_run_at':cl['next_existing_run_at'],'no_new_job':True,'unresolved_h':36,'unresolved_new_d_events':len(cl['pending_ui']),'owner':'zeus'})
print(json.dumps(load(B/'seal-receipt.json'),ensure_ascii=False))
