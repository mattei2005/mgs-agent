"""Inventory and direct canonical REPORT-INFRA with exact readback; no duplicate report."""
import pathlib,json,os,hashlib,datetime,fcntl,subprocess,urllib.request,importlib.util
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';D=A/'private/account-links-1546752274989191230';K=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard');marker='FINANCE-ACCOUNT-LINKS-1546752274989191230'
files=[A/f for f in ['deploy/account-links-operation.py','deploy/reconcile-account-links.mjs','deploy/record-account-links-inventory.py','tests/account-links-preflight.mjs','tests/account-links-browser.mjs']]+[R/'docs/finance-system-product-direction.md',R/'reports/finance-account-links-1546752274989191230.md',K/'references/explicit-account-source-reconciliation.md',K/'references/monthly-periods-and-ad-accounts.md']
for n in ['prepared.json','stage-readback.json','apply-readback.json','browser-readback.json']:assert json.loads((D/n).read_text())['pass']
proof=json.loads((D/'apply-readback.json').read_text());live=json.loads((D/'browser-readback.json').read_text());assert len(proof['bindings'])==2 and len(live['checks'])==4 and live['pending_with_money']==0
now=datetime.datetime.now(datetime.timezone.utc).isoformat();entry={'id':marker.lower(),'agent':'zeus','authorization_message_ids':['1546752274989191230'],'thread_id':'1545426987756298340','status':'published_verified','updated_at':now,'type':'finance_account_source_reconciliation','evidence_path':str(D),'backup_remote':'/home/zeus/mgs-finance-backups/1546752274989191230','isolated_database':'mgs_finance_links_1546752274989191230','stage':'/var/tmp/mgs-finance-account-links-1546752274989191230','scope':{'bindings':proof['bindings'],'accounts_before':80,'accounts_after':82,'pending_with_money':0,'browser_checks':4,'financial_scenarios_unchanged':True,'source_values_preserved':True,'meta_writes':False,'sheet_writes':False,'service_restart':False},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);p=R/'data/infra-inventory.json';data=json.loads(p.read_text());items=data.setdefault('runtime_artifacts',[]);existing=next((x for x in items if x.get('id')==entry['id']),None)
 if existing:assert existing['files']==entry['files'],'Concurrent inventory differs'
 else:
  items.append(entry);data['_meta']['updated_at']=now;t=p.with_suffix('.manager-layout.tmp')
  with t.open('w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])['files']==entry['files']
spec=importlib.util.spec_from_file_location('notice',A/'finance-notifications.py');assert spec is not None and spec.loader is not None;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);token=m.dotenv_values('/root/.hermes/profiles/zeus/.env')['DISCORD_BOT_TOKEN'];headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Readback'};base='https://discord.com/api/v10/channels/1498132022634483894/messages'
def get(url):return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25))
def matches():return [d for d in get(base+'?limit=50') if marker in json.dumps(d.get('embeds',[]))]
found=matches()
if not found:
 env=dict(os.environ);env['MGS_DISCORD_BOT_TOKEN_OVERRIDE']=token;env.pop('MGS_DISCORD_API_URL_OVERRIDE',None)
 r=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','finance-account-links','--path','Finance master-ad-accounts + dois aliases explícitos + skill financeira','--reason',marker+': Rodolfo confirmou os IDs1063939172741186 e7840111366055613 para as duas pendências.','--evidence','Meta live nomes/IDs/moeda/fuso PASS; backupduplo/hash/restore; canário+produção revision3→4, cadastro80→82;62chaves vinculadas sem alterar valores/cenários,4checks390/1440,0avisos com dinheiro,0JS. Sem Meta/Sheets/service writes. Registry/inventário/readback.'],env=env,text=True,capture_output=True)
 assert r.returncode==0,'Helper failed: reconcile readback before retry';found=matches()
assert len(found)==1;message=get(base+'/'+found[0]['id']);assert message['content']=='' and len(message['embeds'])==1 and not message.get('mentions')
out={'pass':True,'inventory_readback':True,'report_message_id':message['id'],'report_readback':True,'files':len(files),'accounts':82,'linked_accounts':len(proof['bindings']),'pending_with_money':0};(D/'final-readback.json').write_text(json.dumps(out,indent=2))
with (R/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'event':'finance_account_links_confirmed','agent':'zeus','authorization_message_ids':entry['authorization_message_ids'],'scope':entry['scope'],**out})+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(out))
