import pathlib,json,datetime,fcntl,os,hashlib,subprocess,re,urllib.request
R=pathlib.Path('/root/mgs-agent');W=pathlib.Path(__file__).parent;ident='finance-cleanup-audit-1552356639850373301';now=datetime.datetime.now(datetime.timezone.utc).isoformat();a=json.loads((W/'analysis.json').read_text());assert a['status']=='analysis_only_no_deletion' and not a['process_references'] and not a['errors'];assert json.loads((W/'retained-restore.json').read_text())['pass']
record={'id':ident,'type':'finance-cleanup-analysis','authority':'1552356639850373301','agent':'zeus','updated_at':now,'status':'analysis_complete_no_deletion','report_path':'reports/'+ident+'.md','evidence_path':str(W),'target_count':a['target_count'],'file_count':a['file_count'],'proposed_reclaim_bytes':a['inode_aware_reclaim_bytes'],'deletions':0,'manifest_sha256':hashlib.sha256((W/'analysis.json').read_bytes()).hexdigest(),'retained_restore_pass':True}
p=R/'data/infra-inventory.json'
with p.open('r+') as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=json.load(f);d['runtime_artifacts']=[x for x in d['runtime_artifacts'] if x.get('id')!=ident]+[record];d['_meta']['updated_at']=now;f.seek(0);json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n');f.truncate();f.flush();os.fsync(f.fileno())
event={'timestamp':now,'agent':'zeus','action':'finance_cleanup_candidates_audited','authority_message_id':'1552356639850373301','thread_id':'1545426987756298340','status':'analysis_only','artifact_id':ident,'report':record['report_path'],'deletions':0}
p=R/'logs/events-audit.jsonl'
with p.open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event)+'\n');f.flush();os.fsync(f.fileno())
assert next(x for x in json.loads((R/'data/infra-inventory.json').read_text())['runtime_artifacts'] if x.get('id')==ident)==record;assert any(json.loads(x)==event for x in p.read_text().splitlines()[-10:]);print('INVENTORY_AUDIT_READBACK_OK')
r=subprocess.run(['bash',str(R/'scripts/send-report-infra-embed.sh'),'--action','criada','--type','audit/skill/docs/data','--path','work/'+ident+';reports/'+ident+'.md;skill mgs-finance-dashboard current-security-performance-and-dr;registry/checkpoint','--reason','Rodolfo1552356639850373301 pediu analisar limpeza financeira, sem excluir.','--evidence','270alvos de teste55.60GB;zero refs processos/hardlinks externos;9amostras preservadas;tarrestore85868celulas.13stages22.69GB condicionais. Producao remota ativa. Nenhuma exclusao nem alteracao runtime/regras.'],capture_output=True,text=True,timeout=60);assert r.returncode==0;match=re.search(r'message_id=(\d+)',r.stdout);assert match;mid=match.group(1);token=None
for line in pathlib.Path('/root/.hermes/profiles/zeus/.env').read_text().splitlines():
 if line.startswith('DISCORD_BOT_TOKEN='):token=line.split('=',1)[1].strip().strip('\"').strip("'")
assert token
req=urllib.request.Request(f'https://discord.com/api/v10/channels/1498132022634483894/messages/{mid}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS/1.0'})
with urllib.request.urlopen(req,timeout=20) as response:m=json.load(response)
assert not m['content'] and len(m['embeds'])==1 and not m.get('mentions');(W/'infra-report.json').write_text(json.dumps({'message_id':mid,'readback':True}));print(json.dumps({'report_infra_readback':True,'message_id':mid}))
