import os,sys,json,subprocess,fcntl,re,runpy,urllib.request,shutil
from pathlib import Path
from datetime import datetime
launcher=shutil.which('hermes');assert launcher
R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-20261107-2102'
def load(p):return json.loads(p.read_text())
def save(p,x):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p);assert load(p)==x
cl=load(B/'closure-current.json');assert cl['accounts']==47 and cl['fresh_h_count']==18 and cl['h_preserved_count']==18 and len(cl['pending_ui'])==3 and cl['lease_free']
job=next(j for j in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if j['id']=='2ee720363d7d');assert job['enabled']and job['schedule']['expr']=='2 8,14,21 * * *'and job['timezone']=='America/New_York'and job['last_dispatch']['scheduled_at']=='2026-11-07T21:02:00-05:00'and job['fire_claim']
cl.update(report_infra_status='pending',cron_coordination={'job_id':job['id'],'same_existing_job':True,'schedule_unchanged':True,'next_run_at':job['next_run_at'],'current_fire_claim_reconciled':True})
entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','verification':{'accounts':47,'fresh_metrics':47,'fresh_h':18,'preserved_h':18,'pending_d':len(cl['pending_ui']),'historical_blank_d':cl['historical_d_blank_count'],'other_sheet_data_unchanged':cl['other_sheet_data_unchanged'],'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0}}
def persist():
 with(H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=load(C);assert c['account_ids']==load(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pay_now_last_publication_report']=cl['pay_now_run_dir'];c['pending_card_history']={'status':'new_generic_events_pending_pc1_reauthentication','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=load(I);a=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(a)if x.get('id')==ID];assert len(matches)<=1
  if matches:a[matches[0]]=entry
  else:a.append(entry)
  save(I,d);assert len([x for x in load(I)['runtime_artifacts']if x.get('id')==ID])==1
 save(B/'closure-current.json',cl)
persist()
state=f"Tick07nov21:02Eastern PARCIAL:47API(11cartao36linha)verificadas{cl['validated_metrics_at']};saldoUSD{cl['totals_usd']['balance']};JnovUSD{cl['totals_usd']['month_spend']},dia07ou08parcialporfuso;media3diascompletos04-06ou05-07novUSD{cl['totals_usd']['average_daily']}. E/F29invoicesoutubroUSD{cl['invoice_due_usd']};fora47Growpowerhub02USD161.18 separado. H18/36novas21:06-21:17Eastern,18preservadas14hcomhorasoriginais;gateMetaFacebook2FAautenticadorRodolfoMattei,semretry/bypass. D3eventosgenericosnovospendentesCPV13/Mavroa03/Mavroa04;35lacunasDhistoricas(34semprova+Growpowerhub04semcobrancalocalizada). Fullreadback47IDsfontes/notas/linksUSD+totaisFGHIJPASS;outraabaintacta;8abasantes/depois,leasefree;0pagamento/MetaWrite/billing/cronchange."
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step','Reautenticacao humana no ChromeRodolfoPC1 se necessaria;na retomada nova coleta integral47API+36H e pending_uiatual,semduplicarwriter/job. Proximo mesmojob08nov08:02Eastern;preservar18Hantigas e35lacunashistoricasD.','--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok';assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust')['source']==cl['closure_receipt']
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial_auth_gate','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':cl['closure_receipt'],'accounts':47,'fresh_h':18,'preserved_h':18,'pending_ui':cl['pending_ui'],'historical_d_gaps':35,'payments':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending'}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data operacional','--path',str(C)+'; '+str(B),'--reason','Tick autorizado07nov21:02Eastern;API47 atualizadas,H18/36novas e18preservadas por gateMeta2FA;mesmosIDs/job,sem billing.','--evidence',f"47IDs11cartao36linha. 29invoicesoutubroUSD{cl['invoice_due_usd']};externaUSD161.18separada. H18/36novasAccounts21:06-21:17Eastern;18comhoras14hpreservadas. D3eventosgenericosnovospendentesCPV13/Mavroa03/04;35lacunashistoricas(34semprova+1semcobrancalocalizada). SaldoUSD{cl['totals_usd']['balance']};JnovUSD{cl['totals_usd']['month_spend']};media3diascompletosporfusoUSD{cl['totals_usd']['average_daily']}. Readbackfontes/notas/linksUSD/FGHIJDecimalPASS;outraabaintacta;8abasantes/depois;leasefree.0pagamento/MetaWrite/billing/cronchanges;proximo08nov08:02Eastern."]
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr)
if r.returncode==0:
 m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1];x=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));x['load_env'](x['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
 assert msg['id']==mid and msg['channel_id']=='1498132022634483894'and not msg['content']and not msg['mentions']and msg['embeds']and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
 for obj in [cl,entry,event]:obj.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True)
else:cl['report_infra_status']='failed_pending';event['report_infra_status']='failed_pending'
persist();event['at']=datetime.now().astimezone().isoformat()
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
print(json.dumps({'status':cl['status'],'contract_readback':True,'checkpoint_readback':True,'inventory_readback':True,'audit_readback':True,'report_infra_status':cl['report_infra_status'],'next_run_at':job['next_run_at']},ensure_ascii=False))
