import json,os,datetime,fcntl,hashlib,subprocess,urllib.request,importlib.util
from pathlib import Path
R=Path('/root/mgs-agent');W=R/'work/finance-adops-1551275920671776839';marker='FINANCE-ADOPS-1551275920671776839-SECURITY-BLOCK'
files=[R/'reports/finance-adops-application-1551275920671776839.md',Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md'),Path('/root/.hermes/profiles/zeus/skills/ops/hermes-agent-operations/references/git-autocommit-secret-containment.md')]+[W/x for x in ['build_plan.py','apply.mjs','run_remote.py','fix_source_numbers.py','final_validation.py','final-summary.json']]
now=datetime.datetime.now(datetime.timezone.utc).isoformat();entry={'id':marker.lower(),'agent':'zeus','authorization_message_ids':['1551275920671776839','1551279009415958700'],'thread_id':'1545426987756298340','status':'partial_finance_verified_security_critical_block','updated_at':now,'type':'finance_reconciliation_and_backup_incident','evidence_path':str(W),'report':str(files[0]),'finance':json.load(open(W/'verify-out.json')),'security':{'public_repository':'mattei2005/mgs-agent','exposure_commit':'a73a267d0','remote_head_at_containment':'025531c4e36e35e4cc663c2ed483ceffd33be284','password_hash_rows':6,'encrypted_mfa_rows':7,'session_rows':308,'trusted_device_rows':9,'autocommit':'stopped_inactive_dead','history_purge':'not_authorized_not_performed','credential_rotation':'not_authorized_not_performed'},'backup':json.load(open(W/'backup-readback.json')),'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=R/'data/infra-inventory.json';d=json.load(open(p));items=d.setdefault('runtime_artifacts',[]);found=next((x for x in items if x.get('id')==entry['id']),None)
 if found:assert found==entry
 else:items.append(entry)
 d['_meta']['updated_at']=now;tmp=p.with_suffix('.adops.tmp')
 with open(tmp,'w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.load(open(p))['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (R/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'event':'finance_adops_partial_and_public_dump_exposure','agent':'zeus',**{k:entry[k] for k in ['authorization_message_ids','thread_id','status','security','report']}})+'\n');f.flush();os.fsync(f.fileno())
spec=importlib.util.spec_from_file_location('notice',R/'apps/finance-system/finance-notifications.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);token=m.dotenv_values('/root/.hermes/profiles/zeus/.env')['DISCORD_BOT_TOKEN'];headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Readback'};base='https://discord.com/api/v10/channels/1498132022634483894/messages'
def get(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30))
found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
if not found:
 env=dict(os.environ);env['MGS_DISCORD_BOT_TOKEN_OVERRIDE']=token;env.pop('MGS_DISCORD_API_URL_OVERRIDE',None)
 r=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','finance-data/security-incident','--path',str(files[0]),'--reason',marker+': reconciliacao autorizada e incidente causado por backup completo em work/ auto-publicado no GitHub PUBLICO.','--evidence','Finance PASS: workspace391→392/cadastro6→7;audit1513/1514;50contas gastos;21sitesSB;4celulas corrigidas. Dump publicado a73a267d0:6hashes senha,7MFA cifrados,308sessoes,9trusted. Copia local protegida;autocommit parado. Purga/rotacao aguardam confirmacao critica. AV/M2 pendentes;TopFeed detalhe6937.68 vs6937.50. Backup restaurado;servicos ativos.','--color','15158332'],env=env,text=True,capture_output=True,timeout=90)
 assert r.returncode==0,'REPORT helper failed; reconcile before retry'
 found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
assert len(found)==1;message=get(base+'/'+found[0]['id']);assert message['content']=='' and len(message['embeds'])==1 and not message.get('mentions');out={'pass':True,'inventory_readback':True,'report_readback':True,'message_id':message['id'],'status':entry['status']};(W/'report-readback.json').write_text(json.dumps(out));print(json.dumps(out))
