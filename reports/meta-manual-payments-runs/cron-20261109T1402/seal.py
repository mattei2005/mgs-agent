import os,json,fcntl,subprocess,sys,copy
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent.resolve();H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
cl=load(B/'closure-current.json');assert cl['fresh_metrics_count']==47 and cl['fresh_h_count']==36 and not cl['pending_ui']and cl['other_sheet_data_unchanged']
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['month_since']=='2026-11-01'and c['month_until']=='2026-11-30'and c['payments_authorized']is False
 save(B/'contract-before-seal.json',c);c['latest_refresh_qualification']=cl;c['pending_card_history']={'status':'new_events_resolved_historical_gaps_qualified','account_ids':[],'pending_ui':[],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json')};save(H/'digital-trust-workbook-contract.json',c)
ID='meta-manual-payments-refresh-20261109-1402'
with (ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(items)if isinstance(x,dict)and x.get('id')==ID];assert len(matches)<=1
 entry={'agent':'zeus','id':ID,'evidence':str(B/'closure-current.json'),'status':cl['status'],'type':'authorized_recurring_financial_snapshot','updated_at':cl['verified_at'],'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':36,'pending_d':0,'historical_blank_d':35,'card_proofs_updated':2,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0}}
 if matches:items[matches[0]]=entry
 else:items.append(entry)
 save(ROOT/'data/infra-inventory.json',d)
state='09nov14:02 concluido/validado:47IDs(11cartao36linha);metricas14:36Eastern;H36/36 Accounts14:06–14:30USD549065.63;D2eventos Mavroa03USD930 e Mavroa04USD335 MasterCard2311 Paid09nov confirmados pixels,ledger,Sheets. APIpending_ui vazio;35lacunasDhistoricas explicitas.29invoicesoutubroUSD417702.93;externaGrowpowerhub02USD161.18 fora dos totais. Jnov01–09parcialUSD170434.31;media06–08novUSD19124.39;IUSD552033.37. IDs/links/notas/fontes/moeda/totaisFGHIJ/outraaba PASS;6abasantes/depois e lease livre;zero pagamento/billing/MetaWrite/cronchange. REPORT-INFRA pendente pela restricao de entrega do cron.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step','Mesmo job proximo09nov21:02Eastern;nao repetir writes deste snapshot.35lacunasDhistoricas qualificadas;nenhuma pendencia nova D/H. Entrega automatica do resultado por este cron;REPORT-INFRA registrado pendente,sem envio manual.','--source',str(B/'closure-current.json')],capture_output=True,text=True);assert r.returncode==0 and json.loads(r.stdout)['status']=='ok'
cp=next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust');assert cp['source']==str(B/'closure-current.json')and cp['state']==state.lower()or cp['source']==str(B/'closure-current.json')and cp['state']==state
line={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_validated','job_id':'2ee720363d7d','scheduled_at':'2026-11-09T14:02:00-05:00','source_thread':'1563926766286803004','accounts':47,'fresh_h':36,'pending_ui':[],'historical_d_blank_count':35,'card_proofs_updated':2,'receipt':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0,'recovery_note':'Search input lost focus once; diagnostic showed Accounts loaded with empty search and selected page text, no auth/provider gate.15s cooldown and retry only missing batch succeeded;no completed data replay.'}
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==line
print(json.dumps({'status':'sealed','contract_checkpoint_inventory_audit_readback':True,'report_infra_status':cl['report_infra_status'],'receipt':str(B/'closure-current.json'),'next_run_at':'2026-11-09T21:02:00-05:00'},ensure_ascii=False))
