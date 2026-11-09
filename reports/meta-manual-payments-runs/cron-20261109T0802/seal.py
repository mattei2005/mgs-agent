import sys,os,json,shutil,subprocess,fcntl,runpy,re,urllib.request
from pathlib import Path
from datetime import datetime
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
ROOT=Path('/root/mgs-agent');B=Path(__file__).parent;H=ROOT/'data/meta-manual-payments';sys.path.insert(0,str(ROOT/'scripts'))
from mgs_automation_continuity import Queue,native_contract_hash

def load(p):return json.loads(p.read_text())
def save(p,d):
 t=p.with_suffix(p.suffix+'.next');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p);assert load(p)==d
p='/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/validate_workbook_readonly.py'
code="import sys,runpy;from pathlib import Path;sys.path.insert(0,"+repr(str(R))+");from pm.environments import activate_dependencies;activate_dependencies(Path("+repr(str(R))+"));sys.argv="+repr([p,'--spreadsheet-id','1PrKBawAGgRxx1LPcjcf8U6QH4ZcJfJTn-niJ2SzCdyU','--sheet-id','271321738','--business-id','155263197283282'])+";runpy.run_path("+repr(p)+",run_name='__main__')"
r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=120,check=True);v=json.loads(r.stdout);assert v['status']=='snapshot_readback_pass';save(B/'structural-validation.json',v)
r=subprocess.run([sys.executable,str(B/'verify.py')],capture_output=True,text=True,timeout=120,check=True)
cl=load(B/'closure-current.json');assert cl['accounts']==47 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and len(cl['pending_ui'])==2 and cl['lease_free'] and cl['other_sheet_data_unchanged']
job=next(x for x in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if x['id']=='2ee720363d7d');assert job['enabled'] and job['schedule']['expr']=='2 8,14,21 * * *' and job['timezone']=='America/New_York' and job['last_dispatch']['scheduled_at']=='2026-11-09T08:02:00-05:00' and job['fire_claim']
cl['cron_coordination']={'job_id':job['id'],'same_existing_job':True,'schedule_unchanged':True,'next_run_at':job['next_run_at'],'current_fire_claim_reconciled':True}
cl['structural_validation']=str(B/'structural-validation.json');cl['report_infra_status']='pending';cl['delivery_owner']='Native existing cron automatic final response only; no financial report POST by worker'
q=Queue();src={'kind':'native','profile':'zeus','job_id':job['id'],'thread_id':'1563926766286803004','resource':'pc1','contract_hash':native_contract_hash(job),'scheduled_at':'2026-11-09T08:02:00-05:00','financial_receipt':str(B/'closure-current.json'),'same_47_account_contract':True,'completed_layers':['funding','invoices','metrics','source_to_sheet_readback'],'pending_layers':['36_accounts_balances_H','2_new_generic_events_instrument_D'],'authentication_target':'Digital Trust Billing & payments on approved Rodolfo Chrome PC1','time_sensitive':False}
rec=q.enqueue('native:zeus:2ee720363d7d',src,'facebook_twofactor_reauth')
assert rec['state']!='running','supervisor_already_has_owner_do_not_steal'
q.defer(rec['key'],'waiting_human','facebook_twofactor_reauth',delay=1800,observation='2FA exigida por Meta na rota Billing do Chrome Rodolfo PC1. Pixels blocked.png: Confirm it’s you with your authentication app. API47 e E/F validadas;H0/36 novas,36 antigas preservadas;D2 eventos genericos novos sem prova. Nao repetir writes concluidos ou contornar login. Retomar somente apos leitura positiva do mesmo alvo;47IDs/job originais. Recibo: '+str(B/'closure-current.json'))
assert q.get(rec['key'])['state']=='waiting_human';cl['continuity_key']=rec['key'];cl['continuity_state']='waiting_human';save(B/'continuity-readback.json',q.get(rec['key']))
ID='meta-manual-payments-refresh-20261109-0802'
def persist():
 with(H/'writer.lock').open('a')as f:
  fcntl.flock(f,fcntl.LOCK_EX);c=load(H/'digital-trust-workbook-contract.json');assert c['account_ids']==load(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pending_card_history']={'status':'new_generic_events_pending_pc1_reauthentication','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_count':cl['historical_d_blank_count'],'evidence':str(B/'closure-current.json'),'continuity_key':rec['key']};save(H/'digital-trust-workbook-contract.json',c)
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as f:
  fcntl.flock(f,fcntl.LOCK_EX);d=load(ROOT/'data/infra-inventory.json');a=d.setdefault('runtime_artifacts',[]);matches=[i for i,x in enumerate(a)if x.get('id')==ID];assert len(matches)<=1
  entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':str(B/'closure-current.json'),'report_infra_status':cl['report_infra_status'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':0,'preserved_h':36,'pending_d':2,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0},'continuity_key':rec['key']}
  if matches:a[matches[0]]=entry
  else:a.append(entry)
  save(ROOT/'data/infra-inventory.json',d)
 save(B/'closure-current.json',cl)
