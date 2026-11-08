import os,sys,json,subprocess,fcntl,re,runpy,urllib.request,shutil,sqlite3
from pathlib import Path
from datetime import datetime
launcher=shutil.which('hermes');assert launcher
R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-20261108-1402'
def load(p):return json.loads(p.read_text())
def save(p,x):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p);assert load(p)==x
cl=load(B/'closure-current.json');assert cl['accounts']==47 and cl['fresh_metrics_count']==0 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and cl['lease_free']
job=next(j for j in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if j['id']=='2ee720363d7d');assert job['enabled']and job['schedule']['expr']=='2 8,14,21 * * *'and job['timezone']=='America/New_York'and job['last_dispatch']['scheduled_at']=='2026-11-08T14:02:00-05:00'and job['fire_claim']
conn=sqlite3.connect('/root/.hermes/profiles/zeus/cron/executions.db');active=conn.execute("select id,status,scheduled_instant from executions where job_id=? and status in ('claimed','running')",(job['id'],)).fetchall();assert len(active)==1 and active[0][2]=='2026-11-08T19:02:00+00:00'
cl['cron_coordination']={'job_id':job['id'],'same_existing_job':True,'schedule_unchanged':True,'next_run_at':job['next_run_at'],'current_fire_claim_reconciled':True,'single_active_execution':active[0][0]}
entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','verification':{'accounts':47,'fresh_metrics':0,'preserved_metrics':47,'fresh_invoices':47,'fresh_h':0,'preserved_h':36,'previous_pending_d':len(cl['pending_ui']),'pending_d_collection_current':False,'historical_blank_d':cl['historical_d_blank_count'],'other_sheet_data_unchanged':cl['other_sheet_data_unchanged'],'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0}}
def persist():
 with(H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=load(C);assert c['account_ids']==load(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pending_card_history']={'status':'previous_pending_preserved_current_api_collection_incomplete_pc1_2fa','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'pending_ui_freshness':cl['pending_ui_freshness'],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=load(I);a=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(a)if x.get('id')==ID];assert len(matches)<=1
  if matches:a[matches[0]]=entry
  else:a.append(entry)
  save(I,d);assert len([x for x in load(I)['runtime_artifacts']if x.get('id')==ID])==1
 save(B/'closure-current.json',cl)
persist()
state=f"Tick08nov14:02Eastern PARCIAL.47IDs preservados(11cartao36linha); funding live sem transicao. E/F29invoicesoutubroUSD{cl['invoice_due_usd']} atuais; externaGrowpowerhub02USD161.18 separada. C/G/I/J preservados47/47 no snapshot08nov08:07:31: Meta Insights Yolokfx-US-SHEIN-EN-01-G002 ID7840111366055613 diarioUSD14041.56 vs agregado14046.34,delta4.78 persistiu2releituras limitadas; causa interna provider nao comprovada; nenhuma escrita da coleta falha. H0/36novas:reautenticacaoFacebook2FAperfilRodolfoMattei na rotaBilling;36valores/horas07novpreservados. D5pendenciasda coleta08:07 preservadas,enumeracaoatualincompleta(nao afirmar lista atual completa);35vazioshistoricos34semprova+Growpowerhub04semcobrancalocalizada. Fullreadback47IDs links/notasUSDtotaisFGHIJPASS,outraabaintacta,8abasantes/depois,leasefree;0pagamento/billing/MetaWrite/cronchange."
nextstep='Mesmojob08nov21:02Eastern:retomar funding/invoices/API47;Insightsdeveconciliar com max2releituras limitadas,sem enfraquecer gate;coletar36H somente apos2FA humana PC1. Derivar pending_ui de nova coleta completa;preservar snapshots antigos sem falsificar frescor. Sem writer/job paralelo.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok';assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust')['source']==cl['closure_receipt']
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial_insights_and_auth_gate','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':cl['closure_receipt'],'accounts':47,'fresh_metrics':0,'fresh_h':0,'preserved_h':36,'insights_blocker':cl['insights_blocker'],'historical_d_gaps':35,'payments':0,'meta_writes':0,'cron_changes':0,'report_infra_status':'pending'}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data operacional','--path',str(C)+'; '+str(B),'--reason','Tick autorizado08nov14:02Eastern PARCIAL:invoices atuais;metricas preservadas por divergencia Insights;H preservado por2FA. Mesmojob/47IDs sem billing.','--evidence',f"47IDs11cartao36linha.29invoicesoutubroUSD{cl['invoice_due_usd']};externaUSD161.18separada. C/G/I/J47preservados08:07:31;Yolokfx01 ID7840111366055613 diario14041.56/agregado14046.34 delta4.78 persistente2releituras,0writesda fasefalha.H0/36novas,36comhoras07novpreservadas;gateMeta2FA.D5pendencias08:07preservadas,enumeracaoatualincompleta;35lacunashistoricas. Readback47IDsfontes/notas/linksUSD/FGHIJDecimalPASS;outraabaintacta;8abasantes/depois;leasefree.0pagamento/MetaWrite/billing/cronchanges;proximo08nov21:02Eastern."]
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
print(json.dumps({'status':cl['status'],'contract_readback':True,'checkpoint_readback':True,'inventory_readback':True,'audit_readback':True,'report_infra_status':cl['report_infra_status'],'report_infra_message_id':cl.get('report_infra_message_id'),'next_run_at':job['next_run_at']},ensure_ascii=False))
