"""Inventory and direct canonical REPORT-INFRA with exact readback; no duplicate report."""
import pathlib,json,os,hashlib,datetime,fcntl,subprocess,urllib.request,importlib.util
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';D=A/'private/manager-layout-1546719646919434370';K=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard');marker='FINANCE-MANAGER-LAYOUT-1546719646919434370'
files=[A/f for f in ['public/operations.js','public/operations.css','public/navigation.css','tests/manager-layout.test.mjs','tests/manager-layout-browser.mjs','deploy/manager-layout-release.py','deploy/record-manager-layout-inventory.py']]+[R/'docs/finance-system-product-direction.md',R/'reports/finance-manager-layout-1546719646919434370.md',K/'SKILL.md',K/'references/manager-layout-and-total-contrast.md',K/'references/payments-approvals-nicolas-pilot.md']
for n in ['live-browser.json','deploy-readback.json','decimal-total-audit.json','prepared.json','published.json']:assert json.loads((D/n).read_text())['pass']
live=json.loads((D/'live-browser.json').read_text());assert live['dataHash']==json.loads((D/'before-browser.json').read_text())['dataHash'];assert '# fail 0' in (D/'node-tests.log').read_text()
now=datetime.datetime.now(datetime.timezone.utc).isoformat();entry={'id':marker.lower(),'agent':'zeus','authorization_message_ids':['1546719646919434370','1546720000134483970'],'thread_id':'1545426987756298340','status':'published_verified','updated_at':now,'type':'finance_manager_frontend','evidence_path':str(D),'backup_remote':'/home/zeus/mgs-finance-backups/1546719646919434370','isolated_database':'mgs_finance_manager_1546719646919434370','stage':'/var/tmp/mgs-finance-manager-1546719646919434370','scope':{'frontend_files':3,'blocks':8,'views_verified':len(live['managerViews']),'node_tests':48,'sidebar_logo_changed':False,'auth_or_financial_changes':False,'restart':False},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
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
 r=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','finance-manager-layout','--path','operations.js/css; navigation.css; manager-layout tests/deploy; product direction; skill0.1.28','--reason',marker+': Nicolas visual limpo/mes completo/decimais ptBR; contraste de todos os subtotais. Rodolfo1546719646919434370+1546720000134483970.','--evidence','48Node PASS;42visoes/8blocos/31ou30dias;390/1440px e0JS. Totais Decimal agosto/setembro PASS; snapshots financeiros identicos. Backup duplo/hash/restorePGisolado. Tres assets somente; sem credenciais/financeiro/acessos/restart. Inventario/registry/checkpoint e browser live readback.'],env=env,text=True,capture_output=True)
 assert r.returncode==0,'Helper failed: reconcile readback before retry';found=matches()
assert len(found)==1;message=get(base+'/'+found[0]['id']);assert message['content']=='' and len(message['embeds'])==1 and not message.get('mentions')
out={'pass':True,'inventory_readback':True,'report_message_id':message['id'],'report_readback':True,'files':len(files),'node_tests':48,'manager_views':len(live['managerViews']),'snapshot_parity':True};(D/'final-readback.json').write_text(json.dumps(out,indent=2))
with (R/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'event':'finance_manager_layout_published','agent':'zeus','authorization_message_ids':entry['authorization_message_ids'],'scope':entry['scope'],**out})+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(out))
