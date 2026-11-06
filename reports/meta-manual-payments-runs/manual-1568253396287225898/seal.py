"""Seal authorized manual refresh and tested, local Accounts-input repair."""
import json,os,subprocess,fcntl,re,urllib.request,runpy,hashlib,shutil
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-1568253396287225898'
def read(p):return json.loads(p.read_text())
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p);assert read(p)==d
cl=read(B/'closure-current.json');assert cl['accounts']==47 and cl['fresh_h_count']==36 and cl['h_preserved_count']==0 and cl['pending_ui']==[] and cl['card_proofs_updated']==8 and cl['other_sheet_data_unchanged']
job=[j for j in read(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if j['id']=='2ee720363d7d'][0]
assert job['schedule']['expr']=='2 8,14,21 * * *'and job['enabled']and job['timezone']=='America/New_York'and job['fire_claim']is None
assert datetime.fromisoformat(job['next_run_at'])>datetime.now().astimezone()
cl.update(report_infra_status='pending',cron_changes=0,billing_changes=0)
cl['cron_coordination']={'job_id':job['id'],'same_existing_job':True,'schedule_unchanged':True,'next_run_at':job['next_run_at']}
cleanup={'final_browser_tabs_visually_counted':6,'during_owned_collection_browser_tabs_visually_counted':7,'active_final_surface':'original unfiltered Meta Digital Trust Accounts','owned_tab_closed':True,'exact_initial_browser_tab_identity_parity_established':False,'reason':'initial screenshot and full AX cache expired; inline AX retained but truncated. TabItem count was site-internal navigation, not Chrome tabs. Recovered validation using final durable pixels, own-tab capture pixels, unchanged initial inline labels and finally-close worker receipts. No additional UI input or uncertain tab closure.','lease_free':True,'final_screenshot':str(B/'surface-final.png')}
save(B/'ui-cleanup.json',cleanup);cl['ui_cleanup']=cleanup
live=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning');mirror=ROOT/'profiles/zeus-skills/ops/meta-manual-payments-planning';changed=['scripts/read_pc1_accounts_list.py','references/accounts-list-search.md','references/recurring-refresh.md'];hashes={}
for rel in changed:
 lp=live/rel;mp=mirror/rel
 if lp.read_bytes()!=mp.read_bytes():
  # The only remaining reference edit is this task's explicit new cache lesson.
  assert rel=='references/recurring-refresh.md'
  old='1. Ler contrato, checkpoint e estado do job existente; conferir ausência de execução concorrente. Validar Drive/Sheets na SA canônica.'
  new=lp.read_text();before=mp.read_text();start=new.index('1. Ler contrato, checkpoint e estado do job existente;');end=new.index(' Validar Drive/Sheets na SA canônica.',start)+len(' Validar Drive/Sheets na SA canônica.')
  assert new[:start]+old+new[end:]==before
  shutil.copy2(lp,mp)
 assert lp.read_bytes()==mp.read_bytes();hashes[rel]=hashlib.sha256(lp.read_bytes()).hexdigest()
cl['repair']={'scope':'Accounts Edit/Search only; native fresh-bounds background pixel click','root_cause_proven':'Element-index route failed to establish effective query; same authenticated UI recovered with pixel focus. Internal driver/UI focus cause remains unproven.','validated_targets':36,'canonical_collector_live_canary':str(B/'canonical-collector-canary/336562339356179-receipt.json'),'unit_tests':'valid native/scaled bounds and invalid bounds rejected','live_mirror_sha256':hashes,'runtime_config_changes':0,'foreground_escalations':0}
def contract_write():
 with(H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=read(C);assert c['account_ids']==read(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pending_card_history']={'status':'current_events_resolved_historical_gaps_preserved','account_ids':[],'pending_ui':[],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
save(B/'closure-current.json',cl);contract_write()
state=f"06nov manual1568253396287225898:47API11cartao36linha;metricas{cl['validated_metrics_at']};H36/36renovadas{cl['h_read_at_min']}a{cl['h_read_at_max']};HUSD{cl['h_sum_usd']};D8provasrenovadas,pending_ui0;35lacunas historicas34semprova+Growpowerhub04semcobrancalocalizada. Invoices29outubroUSD{cl['invoice_due_usd']};saldoUSD{cl['totals_usd']['balance']};media03-05novUSD{cl['totals_usd']['average_daily']};JnovUSD{cl['totals_usd']['month_spend']}. Readback integral fontes/valores/notas/links/totais/47IDsPASS;outraaba intacta. BuscaPC1recuperada por pixel local/coletorcanonico testado;sem authgate;0pagamento/billing/cronchanges;leasefree. Paridadeexata abasbrowseriniciais nao estabelecida,cacheAXexpirou;estadofinal6tabs,evidenciacoletaa7compropria,e finalAccountsoriginal."
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step','Manter mesmo job08:02/14:02/21:02Eastern e mesmo47IDs. Proximo tick usa coletor Accounts corrigido;provasD antigas reutilizaveis sem eventos novos. Capturar baselineAXcompleta+pixelsduraveis antes da UI;nao contar TabItem do site como abadeChrome. Sem pendenciasUI atuais;35lacunasD historicas qualificadas.','--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok'
cp=[x for x in read(ROOT/'data/agent-checkpoints.json')['checkpoints']if x['id']=='meta-manual-payments-digital-trust'];assert len(cp)==1 and cp[0]['source']==cl['closure_receipt']
entry={'id':ID,'agent':'zeus','type':'authorized_manual_financial_refresh_and_safe_input_recovery','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','verification':{'accounts':47,'fresh_metrics':47,'fresh_h':36,'preserved_h':0,'pending_d':0,'renewed_d':8,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0},'skill_sha256':hashes}
def inventory(e):
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=read(I);arr=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(arr)if x.get('id')==ID];assert len(matches)<=1
  if matches:arr[matches[0]]=e
  else:arr.append(e)
  skills=[x for x in d['skills_hermes']['zeus']if x.get('name')=='meta-manual-payments-planning'];assert len(skills)==1;skills[0].update(last_verified_at=cl['verified_at'],last_verified_receipt=cl['closure_receipt'],accounts_search_repair_sha256=hashes)
  save(I,d);assert len([x for x in read(I)['runtime_artifacts']if x.get('id')==ID])==1
inventory(entry)
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data/skill/script','--path',str(C)+'; '+str(live/'scripts/read_pc1_accounts_list.py')+'; '+str(B/'closure-current.json'),'--reason','Atualizacao integral solicitada1568253396287225898,mesmos47IDs/job. Recuperar buscaAccounts por pixel fresco em background sem bypass/autenticacao/runtime global. Aprendizado persistido e espelhos validados.','--evidence',f"47API/36H/8D validadas;pending_ui0;35lacunasDhistoricas;29invoicesoutubroUSD{cl['invoice_due_usd']};readbackCGIJ/EF/H/Dnotasfontes+linksUSD+totaisDecimalPASS;outraaba intacta;coletorcanonico canarioPASS e boundsunitPASS;3arquivos skillmirrorSHA256iguais. Leasefree,0pagamento/MetaWrite/billing/cronchanges. ValidacaoabasrecuperadadecacheAXexpirado:6browserfinal/7duranteaba propria;paridadeinicialexatanaocertificada." ]
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0
m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1]
x=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));x['load_env'](x['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
assert msg['id']==mid and msg['channel_id']=='1498132022634483894'and not msg['content']and not msg['mentions']and msg['embeds']and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
assert {'Ação','Tipo','Path','Motivo','Evidência'}<={f['name']for f in msg['embeds'][0]['fields']}
cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);save(B/'closure-current.json',cl);contract_write();entry.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);inventory(entry)
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_manual_refresh_recovered_validated','source_thread':'1563926766286803004','source_message':'1568253396287225898','job_id':job['id'],'runtime_artifact_id':ID,'receipt':cl['closure_receipt'],'accounts':47,'fresh_h':36,'preserved_h':0,'renewed_d':8,'historical_d_gaps':35,'pending_ui':[],'other_sheet_data_unchanged':True,'payments':0,'meta_writes':0,'cron_changes':0,'skill_sha256':hashes,'report_infra_message_id':mid,'report_infra_readback':True}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
print(json.dumps({'status':'sealed','contract_readback':True,'checkpoint_readback':True,'inventory_readback':True,'audit_readback':True,'report_infra_message_id':mid,'report_infra_readback':True,'next_run_at':job['next_run_at'],'skill_mirrors_equal':True},ensure_ascii=False))
