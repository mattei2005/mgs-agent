import json,os,fcntl,subprocess
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments'
r=json.loads((B/'financial-validation.json').read_text());assert r['status']=='completed_validated'and r['business_refresh_complete']and r['pending_ui']==[]and r['fresh_h_count']==40 and r['fresh_metrics_count']==55
now=datetime.now().astimezone().isoformat()
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p)
def backup(p,label):
 q=B/label;assert not q.exists();q.write_bytes(p.read_bytes());q.chmod(0o600)
with(H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 p=H/'digital-trust-workbook-contract.json';c=json.loads(p.read_text());original=json.loads((B/'contract-before.json').read_text())
 for key in ['account_ids','pay_now_account_ids','business_id','spreadsheet_id','sheet_id','month_since','month_until','cron_job_id','cron_expression','h_source','payments_authorized']:assert c[key]==original[key],key
 backup(p,'contract-pre-closure.json');c['latest_refresh_qualification']=r
 old=c.get('pending_card_history',{});c['pending_card_history']={'status':'resolved_current_event_pending_ui_empty','account_ids':[],'pending_ui':[],'resolved_account_ids':r['renewed_d_ids'],'evidence':r['evidence'],'verified_at':r['verified_at'],'historical_blank_count':len(r['historical_blank_d']),'history_gaps_are_not_zero':True,'prior_evidence':old.get('evidence'),'next_step':'Existing next scheduled tick; revalidate actual surface and collect new events only. Historical D blanks remain qualified, not recent pending events.'}
 c['pay_now_last_publication_report']=r['h_run_dir'];c['general_refresh_blocker']=None
 save(p,c);assert json.loads(p.read_text())==c
# Inventory operational receipt, not a new operational policy or cron.
p=ROOT/'data/infra-inventory.json'
with (ROOT/'data/.meta-manual-inventory.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 inventory=json.loads(p.read_text());backup(p,'inventory-pre-closure.json');entries=inventory.setdefault('runtime_artifacts',[]);assert isinstance(entries,list)
 ident='meta-manual-payments-manual-1574520802391363625';assert not any(e.get('id')==ident for e in entries if isinstance(e,dict))
 entry={'id':ident,'agent':'zeus','type':'authorized_manual_financial_refresh_existing_UIA','status':r['status'],'source_message_id':r['source_message_id'],'updated_at':now,'evidence':r['evidence'],'report_infra_status':'pending','verification':{'accounts':55,'fresh_metrics':55,'fresh_h':40,'renewed_d':r['renewed_d_count'],'pending_ui':0,'historical_blank_d':len(r['historical_blank_d']),'source_parity_cgij_ef_h_d':True,'other_sheet_data_unchanged':r['other_sheet_data_unchanged'],'outside_write_masks_preserved':r['outside_write_masks_preserved'],'browser_tabs_preserved':True,'browser_original_tabs':r['browser_tabs_original_count'],'lease_free':r['lease_free'],'cron_changes':0,'meta_writes':0,'payments':0,'billing_changes':0}}
 entries.append(entry);save(p,inventory);read=json.loads(p.read_text());matches=[e for e in read['runtime_artifacts']if e.get('id')==ident];assert matches==[entry]
cp=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Refresh integral manual23nov autorizado1574520802391363625 das mesmas55contas e40H;mesmo workbook/job','--state','completed_validated: API55 final15:56ET,H40 pixels+ledger, D5provas renovadas,pending_ui vazio;invoicesoutubro30USD417864.11;39Dhistoricosvaziosqualificados;outraaba e6abasChrome preservadas;0pagamentos/billing.','--next-step','Mesmo job proximo23nov21:02ET; nova coleta contratada e somente eventosDnovos. Concluir REPORT-INFRA manual e entrega na origem,sem outro writer/job.','--source',r['evidence']],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
checkpoints=json.loads((ROOT/'data/agent-checkpoints.json').read_text());cp_matches=[e for e in checkpoints['checkpoints']if e.get('id')=='meta-manual-payments-digital-trust'];assert len(cp_matches)==1 and cp_matches[0]['source']==r['evidence']
event={'at':now,'agent':'zeus','event':'meta_manual_payments_authorized_manual_refresh_completed','job_id':original['cron_job_id'],'source_message_id':r['source_message_id'],'source_thread_id':'1563926766286803004','status':r['status'],'evidence':r['evidence'],'accounts':55,'fresh_h':40,'renewed_d':r['renewed_d_count'],'historical_blank_d':len(r['historical_blank_d']),'pending_ui':[],'other_sheet_data_unchanged':True,'lease_free':True,'payments':0,'billing_changes':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending'}
p=ROOT/'logs/events-audit.jsonl'
with p.open('a+')as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());f.seek(0);last=None
 for line in f:
  if line.strip():last=line
 assert json.loads(last)==event
save(B/'closure-state-readback.json',{'status':'contract_inventory_checkpoint_audit_readback_pass','evidence':r['evidence'],'inventory_id':ident,'report_infra_status':entry['report_infra_status'],'payment_actions':0,'cron_changes':0,'closed_at':now})
print(json.dumps({'status':'contract_inventory_checkpoint_audit_readback_pass','accounts':55,'H':40,'D_renewed':r['renewed_d_count'],'pending_ui':0,'report_infra':'pending_report'}))
