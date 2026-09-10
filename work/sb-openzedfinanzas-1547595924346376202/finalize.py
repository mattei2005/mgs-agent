import json,hashlib,fcntl,os,sys,importlib.util
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
P=Path(__file__).parent;root=Path('/root/mgs-agent');ident='sb-openzedfinanzas-1547595924346376202'
v=json.loads((P/'verification.json').read_text());assert v['daily_combined_exact_match'] and v['rows']==65
assert {(g['country'],g['vertical']) for g in v['groups']}=={('es','ccr'),('us','ccr')}
assert all(len(g['days'])==9 for g in v['groups'])
report=sys.argv[1] if len(sys.argv)>1 else None
if report:
 spec=importlib.util.spec_from_file_location('poster',root/'scripts/discord-bot-post.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.load_env(mod.DEFAULT_ENV);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
 req=Request(f'https://discord.com/api/v10/channels/1498132022634483894/messages/{report}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urlopen(req,timeout=30) as res:m=json.loads(res.read())
 assert m['content']=='' and not m['mentions'] and len(m['embeds'])==1
 assert '1547595924346376202' in str(m['embeds'][0]['fields'])
paths=sorted([p for p in P.iterdir() if p.is_file()]+[root/'data/agent-checkpoints.json',Path('/root/.hermes/profiles/zeus/skills/ops/revenue-spend-reporting-pipeline/references/gam-daily-excel-consolidation.md')])
assert '1547595924346376202' in paths[0].read_text() if paths[0].suffix=='.md' else True
entry={'id':ident,'agent':'zeus','authorization_message_id':'1547595924346376202','thread_id':'1545426987756298340','updated_at':datetime.now(timezone.utc).isoformat(),'type':'read_only_sb_country_vertical_validation','evidence_directory':str(P),'paths':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in paths],'verification':v,'financial_writes':False,'report_infra_pending':report is None,'report_infra_message_id':report,'report_infra_readback':report is not None}
p=root/'data/infra-inventory.json'
with (root/'data/.infra-inventory.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=json.loads(p.read_text());a=d.setdefault('runtime_artifacts',[]);a[:]=[r for r in a if r.get('id')!=ident];a.append(entry)
 tmp=p.with_name(p.name+'.sbvertical.tmp')
 with tmp.open('w') as o:json.dump(d,o,ensure_ascii=False,indent=2);o.write('\n');o.flush();os.fsync(o.fileno())
 tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p);assert next(r for r in json.loads(p.read_text())['runtime_artifacts'] if r.get('id')==ident)==entry
with (root/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':entry['updated_at'],'agent':'zeus','event':'sb_openzedfinanzas_vertical_verified','authorization_message_id':'1547595924346376202','evidence':v,'report_infra_message_id':report,'financial_writes':False},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps({'status':'PASS','records':v['rows'],'countries':['es','us'],'days_each':9,'inventory_readback':True,'report_readback':report is not None}))
