import sys,json,os,subprocess,time
from pathlib import Path
from datetime import datetime
B=Path(__file__).resolve().parent;sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_automation_continuity import Queue,native_contract_hash
load=lambda p:json.loads(Path(p).read_text())
c=load('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json');j=next(x for x in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs']if x['id']==c['cron_job_id']);r=load(B/'partial-receipt.json')
assert j['last_dispatch']['scheduled_at']==r['scheduled_at']and j['fire_claim']['by']==r['fire_claim']['by']
q=Queue();prior={x['key']:x['state']for x in q.open()if json.loads(x['source']).get('job_id')==j['id']}
source={'kind':'native','profile':'zeus','job_id':j['id'],'thread_id':c['thread_id'],'resource':'pc1','session_id':os.environ['HERMES_SESSION_ID'],'contract_hash':native_contract_hash(j),'scheduled_at':r['scheduled_at'],'run_dir':str(B),'financial_receipt':r['evidence'],'pending_cause':'pc1_offline_transport_timeout','pending_account_ids_D':[x['account_id']for x in r['pending_ui']],'pending_account_ids_H':c['pay_now_account_ids'],'completed_layers':['funding','invoices','metrics','source_to_sheet_readback'],'pending_layers':['H40_Accounts_outstanding_balance','D7_new_generic_events_instrument','final_API_reconciliation_and_validation'],'resume_policy':'Same scheduled occurrence, same contract/job and Chrome. Reconcile native fire claim, writer and prior continuity owner before writing. Resume only H/D missing layers with canonical workers, then API final and full readback. Never repeat funding/invoices or create cron/writer. PC1 offline confirmed, not authentication. Preserve earlier occurrences separately; later snapshot is not their completion. Current short result is automatic delivery only; REPORT-INFRA pending separately.','time_sensitive':False}
keysource='native:zeus:'+j['id']+':20261118T0802';existing=next((x for x in q.open()if x['source_key']==keysource),None)
row=q.enqueue(keysource,source,'pc1_offline_transport_timeout')
if existing is None:q.defer(row['key'],'retry_scheduled','pc1_offline_transport_timeout',delay=600,observation='Pendente: PC1 offline na rede privada; SSH22 timeout. API55/E-F verificados; H40 e sete eventosD aguardam mesmo Chrome. Não é autenticação comprovada. Não repetir etapas já publicadas.')
row=q.get(row['key']);assert row and row['state']=='retry_scheduled'and not row['owner']
services={k:json.loads(v)for k,v in q.db.execute('select key,value from service')};hb=services['heartbeat'];assert services['enabled']is True and time.time()-hb['at']<1200
try:os.kill(hb['pid'],0);consumer_alive=True
except ProcessLookupError:consumer_alive=False
summaries=[json.loads(line)for line in Path('/root/mgs-agent/logs/alerts-infra-failed-alert-resolver.log').read_text().splitlines()[-30:]if line.startswith('{')and 'supervisor_tick_complete'in line]
assert consumer_alive or(hb['phase']=='idle'and summaries),'consumer_not_proven'
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout;line=next(l for l in cron.splitlines()if not l.startswith('#')and'alerts-infra-failed-alert-resolver.py'in l)
assert all(q.get(k)['state']==v for k,v in prior.items()if v=='blocked_decision')
result={'key':row['key'],'source_key':row['source_key'],'state':row['state'],'due_epoch':row['due'],'retry_at':datetime.fromtimestamp(row['due']).astimezone().isoformat(),'source':json.loads(row['source']),'consumer_enabled':True,'consumer_heartbeat':hb,'consumer_process_alive':consumer_alive,'consumer_last_tick_completed':bool(summaries),'consumer_cron':line,'consumer_entrypoint':'mgs_automation_supervisor.py -> run_worker -> build_prompt preserves original native contract and occurrence','old_historical_gate_preserved':True,'no_new_job':True}
(B/'continuity-readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('source','consumer_cron')}))
