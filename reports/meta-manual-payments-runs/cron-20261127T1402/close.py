import json,os,fcntl,subprocess
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments'
def load(p):return json.loads(p.read_text())
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p)
def backup(p,name):
 q=B/name;assert not q.exists();q.write_bytes(p.read_bytes());q.chmod(0o600)
r=load(B/'financial-validation.json');c=load(H/'digital-trust-workbook-contract.json');original=load(B/'contract-before.json');j=next(x for x in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if x['id']==c['cron_job_id'])
assert r['status']=='completed_validated' and r['business_refresh_complete'] and not r['pending_ui']
assert r['fresh_h_count']==len(c['pay_now_account_ids']) and r['fresh_metrics_count']==len(c['account_ids'])
assert r['other_sheet_data_unchanged'] and r['browser_tabs_preserved'] and r['lease_free']
assert j['fire_claim']['by']==r['fire_claim_by'] and j['last_dispatch']['scheduled_at']==r['scheduled_at']
now=datetime.now().astimezone().isoformat()
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for k in ['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','month_since','month_until','cron_job_id','cron_expression','h_source','payments_authorized','recurring_scope']:assert c[k]==original[k],k
 p=H/'digital-trust-workbook-contract.json';assert load(p)==c;backup(p,'contract-pre-closure.json');c['previous_refresh_qualification']=c.get('latest_refresh_qualification');c['latest_refresh_qualification']=r
 old=c.get('pending_card_history',{});c['pending_card_history']={'status':'resolved_current_event_pending_ui_empty','account_ids':[],'pending_ui':[],'resolved_account_ids':[],'evidence':r['evidence'],'verified_at':r['verified_at'],'historical_blank_count':len(r['historical_blank_d']),'history_gaps_are_not_zero':True,'prior_evidence':old.get('evidence'),'next_step':'Existing next scheduled tick; revalidate actual surface and collect only new D events. Historical D blanks and original proof timestamps remain qualified; no automatic archive reactivation.'}
 c['pay_now_last_publication_report']=r['h_run_dir'];c['general_refresh_blocker']=None
 save(p,c);assert load(p)==c
ident='meta-manual-payments-cron-20261127T1402'
with(ROOT/'data/.meta-manual-inventory.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=ROOT/'data/infra-inventory.json';inv=load(p);backup(p,'inventory-pre-closure.json');entries=inv.setdefault('runtime_artifacts',[]);assert not any(isinstance(x,dict)and x.get('id')==ident for x in entries)
 entry={'id':ident,'agent':'zeus','type':'scheduled_financial_refresh','status':r['status'],'scheduled_at':r['scheduled_at'],'updated_at':now,'evidence':r['evidence'],'report_infra_status':'pending_due_to_cron_no_manual_delivery','verification':{'active_accounts':r['accounts'],'fresh_metrics':r['fresh_metrics_count'],'fresh_h':r['fresh_h_count'],'new_d_events':r['current_d_event_count'],'renewed_d':r['renewed_d_count'],'historical_blank_d':len(r['historical_blank_d']),'source_parity_cgij_ef_h_d':True,'other_sheet_data_unchanged':True,'outside_write_masks_preserved':True,'browser_tabs_preserved':True,'lease_free':True,'cron_changes':0,'meta_writes':0,'payments':0,'billing_changes':0},'recovery':'Initial Accounts synthetic search no-op recovered by existing scoped UIA ValuePattern collector; all35 H actual screenshots read, exact source and individual timestamps retained.'}
 entries.append(entry);save(p,inv);assert [x for x in load(p)['runtime_artifacts']if isinstance(x,dict)and x.get('id')==ident]==[entry]
state=f"Refresh agendado27nov14:02ET concluído: {r['accounts']} métricas API finais, {r['fresh_h_count']}H Outstanding balance pixels+AX+ledger; nenhum evento D novo pendente; {len(r['historical_blank_d'])}D históricos vazios qualificados e provas anteriores datadas preservadas; invoices outubro30USD417864.11;3abas alheias completas e6abasChrome preservadas;0pagamento/billing."
nextstep='Mesmo job próximo27nov21:02ET; nova coleta contratada, somente eventos D novos. Sem reativar146arquivadas. REPORT-INFRA pendente por proibição de envio manual nesta ocorrência; evidência financial-validation.json. Resultado operacional somente pelo final automático do cron.'
p=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id',c['thread_id'],'--objective','Refresh agendado somente contas ativas Contas com saldo, mesmo job/cadência','--state',state,'--next-step',nextstep,'--source',r['evidence']],capture_output=True,text=True);assert p.returncode==0,p.stderr
assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust')['source']==r['evidence']
event={'at':now,'agent':'zeus','event':'meta_manual_payments_scheduled_refresh_completed','job_id':c['cron_job_id'],'scheduled_at':r['scheduled_at'],'evidence':r['evidence'],'accounts':r['accounts'],'fresh_h':r['fresh_h_count'],'new_d_events':0,'pending_ui':[],'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'report_infra_status':entry['report_infra_status']}
p=ROOT/'logs/events-audit.jsonl'
with p.open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert last is not None
 assert json.loads(last)==event
save(B/'report-infra-pending.json',{'status':'pending_due_to_cron_no_manual_delivery','helper':'/root/mgs-agent/scripts/send-report-infra-embed.sh','destination':'1498132022634483894','action':'modificada','type':'data operacional','paths':['data/meta-manual-payments/digital-trust-workbook-contract.json','data/meta-manual-payments/pc1-pay-now-ledger.json','data/meta-manual-payments/last-refresh.json','data/infra-inventory.json','data/agent-checkpoints.json'],'reason':state,'evidence':r['evidence'],'no_manual_message_sent':True})
save(B/'closure-state-readback.json',{'status':'contract_inventory_checkpoint_audit_readback_pass','evidence':r['evidence'],'inventory_id':ident,'report_infra_status':entry['report_infra_status'],'payment_actions':0,'cron_changes':0,'closed_at':now,'no_manual_message_sent':True})
print(json.dumps({'status':'contract_inventory_checkpoint_audit_readback_pass','accounts':r['accounts'],'H':r['fresh_h_count'],'new_D_events':0,'historical_D_blanks':len(r['historical_blank_d']),'report_infra':entry['report_infra_status'],'cron_changes':0}))