persist()
state='Tick09nov08:02Eastern PARCIAL:47API(11cartao36linha)verificadas08:04;saldoUSD546930.21;JnovUSD164047.87,01-09nov,dia09parcial;media06-08novUSD19113.57.E/F29invoicesoutubroUSD417702.93;externaGrowpowerhub02USD161.18separada.H0/36novas,36preservadascomhoras08nov23h50-09nov00h28;gateMeta2FAautenticadorRodolfoMattei na rotaBilling antes da primeira linha;semretry/bypass.D2eventosgenericospendentesCPV14/Escalatepower03;35lacunasDhistoricas(34semprova+Growpowerhub04semcobrancalocalizada).Readback47IDsfontes/notas/linksUSD/totaisFGHIJPASS;outraabaintacta;7tabsantes/depois;leasefree.0pagamento/MetaWrite/billing/cronchange.Filaexistentewaiting_human.'
nextstep='Dependencia humana:concluir 2FAFacebook na rotaBilling do ChromeRodolfoPC1. Supervisor existente deve verificar positivamente MESMO alvo antes de retry;preservar mesma fila e47IDs. Reconciliar recibos/escritas deste tick;sem writer/job paralelo. Proximo tick original09nov14:02Eastern. Nao reabrir detalhes/modais paraH;nao repetir coleta enquanto gate persistir.'
r=subprocess.run([sys.executable,str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',nextstep,'--source',str(B/'closure-current.json')],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok'
assert next(x for x in load(ROOT/'data/agent-checkpoints.json')['checkpoints']if x.get('id')=='meta-manual-payments-digital-trust')['source']==str(B/'closure-current.json')
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data operacional','--path',str(H/'digital-trust-workbook-contract.json')+'; '+str(B),'--reason','Tick autorizado09nov08:02Eastern:API47 atualizadas;H36historicas preservadas por desafioMeta2FA;mesmos47IDs/job;sem billing.','--evidence','Fonte→Sheets47IDs/notas/linksUSD/totaisFGHIJ PASS;11cartao36linha;G06-08novUSD19113.57/dia;J01-09novparcialUSD164047.87;IUSD546930.21;29invoicesoutubroUSD417702.93;externaUSD161.18separada.H0/36novas,36preservadas.D2eventospendentes(CPV14/Escalatepower03),35lacunashistoricas.2abasnoWorkbook;abaalheiaintacta;7tabsChromeantes/depois;leasefree.Filaexistente '+rec['key']+' waiting_human.0pagamento/MetaWrite/billing/cronchange.Proximo09nov14:02Eastern.']
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr)
if r.returncode==0:
 m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1];helpers=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));helpers['load_env'](helpers['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
 assert msg['id']==mid and msg['channel_id']=='1498132022634483894' and not msg['content'] and not msg['mentions'] and msg['embeds'] and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
 cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True)
else:cl['report_infra_status']='failed_pending'
persist()
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial_auth_gate','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':str(B/'closure-current.json'),'accounts':47,'fresh_h':0,'preserved_h':36,'pending_ui':cl['pending_ui'],'historical_d_gaps':35,'payments':0,'meta_writes':0,'cron_changes':0,'continuity_key':rec['key'],'report_infra_status':cl['report_infra_status']}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
assert load(H/'digital-trust-workbook-contract.json')['latest_refresh_qualification']==cl
print(json.dumps({'status':cl['status'],'contract_readback':True,'checkpoint_readback':True,'inventory_readback':True,'audit_readback':True,'continuity_state':q.get(rec['key'])['state'],'report_infra_status':cl['report_infra_status'],'next_run_at':job['next_run_at']},ensure_ascii=False))
