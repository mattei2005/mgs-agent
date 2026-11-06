"""Seal verified partial financial refresh; never change billing or scheduler."""
import json,os,subprocess,fcntl,re,urllib.request,runpy
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');H=ROOT/'data/meta-manual-payments';C=H/'digital-trust-workbook-contract.json';I=ROOT/'data/infra-inventory.json';ID='meta-manual-payments-refresh-20261106-0802'
def read(p):return json.loads(p.read_text())
def save(p,d):
 tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p);assert read(p)==d
cl=read(B/'closure-current.json');assert cl['status']=='partial_updated_validated_pc1_search_input_unconfirmed'and cl['accounts']==47 and cl['fresh_h_count']==0 and cl['h_preserved_count']==36 and len(cl['pending_ui'])==5 and cl['other_sheet_data_unchanged']
cl.update(report_infra_status='pending',cron_changes=0,billing_changes=0)
job=[j for j in read(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs']if j['id']=='2ee720363d7d'][0]
assert job['schedule']['expr']=='2 8,14,21 * * *'and job['enabled']and job['timezone']=='America/New_York'and job['last_dispatch']['scheduled_at']=='2026-11-06T08:02:00-05:00'
cl['cron_coordination']={'job_id':job['id'],'same_scheduled_execution':True,'schedule_unchanged':True,'next_run_at':job['next_run_at']}
cl['ui_cleanup']=read(B/'ui-cleanup.json');assert cl['ui_cleanup']['tab_labels_exact_parity']and cl['ui_cleanup']['total_elements_parity']and cl['ui_cleanup']['preexisting_tabs']==cl['ui_cleanup']['final_tabs']==2
cl['pc1_blocker'].update(owned_tab_closed_independently_verified=True,preexisting_tab_labels_restored=True,preexisting_surface_restored_exact_inline_ax=cl['ui_cleanup']['inline_ax_exact_parity'],technical_dependency='Resolve search input/focus confirmation in approved Chrome. No login/2FA gate observed; no human authentication requirement established. Current run stopped after first failed search, no bypass/reload/alternative profile or further navigation.')
cl['ui_cleanup']['remaining_ax_difference']={'count':1,'element_role':'Button','changed_field':'label','index':11,'cause':'not established; no input or additional navigation used to change it'}
cl['pc1_blocker']['visual_check']='vision_analyze read blocked.png: Digital Trust Accounts loaded; search empty, unfiltered001 rows; no provider/auth/native gate.'
def contract_write():
 with(H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=read(C);assert c['account_ids']==read(B/'contract-before.json')['account_ids'];c['latest_refresh_qualification']=cl;c['next_run_at']=job['next_run_at'];c['pending_card_history']={'status':'blocked_pc1_search_input_unconfirmed','account_ids':[x['account_id']for x in cl['pending_ui']],'pending_ui':cl['pending_ui'],'historical_blank_account_ids':[x['account_id']for x in cl['historical_d_gaps']],'historical_blank_without_proof_count':sum(x['reason']=='no_historical_card_instrument_proof_collected'for x in cl['historical_d_gaps']),'verified_at':cl['verified_at'],'evidence':cl['closure_receipt']};save(C,c)
save(B/'closure-current.json',cl);contract_write()
state=f"06nov08:06EST:47API validadas(11cartao36linha);29invoices outubro USD{cl['invoice_due_usd']};saldo USD{cl['totals_usd']['balance']};media03-05nov USD{cl['totals_usd']['average_daily']};gasto novembro01-06parcial USD{cl['totals_usd']['month_spend']}. H0/36novas,36preservadas04nov21:07-21:25EST. Accounts autenticada,mas busca vazia apos input:searched_row_not_ready_336562339356179;sem gate login/2FA/provider. Parada apos primeira falha,sem bypass/reload/perfil alternativo. D5eventospendentes e35vazios(34sem prova;Growpowerhub04 no_charge_located). Fullreadback CGIJ/EF/Hhistorico/D+totais/links/notasUSD;outraaba intacta,abaspreexistentes restauradas,1labelButtonAXdiferente,leasefree;0pagamento/MetaWrite/cronchanges."
next_step='Zeus: diagnosticar e validar foco/input no Chrome PC1 aprovado antes de repetir navegacao de H/D. Nao presumir logout ou requerer autenticacao sem gate real. Preservar timestamps H ate leitura visual nova. Retomar apenas no mesmo contrato/job47IDs e cadencia08:02/14:02/21:02Eastern;sem writer/job paralelo. PendenciasD devem vir da proxima coleta live.'
r=subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','meta-manual-payments-digital-trust','--agent','zeus','--thread-id','1563926766286803004','--objective','Atualizar mesmos47IDs Digital Trust; J novembro e invoices outubro; sem pagamentos ou billing','--state',state,'--next-step',next_step,'--source',cl['closure_receipt']],capture_output=True,text=True,check=True);assert json.loads(r.stdout)['status']=='ok'
cp=[x for x in read(ROOT/'data/agent-checkpoints.json')['checkpoints']if x['id']=='meta-manual-payments-digital-trust'];assert len(cp)==1 and cp[0]['source']==cl['closure_receipt']
entry={'id':ID,'agent':'zeus','type':'authorized_recurring_financial_snapshot','status':cl['status'],'updated_at':cl['verified_at'],'evidence':cl['closure_receipt'],'report_infra_status':'pending','verification':{'accounts':47,'fresh_metrics':47,'fresh_h':0,'preserved_h':36,'pending_d':5,'historical_blank_d':35,'other_sheet_data_unchanged':True,'lease_free':True,'meta_writes':0,'payments_executed':0,'cron_changes':0}}
def inventory(e):
 with(ROOT/'data/.meta-financial-inventory.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);d=read(I);arr=d.setdefault('runtime_artifacts',[]);matches=[k for k,x in enumerate(arr)if x.get('id')==ID];assert len(matches)<=1
  if matches:arr[matches[0]]=e
  else:arr.append(e)
  save(I,d);assert len([x for x in read(I)['runtime_artifacts']if x.get('id')==ID])==1
inventory(entry)
args=[str(ROOT/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','data/financial-recurring-refresh','--path',str(C)+'; '+str(B/'closure-current.json'),'--reason','Tick autorizado06nov08:02EST mesmo job47IDs. Accounts autenticada;buscaPC1 nao confirmada,sem gate auth e sem bypass/reload/perfil alternativo. H/D preservados;sem mudanca cron/billing.','--evidence',f"PARCIAL:47API11cartao36linha;CGIJ/EF/D/Hhistorico+notasreadbackexatos;totaisF/G/H/I/J DecimalPASS;media03-05nov;J01-06novparcial;H0/36novas,36historicas04nov21:07-21:25EST;D5eventospendentes,35lacunas;29invoicesoutubroUSD{cl['invoice_due_usd']};outraaba intacta;abaspreexistentes restauradas,leasefree;0pagamentos/MetaWrites/cronchanges." ]
r=subprocess.run(args,capture_output=True,text=True,timeout=180);(B/'infra-report-output.txt').write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0
m=re.search(r'message_id=(\d+)',r.stdout);assert m;mid=m[1]
x=runpy.run_path(str(ROOT/'scripts/discord-bot-post.py'));x['load_env'](x['DEFAULT_ENV']);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE')or os.environ['DISCORD_BOT_TOKEN'];req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/'+mid,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=25)as response:assert response.status==200;msg=json.load(response)
assert msg['id']==mid and msg['channel_id']=='1498132022634483894'and not msg['content']and not msg['mentions']and msg['embeds']and msg['embeds'][0]['title'].startswith('REPORT-INFRA')
cl.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);save(B/'closure-current.json',cl);contract_write();entry.update(report_infra_status='sent_verified',report_infra_message_id=mid,report_infra_readback=True);inventory(entry)
event={'at':datetime.now().astimezone().isoformat(),'agent':'zeus','event':'meta_manual_payments_recurring_refresh_partial_search_input_unconfirmed','source_thread':'1563926766286803004','job_id':job['id'],'runtime_artifact_id':ID,'receipt':cl['closure_receipt'],'accounts':47,'fresh_h':0,'preserved_h':36,'historical_d_gaps':35,'pending_ui':cl['pending_ui'],'other_sheet_data_unchanged':True,'payments':0,'meta_writes':0,'cron_changes':0,'report_infra_message_id':mid,'report_infra_readback':True}
with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
assert json.loads((ROOT/'logs/events-audit.jsonl').read_text().splitlines()[-1])==event
print(json.dumps({'status':'partial_sealed','contract_readback':True,'checkpoint_readback':True,'inventory_readback':True,'audit_readback':True,'report_infra_message_id':mid,'report_infra_readback':True,'next_run_at':job['next_run_at']},ensure_ascii=False))
