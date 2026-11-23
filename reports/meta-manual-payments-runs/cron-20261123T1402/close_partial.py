import json,os,fcntl,subprocess
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments'
r=json.loads((B/'financial-validation.json').read_text());assert r['status']=='partial_provider_technical_error'and not r['business_refresh_complete']and r['fresh_h_count']==1 and r['fresh_metrics_count']==55 and len(r['pending_ui'])==3
now=datetime.now().astimezone().isoformat()
def save(p,d):
 q=p.with_suffix(p.suffix+'.next');q.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');q.chmod(0o600);os.replace(q,p)
def backup(p,n):
 q=B/n;assert not q.exists();q.write_bytes(p.read_bytes());q.chmod(0o600)
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);p=H/'digital-trust-workbook-contract.json';c=json.loads(p.read_text());original=json.loads((B/'contract-before.json').read_text())
 for k in['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','month_since','month_until','cron_job_id','cron_expression','h_source','payments_authorized']:assert c[k]==original[k]
 backup(p,'contract-pre-closure.json');c['latest_refresh_qualification']=r
 old=c.get('pending_card_history',{});c['pending_card_history']={'status':'pending_provider_technical_error','account_ids':[x['account_id']for x in r['pending_ui']],'pending_ui':r['pending_ui'],'resolved_account_ids':[],'evidence':r['evidence'],'verified_at':r['verified_at'],'historical_blank_count':len(r['historical_blank_d']),'history_gaps_are_not_zero':True,'prior_evidence':old.get('evidence'),'owner':'zeus','next_step':r['resume']}
 c['pay_now_last_publication_report']=r['h_run_dir'];c['general_refresh_blocker']='provider_technical_error_on_pc1_accounts_no_authentication_gate';save(p,c);assert json.loads(p.read_text())==c
p=ROOT/'data/infra-inventory.json'
with(ROOT/'data/.meta-manual-inventory.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);d=json.loads(p.read_text());backup(p,'inventory-pre-closure.json');entries=d.setdefault('runtime_artifacts',[]);ident='meta-manual-payments-cron-20261123T1402';assert not any(e.get('id')==ident for e in entries if isinstance(e,dict))
 entry={'id':ident,'agent':'zeus','type':'scheduled_financial_refresh_partial_provider_error','status':r['status'],'scheduled_at':r['scheduled_at'],'updated_at':now,'evidence':r['evidence'],'report_infra_status':'pending_cron_delivery_only_no_direct_send','verification':{'accounts':55,'fresh_metrics':55,'fresh_h':1,'preserved_h':39,'pending_ui':3,'other_sheet_data_unchanged':True,'outside_write_masks_preserved':True,'lease_free':True,'cron_changes':0,'meta_writes':0,'payments':0,'billing_changes':0}}
 entries.append(entry);save(p,d);assert [e for e in json.loads(p.read_text())['runtime_artifacts']if e.get('id')==ident]==[entry]
cmd=['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Refresh recorrente23nov14:02ET das mesmas55contas e40H; mesmo job/workbook','--state','Parcial validado: API55 e invoicesoutubro atualizadas; H1 novo e39 históricos preservados; D3eventos pendentes; Meta Accounts exibe erro técnico temporário confirmado em pixels, sem gate autenticação. Inputs interrompidos sem reload/bypass. Outras abas preservadas; lease livre;0pagamentos/billing.','--next-step','Zeus mantém pendência H39/D3. Mesmo job existente21:02ET, sem novo job/writer: revalidar superfície e reconciliar ledgers antes da retomada; não repetir prova já publicada. REPORT-INFRA pendente pela restrição de envio direto do cron.','--source',r['evidence']]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
checkpoints=json.loads((ROOT/'data/agent-checkpoints.json').read_text());matches=[x for x in checkpoints['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust'];assert len(matches)==1 and matches[0]['source']==r['evidence']
e={'at':now,'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial','job_id':original['cron_job_id'],'scheduled_at':r['scheduled_at'],'source_thread_id':'1563926766286803004','status':r['status'],'evidence':r['evidence'],'accounts':55,'fresh_h':1,'preserved_h':39,'pending_ui':r['pending_ui'],'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending_cron_delivery_only_no_direct_send'}
with(ROOT/'logs/events-audit.jsonl').open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(e,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert json.loads(last)==e
save(B/'closure-state-readback.json',{'status':'partial_contract_inventory_checkpoint_audit_readback_pass','evidence':r['evidence'],'inventory_id':ident,'report_infra_status':'pending_cron_delivery_only_no_direct_send','payment_actions':0,'cron_changes':0,'closed_at':now});print(json.dumps({'status':'partial_state_recorded_and_readback_pass','accounts':55,'fresh_h':1,'preserved_h':39,'pending_ui':3,'report_infra':'pending_delivery_restriction'}))
