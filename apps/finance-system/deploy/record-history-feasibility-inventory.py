"""Inventory and direct canonical REPORT-INFRA with exact readback; no duplicate report."""
import pathlib,json,os,hashlib,datetime,fcntl,subprocess,urllib.request,importlib.util
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';D=A/'private/history-feasibility-1546757745078968381';K=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard');marker='FINANCE-HISTORY-FEASIBILITY-1546757745078968381'
files=[A/'tests/history-feasibility.py',A/'deploy/record-history-feasibility-inventory.py',R/'docs/finance-system-product-direction.md',R/'reports/finance-history-feasibility-1546757745078968381.md',K/'SKILL.md',K/'references/closed-history-jan-jul-feasibility.md']
analysis=json.loads((D/'analysis.json').read_text());assert analysis['monthly_tabs']==40 and analysis['total_tabs_read']==41 and analysis['pass_readonly_capture']
raw=sorted(p for p in D.glob('*.json') if p.name not in ['manifest.json','final-readback.json']);manifest={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in raw};(D/'manifest.json').write_text(json.dumps({'files':manifest,'count':len(manifest)},indent=2));assert json.loads((D/'manifest.json').read_text())['count']==len(raw)
now=datetime.datetime.now(datetime.timezone.utc).isoformat();entry={'id':marker.lower(),'agent':'zeus','authorization_message_ids':['1546757745078968381'],'thread_id':'1545426987756298340','status':'published_verified','updated_at':now,'type':'finance_historical_readonly_audit','evidence_path':str(D),'production_backup_required':False,'snapshot_manifest':str(D/'manifest.json'),'scope':{'monthly_tabs':40,'total_tabs_read':41,'months':7,'read_source_cells':analysis['source_cells'],'snapshot_files':len(raw),'closed_values_policy':'January-July2026 frozen values; August+ unchanged','icaro_source_identified':False,'user_creation_requires_confirmation':True,'production_imports':0,'sheet_writes':0,'credentials_created':0,'service_restart':False},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
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
 r=subprocess.run([str(R/'scripts/send-report-infra-embed.sh'),'--action','modificada','--type','finance-history-feasibility','--path','Read-only Jan-Jul2026 study + historical policy + audit script/skill','--reason',marker+': Rodolfo pediu analisar sete meses fechados antes de importar; usuários adicionais dependem de confirmação crítica.','--evidence','40abas mensais+Caixa=41abas/6arquivos,377907células,40calendários completos. Viável snapshotindependente; abriltexto waves/22erros,ROIjanfev,NicolasREFlegado,Georgejanfevausentes e fonteÍcaro desconhecida. Sem importação,Sheetswrites ou usuários. Manifesthash/registry/checkpoint/candidato/reportreadback.'],env=env,text=True,capture_output=True)
 assert r.returncode==0,'Helper failed: reconcile readback before retry';found=matches()
assert len(found)==1;message=get(base+'/'+found[0]['id']);assert message['content']=='' and len(message['embeds'])==1 and not message.get('mentions')
out={'pass':True,'inventory_readback':True,'report_message_id':message['id'],'report_readback':True,'files':len(files),'snapshot_files':len(raw),'months_analyzed':7,'monthly_tabs':40,'total_tabs_read':41,'production_imports':0,'users_created':0};(D/'final-readback.json').write_text(json.dumps(out,indent=2))
with (R/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'event':'finance_history_feasibility_completed','agent':'zeus','authorization_message_ids':entry['authorization_message_ids'],'scope':entry['scope'],**out})+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(out))
