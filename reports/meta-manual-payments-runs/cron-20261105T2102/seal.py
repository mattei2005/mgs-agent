"""Seal current partial tick; no billing, authentication or scheduler changes."""
import json,os,subprocess,fcntl,re,urllib.request,runpy,hashlib
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-20261105-2102'
def read(p):return json.loads(p.read_text())
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p);assert read(p)==d
cl=read(B/'closure-current.json');assert cl['status']=='partial_updated_validated_pc1_search_input_unconfirmed'and cl['accounts']==47 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and len(cl['pending_ui'])==5 and cl['other_sheet_data_unchanged']
cl['report_infra_status']='pending';cl['cron_changes']=0;cl['billing_changes']=0
job=[j for j in read(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if j['id']=='2ee720363d7d'][0];assert job['schedule']['expr']=='2 8,14,21 * * *'and job['enabled']and job['timezone']=='America/New_York'
assert job['last_dispatch']['scheduled_at']=='2026-11-05T21:02:00-05:00'
cl['cron_coordination']={'job_id':job['id'],'same_scheduled_execution':True,'schedule_unchanged':True,'next_run_at':job['next_run_at']}
cl['ui_cleanup']=read(B/'ui-cleanup.json');assert cl['ui_cleanup']['inline_ax_exact_parity']and cl['ui_cleanup']['tab_labels_exact_parity']
cl['pc1_blocker']['preexisting_surface_restored_exact_inline_ax']=True
cl['pc1_blocker']['technical_dependency']='Resolve input/focus verification in approved Chrome before further reads. No current authentication action proven necessary.'
ref=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/references/recurring-refresh.md');mirror=ROOT/'profiles/zeus-skills/ops/meta-manual-payments-planning/references/recurring-refresh.md'
assert ref.read_bytes()==mirror.read_bytes()
cl['procedural_learning']={'subsystem':'skill','path':str(ref),'summary':'Validate periods at collection timestamp in each account timezone; next-day European partial periods valid in Eastern night ticks. Correct only stale validator after landed writes.','canonical_mirror_equal':True,'sha256':hashlib.sha256(ref.read_bytes()).hexdigest()}
def contract_write():
 with(H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=read(C);assert c['account_ids']==read(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pending_card_history']={'status':'blocked_pc1_search_input_unconfirmed','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
contract_write()
state=f"05nov21:08EST:47API validadas(11cartao36linha),29invoices outubro USD{cl['invoice_due_usd']};saldo USD{cl['totals_usd']['balance']},media USD{cl['totals_usd']['average_daily']},gasto novembro parcial USD{cl['totals_usd']['month_spend']}. G02-04nov nas Americas e03-05nov Europa;J ate05nov Americas/06nov Europa. Accounts autenticada,mas busca nao confirmada em pixels:searched_row_not_ready_336562339356179,campo vazio/lista001.0Hnovas,36Hpreservadas04nov21:07-21:25EST.5eventosDpendentes(1150399088163771 e1414197490675732 novos ante14h),35lacunas historicas preservadas. Outraaba intacta,superficie AX igual baseline,leasefree,0MetaWrite/pagamento."
next_step='Zeus: diagnosticar confirmacao de foco/input no Chrome aprovado PC1 antes de novas leituras;nao presumir logout ou solicitar autenticacao sem novo gate provado. Respeitar parada sem bypass/reload/perfil alternativo. Na proxima execucao existente renovar todos36H e pendenciasD atuais,mesmos47IDs e cadencia08:02/14:02/21:02Eastern. Preservar horas antigas ate prova.'
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',next_step,'--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok'
cp=[x for x in read(ROOT/'data/agent-checkpoints.json')['checkpoints']if x['id']=='meta-manual-payments-digital-trust'];assert len(cp)==1 and cp[0]['source']==cl['closure_receipt'];print('checkpoint_saved_readback',flush=True)
entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','procedural_learning':cl['procedural_learning'],'verification':{'accounts':47,'fresh_metrics':47,'fresh_h':0,'preserved_h':36,'card_proofs_updated':0,'pending_d':5,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0}}
def inventory(e):
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=read(I);arr=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(arr)if x.get('id')==ID];assert len(matches)<=1
  if matches:arr[matches[0]]=e
  else:arr.append(e)
  save(I,d);assert len([x for x in read(I)['runtime_artifacts']if x.get('id')==ID])==1
inventory(entry);save(B/'closure-current.json',cl)
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data/financial-recurring-refresh+skill','--path',str(C)+'; '+str(ref)+'; '+str(B/'closure-current.json'),'--reason','Tick autorizado05nov21:02Eastern mesmo job47IDs. BuscaPC1 nao confirmada apesar de Accounts autenticada;sem bypass/reload/perfil alternativo. Aprendizado:validar datas por timezone da conta,nao teto Eastern.','--evidence',f"PARCIAL:47API11cartao36linha;CGIJ/EF+notasreadbackexatos;F/G/H/I/JDecimalPASS;H0/36novas,36historicas04nov21:07-21:25EST;D5eventospendentes,35lacunas historicas;29invoicesoutubroUSD{cl['invoice_due_usd']};outraaba intacta;superficieAXigualbaseline,leasefree;0pagamentos/MetaWrites/cronchanges. Skill canonical/mirror SHA256 iguais." ]
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0
m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1]
x=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));x['load_env'](x['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
assert msg['id']==mid and msg['channel_id']=='1498132022634483894'and not msg['content']and not msg['mentions']and msg['embeds']and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);save(B/'closure-current.json',cl);contract_write()
entry.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);inventory(entry)
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial_search_input_unconfirmed','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':cl['closure_receipt'],'accounts':47,'fresh_h':0,'preserved_h':36,'historical_d_gaps':35,'pending_ui':cl['pending_ui'],'other_sheet_data_unchanged':True,'payments':0,'meta_writes':0,'cron_changes':0,'procedural_learning':cl['procedural_learning'],'report_infra_message_id':mid,'report_infra_readback':True}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
print(json.dumps({'status':'partial_sealed','contract_readback':True,'inventory_readback':True,'audit_readback':True,'report_infra_message_id':mid,'report_infra_readback':True,'skill_canonical_mirror_equal':True,'next_run_at':job['next_run_at']},ensure_ascii=False))
