"""Seal verified scheduled refresh, preserving contract scope and scheduler."""
import json,os,subprocess,fcntl,re,urllib.request,runpy
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-20261104-2102'
def read(p):return json.loads(p.read_text())
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p);assert read(p)==d
cl=read(B/'closure-current.json');assert cl['status']=='updated_validated' and cl['accounts']==47 and cl['fresh_h_count']==36 and not cl['pending_ui'] and cl['other_sheet_data_unchanged']
cl['report_infra_status']='pending';cl['cron_changes']=0;cl['billing_changes']=0
job=[j for j in read(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs'] if j['id']=='2ee720363d7d'][0];assert job['schedule']['expr']=='2 8,14,21 * * *' and job['enabled'] and job['timezone']=='America/New_York'
cl['cron_coordination']={'job_id':job['id'],'same_scheduled_execution':True,'schedule_unchanged':True,'next_run_at':job['next_run_at']}
with (H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);c=read(C);assert c['account_ids']==read(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pay_now_last_publication_report']=cl['pay_now_run_dir'];c['pending_card_history']={'status':'no_new_events_pending_historical_gaps_preserved','account_ids':[],'pending_ui':[],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',f"04nov21:32EST validado47API11cartao36linha,H36/36pixels21:07–21:25,D3provasrenovadas0eventospendentes35lacunas historicas;saldoUSD{cl['totals_usd']['balance']},media{cl['totals_usd']['average_daily']},gastonov{cl['totals_usd']['month_spend']};29invoices417702.93;outraabaintacta leasefree.",'--next-step','Manter mesmo job e contrato na proxima execucao; nenhuma recuperacao pendente. Preservar35lacunasDhistoricas (34semprova,1semcobrancalocalizada). Nao repetir este writer nem presumir prova futura.','--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok';print('checkpoint_saved_readback',flush=True)
entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','verification':{'accounts':47,'fresh_metrics':47,'fresh_h':36,'preserved_h':0,'card_proofs_updated':3,'pending_d':0,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0}}
def inventory(e):
 with (ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=read(I);arr=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(arr)if x.get('id')==ID];assert len(matches)<=1
  if matches:arr[matches[0]]=e
  else:arr.append(e)
  save(I,d);assert len([x for x in read(I)['runtime_artifacts']if x.get('id')==ID])==1
inventory(entry)
# Governance report only; the human financial result is delivered by cron itself.
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data/financial-recurring-refresh','--path',str(C)+'; '+str(B/'closure-current.json'),'--reason','Tick autorizado04nov21:02Eastern do mesmo job,mesmos47IDs;sem alteracao de cron/billing.','--evidence',f"47API,11cartao36linha;H36/36pixelsUSD{cl['h_sum_usd']};3provasDrenovadas,0novoseventospendentes,35lacunas historicas;29invoicesoutubroUSD417702.93;CGIJ/EF/D/H+notasreadbackexatos;F/G/H/I/JDecimalPASS;outraabaintacta;leasefree;0pagamentos/MetaWrites."]
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0
m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1]
x=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));x['load_env'](x['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
assert msg['id']==mid and msg['channel_id']=='1498132022634483894' and not msg['content'] and not msg['mentions'] and msg['embeds'] and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);save(B/'closure-current.json',cl)
c=read(C);assert c['latest_refresh_qualification']['closure_receipt']==str(B/'closure-current.json');c['latest_refresh_qualification']=cl;save(C,c)
entry.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);inventory(entry)
with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps({'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_validated','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':str(B/'closure-current.json'),'accounts':47,'fresh_h':36,'historical_d_gaps':35,'pending_ui':[],'card_proofs_updated':3,'other_sheet_data_unchanged':True,'payments':0,'meta_writes':0,'cron_changes':0,'report_infra_message_id':mid,'report_infra_readback':True},ensure_ascii=False)+'\n')
print(json.dumps({'status':'sealed','contract_readback':True,'inventory_readback':True,'report_infra_message_id':mid,'report_infra_readback':True,'next_run_at':job['next_run_at']},ensure_ascii=False))
