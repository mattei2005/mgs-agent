"""Seal the same authorized recovery; never mutate its supervisor queue owner."""
import sys, os, json, re, shutil, subprocess, fcntl
from pathlib import Path
from datetime import datetime
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_finance_continuity import resume, observation
from mgs_alert_transport import request
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent;H=ROOT/'data/meta-manual-payments';KEY='6a8f887c7ddb0077beeeb05b'
def load(p):return json.loads(p.read_text())
def save(p,d):
    t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2));t.chmod(0o600);os.replace(t,p);assert load(p)==d
job=next(j for j in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs'] if j['id']=='2ee720363d7d')
assert job['enabled'] and not job['fire_claim'] and job['schedule']['expr']=='2 8,14,21 * * *' and job['next_run_at']=='2026-11-09T14:02:00-05:00'
delivery=resume(job,verify_only=True,key=KEY);assert delivery['verified']
independent=observation(job);assert independent and independent['message_id']==delivery['message_id']
cl=load(B/'recovery-financial-validation.json');assert cl['pending_ui']==[] and cl['fresh_h_count']==36
cl.update(status='completed_validated',delivery_verified=True,financial_delivery_message_id=delivery['message_id'],financial_delivery_receipt=delivery['receipt'],independent_observation_verified=True,completed_at=datetime.now().astimezone().isoformat(),groups={'Cartão de crédito':11,'Linha de crédito':36},report_infra_status='pending',continuity_state='awaiting_supervisor_independent_closure',scheduled_at='2026-11-09T08:02:00-05:00')
cl['run_dir']=cl['metrics_run_dir'];cl['historical_d_verified_values']=12;cl['h_preserved_count']=0
cl['fresh_h_account_ids']=sorted(cl['h_read_times']);cl['pending_h_account_ids']=[]
cl['cron_coordination']={'job_id':job['id'],'schedule_unchanged':True,'next_run_at':job['next_run_at'],'fire_claim':None}
cl['ui_cleanup']={'owned_tabs_closed':True,'lease_free':True,'evidence':'Both canonical billing-history collectors returned success and closed only their own tabs/released lease in finally; lease status readback unlocked. No exact new browser-tab-count parity claimed.'}
ID='meta-manual-payments-refresh-20261109-0802'
def persist():
    save(B/'recovery-financial-validation.json',cl)
    original=B/'closure-0802-before-recovery.json'
    if not original.exists():shutil.copy2(B/'closure-current.json',original)
    save(B/'closure-current.json',cl)
    with (H/'writer.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert len(c['account_ids'])==47 and c['account_ids']==load(B/'contract-before.json')['account_ids']
        c['latest_refresh_qualification']=cl;c['pending_card_history']={'status':'new_events_resolved_historical_gaps_qualified','account_ids':[],'pending_ui':[],'historical_blank_count':35,'evidence':str(B/'recovery-financial-validation.json'),'continuity_key':KEY};save(H/'digital-trust-workbook-contract.json',c)
    with (ROOT/'data/.meta-financial-inventory.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');items=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(items) if x.get('id')==ID];assert len(matches)==1
        items[matches[0]].update(status=cl['status'],updated_at=cl['completed_at'],evidence=str(B/'recovery-financial-validation.json'),report_infra_status=cl['report_infra_status'],financial_delivery_message_id=delivery['message_id'],verification={'accounts':47,'fresh_metrics':47,'fresh_h':36,'pending_d':0,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0},recovery_scripts=['scripts/mgs_finance_continuity.py','scripts/mgs_automation_supervisor.py'],tests='8 finance delivery tests PASS')
        save(ROOT/'data/infra-inventory.json',d)
persist()
state='Recuperacao mesma ocorrencia09nov08:02 validada:47IDs,11cartao36linha;H36/36USD545853.57 com horas originais;D2eventos resolvidos CPV14Visa3382USD900 e Escalatepower03Discover8397USD57,09nov. Pending_ui vazio apos API47 atualizadas10:42:48Eastern. 35lacunasDhistoricas qualificadas. E/F29invoicesoutubroUSD417702.93;externaUSD161.18 fora dos totais. Fontes/notas/linksUSD/totaisFGHIJ/outraaba PASS. Entrega canonicalGET '+delivery['message_id']+'. Lease livre;0pagamento/MetaWrite/billing/cronchange.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step','Supervisor confirmar independentemente e fechar mesma fila '+KEY+'. Nao recoletar/republicar dados validados. Mesmo job proximo09nov14:02Eastern;historicoD35lacunas explicitas.','--source',str(B/'recovery-financial-validation.json')],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok'
assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints'] if x.get('id')=='meta-manual-payments-digital-trust')['source']==str(B/'recovery-financial-validation.json')
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','script/data/skill','--path','scripts/mgs_finance_continuity.py; scripts/mgs_automation_supervisor.py; tests/test_finance_continuity_delivery.py; data/meta-manual-payments/pc1-card-ledger.json; data/meta-manual-payments/digital-trust-workbook-contract.json; meta-manual-payments-planning/references/recurring-refresh.md','--reason','Recovery mesma ocorrencia09nov08:02;reconciliacaoHpreservada,D2eventosresolvidos;adaptercanonicalagoraseparaocorrencias/snapshots/noncessemreplay;nenhumjob/cadencia/billingalterado.','--evidence','47IDs fonte→Sheets e outra aba PASS;H36/36USD545853.57;D2provas pixels+ledger+readback;APIpending_ui vazio10:42;35lacunasD qualificadas.8testsPASS;entreganathreadoriginalGET '+delivery['message_id']+';verificadorindependentePASS;leasefree.0pagamento/MetaWrite/billing/cronchange.Recibo '+str(B/'recovery-financial-validation.json')]
r=subprocess.run(args,capture_output=True,text=True,timeout=90);save(B/'recovery-infra-report-result.json',{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
mid=re.search(r'message_id=(\d+)',r.stdout)[1];msg=request('GET','https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid)
assert msg['id']==mid and msg['channel_id']=='1498132022634483894' and not msg['content'] and not msg['mentions'] and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);persist()
e={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_same_occurrence_recovered_validated','operation_key':KEY,'job_id':job['id'],'source_thread':'1563926766286803004','receipt':str(B/'recovery-financial-validation.json'),'fresh_h':36,'accounts':47,'pending_ui':[],'historical_d_gaps':35,'financial_delivery_message_id':delivery['message_id'],'report_infra_message_id':mid,'payments':0,'meta_writes':0,'billing_changes':0,'cron_changes':0}
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
assert any(json.loads(x)==e for x in (ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-30:])
print(json.dumps({'status':cl['status'],'financial_delivery_message_id':delivery['message_id'],'independent_observation_verified':True,'report_infra_message_id':mid,'report_infra_readback':True,'contract_checkpoint_inventory_audit_readback':True,'queue_owner_preserved':True,'receipt':str(B/'recovery-financial-validation.json')},ensure_ascii=False))
