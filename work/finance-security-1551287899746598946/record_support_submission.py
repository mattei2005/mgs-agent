import json,os,datetime,fcntl,subprocess,urllib.request,importlib.util
from pathlib import Path
R=Path('/root/mgs-agent');W=R/'work/finance-security-1551287899746598946';marker='GITHUB-SENSITIVE-DATA-SUBMITTED-1551299336959434852';artifact='finance-security-continuity-1551287899746598946';now=datetime.datetime.now(datetime.timezone.utc).isoformat()
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=R/'data/infra-inventory.json';d=json.loads(p.read_text());entry=next(x for x in d['runtime_artifacts'] if x.get('id')==artifact)
 entry['status']='support_request_submitted_historical_purge_pending';entry['updated_at']=now;entry['support']={'request_submitted':True,'confirmation':'Your message has been successfully submitted.','evidence_message_id':'1551299336959434852','ticket_reference':None,'response_deadline':None,'next_gate':'GitHub confirmation plus historical URL no longer serving dump'}
 d['_meta']['updated_at']=now;tmp=p.with_suffix('.support-submission.tmp')
 with open(tmp,'w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);read=next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==artifact);assert read['support']['request_submitted'] is True and read['status']==entry['status']
with (R/'logs/events-audit.jsonl').open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);exists=any(marker in line for line in f)
 if not exists:f.write(json.dumps({'timestamp':now,'event':'github_sensitive_data_removal_request_submitted','marker':marker,'agent':'zeus','actor':'rodolfo','discord_message_id':'1551299336959434852','repository':'mattei2005/mgs-agent','historical_commit':'a73a267d04109c85abcb0dea7642b6c3b9736a59','path':'work/finance-adops-1551275920671776839/before.dump','confirmation':'Your message has been successfully submitted.','ticket_reference':None,'removal_verified':False,'autocommit':'paused_pending_historical_purge_validation'})+'\n');f.flush();os.fsync(f.fileno())
spec=importlib.util.spec_from_file_location('notice',R/'apps/finance-system/finance-notifications.py');assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);token=m.dotenv_values('/root/.hermes/profiles/zeus/.env')['DISCORD_BOT_TOKEN'];headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Readback'};base='https://discord.com/api/v10/channels/1498132022634483894/messages'
def get(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30))
found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
if not found:
 env=dict(os.environ);env['MGS_DISCORD_BOT_TOKEN_OVERRIDE']=token;env.pop('MGS_DISCORD_API_URL_OVERRIDE',None)
 q=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','security-incident/status','--path',str(R/'reports/finance-security-recovery-1551287899746598946.md'),'--reason',marker+': proprietario submeteu pedido de remocao de dados sensiveis ao GitHub.','--evidence','Confirmacao GitHub: message successfully submitted (Discord1551299336959434852). Sem protocolo/prazo visivel. Main permanece limpo;objeto historico ainda nao revalidado como removido;auto-push continua pausado. Inventario,audit e checkpoint atualizados.','--color','16753920'],env=env,text=True,capture_output=True,timeout=90);assert q.returncode==0,'REPORT helper failed; reconcile before retry'
 found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
assert len(found)==1;msg=get(base+'/'+found[0]['id']);assert msg['content']=='' and len(msg['embeds'])==1 and not msg.get('mentions')
out={'inventory_readback':True,'audit_readback':marker in (R/'logs/events-audit.jsonl').read_text(),'report_message_id':msg['id'],'support_submitted':True,'ticket_reference':None,'removal_verified':False};(W/'support-submission-readback.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))