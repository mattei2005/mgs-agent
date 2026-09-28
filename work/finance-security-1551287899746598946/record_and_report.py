import json,os,datetime,fcntl,hashlib,subprocess,urllib.request,importlib.util
from pathlib import Path
R=Path('/root/mgs-agent');W=R/'work/finance-security-1551287899746598946';marker='FINANCE-SECURITY-CONTINUITY-1551287899746598946';report=R/'reports/finance-security-recovery-1551287899746598946.md'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
files=[report,R/'reports/finance-august-continuity-1551287899746598946.md',R/'.gitignore']+list(W.glob('*.py'))+list(W.glob('*.mjs'))+[Path('/root/.hermes/profiles/zeus/skills')/x for x in ['ops/mgs-finance-dashboard/SKILL.md','ops/hermes-agent-operations/references/providers-codex-oauth.md','ops/hermes-agent-operations/references/git-autocommit-secret-containment.md']]
rot=json.loads((W/'rotate-auth-result.json').read_text());check=json.loads((W/'check-auth-result.json').read_text());assert rot['financial']==check['financial'] and all(x['vault_password_matches'] for x in check['users'])
entry={'id':marker.lower(),'agent':'zeus','authorization_message_ids':['1551287899746598946'],'thread_id':'1551285829584953484','finance_thread_id':'1545426987756298340','status':'recovery_validated_github_retention_owner_support_blocked','updated_at':now,'type':'security_remediation_and_finance_session_continuity','report':str(report),'evidence_path':str(W),'security':{k:rot[k] for k in ['rotated','sessions_revoked','devices_revoked','mfa_preserved','financial_unchanged']},'git':json.loads((W/'git-rewrite-result.json').read_text()),'session':json.loads((W/'session-continuity-result.json').read_text()),'support':{'ticket_submitted':False,'blocker':'Owner GitHub browser login unavailable; vault prompt unsupported in headless session','url':'https://support.github.com/contact'},'autocommit':'paused_pending_github_retention_closure','supersedes_security_state_of':'finance-adops-1551275920671776839-security-block','files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=R/'data/infra-inventory.json';d=json.loads(p.read_text());items=d.setdefault('runtime_artifacts',[]);found=next((x for x in items if x.get('id')==entry['id']),None)
 if found:entry=found
 else:items.append(entry)
 d['_meta']['updated_at']=now;tmp=p.with_suffix('.finance-security.tmp')
 with open(tmp,'w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (R/'logs/events-audit.jsonl').open('a+') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);exists=any(marker in line and 'finance_security_recovery_continuity' in line for line in f)
 if not exists:f.write(json.dumps({'timestamp':now,'event':'finance_security_recovery_continuity','marker':marker,**{k:entry[k] for k in ['agent','authorization_message_ids','thread_id','finance_thread_id','status','security','report','support','autocommit']}})+'\n');f.flush();os.fsync(f.fileno())
spec=importlib.util.spec_from_file_location('notice',R/'apps/finance-system/finance-notifications.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);token=m.dotenv_values('/root/.hermes/profiles/zeus/.env')['DISCORD_BOT_TOKEN'];headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Readback'};base='https://discord.com/api/v10/channels/1498132022634483894/messages'
def get(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30))
found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
if not found:
 env=dict(os.environ);env['MGS_DISCORD_BOT_TOKEN_OVERRIDE']=token;env.pop('MGS_DISCORD_API_URL_OVERRIDE',None)
 p=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','security/session-continuity','--path',str(report),'--reason',marker+': remediacao autorizada preservando MFA, dados financeiros e contexto de agosto.','--evidence','6 senhas/cofres/DB PASS;141sessoes+8devices revogados;MFA e financeiro identicos. Main limpo com lease, tags intactas;GitHub SHA antigo HTTP206: suporte exige login dono, ticket NAO aberto. Auto-push pausado.170msgs originais intactas;child nativo+rota validados;Astra smoke real PASS;proxima entrada Discord nao observada. Checkpoint/registry/skills/inventario/audit validados.','--color','16753920'],env=env,text=True,capture_output=True,timeout=90)
 assert p.returncode==0,'REPORT helper failed; reconcile before retry'
 found=[x for x in get(base+'?limit=50') if marker in json.dumps(x.get('embeds',[]))]
assert len(found)==1;msg=get(base+'/'+found[0]['id']);assert msg['content']=='' and len(msg['embeds'])==1 and not msg.get('mentions')
out={'inventory_readback':True,'audit_readback':marker in (R/'logs/events-audit.jsonl').read_text(),'report_readback':True,'message_id':msg['id'],'channel_id':'1498132022634483894','status':entry['status']};(W/'report-readback.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
