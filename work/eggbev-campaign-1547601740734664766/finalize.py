import json,re,hashlib,os,fcntl,sys,importlib.util
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
from datetime import datetime,timezone
from urllib.request import Request,urlopen
P=Path(__file__).parent;root=Path('/root/mgs-agent');ident='eggbev-campaign-1547601740734664766'
sets={k:json.loads((P/(k+'.json')).read_text())['data'] for k in ['adgroup','messenger','message','gam-keyvalues']}
for k,rows in sets.items():assert all(r['DOMAIN']=='eggbev' and '2026-09-01'<=r['DATE'][:10]<='2026-09-09' for r in rows)
for k,pk in [('adgroup','PK_JBF_PERFORMANCE_PER_ADGROUP'),('message','PK_PERFORMANCE_PER_MESSAGE'),('gam-keyvalues','PK_GAM_CUSTOM_CRITERIA')]:assert len({r[pk] for r in sets[k]})==len(sets[k])
loan=[r for r in sets['adgroup'] if 'loan' in (r.get('CAMPAIGN_NAME') or '').lower()];assert sum((D(str(r['REVENUE'])) for r in loan),D(0))==0
op=json.loads((root/'work/sb-eggbev-1547598180990976100/url-period.json').read_text())['data'];classes=defaultdict(set);slots=set()
for r in op:
 classes[(r['date'],r['slot_id'])].add(r['vertical'])
 if r['vertical']=='emp':slots.add(r['slot_id'])
exclusive=[r for r in sets['gam-keyvalues'] if classes.get((r['DATE'][:10],r['SLOT_ID']))=={'emp'}];assert not exclusive
v=json.loads((root/'work/sb-eggbev-1547598180990976100/vertical-period.json').read_text())['data'];origins=defaultdict(lambda:D(0))
for r in v:
 if r['VERTICAL']=='emp':origins[(r['SOURCE'],r.get('UTM_MEDIUM',''))]+=D(str(r['REVENUE']))
assert sum(origins.values(),D(0))==D('28.32')
report=sys.argv[1] if len(sys.argv)>1 else None
if report:
 spec=importlib.util.spec_from_file_location('poster',root/'scripts/discord-bot-post.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.load_env(mod.DEFAULT_ENV);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
 with urlopen(Request(f'https://discord.com/api/v10/channels/1498132022634483894/messages/{report}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'}),timeout=30) as res:msg=json.loads(res.read())
 assert msg['content']=='' and not msg['mentions'] and len(msg['embeds'])==1 and '1547601740734664766' in str(msg['embeds'][0]['fields'])
summary={'status':'investigated_attribution_unresolved','counts':{k:len(v) for k,v in sets.items()},'scope_and_primary_keys_verified':True,'emp_ad_slots':len(slots),'exclusive_emp_campaign_slot_matches':len(exclusive),'loan_named_adgroup_revenue':0,'emp_origins':[{'source':k[0],'medium':k[1],'revenue':str(v)} for k,v in sorted(origins.items())],'report_infra_message_id':report,'report_readback':bool(report),'financial_writes':False}
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
skill=Path('/root/.hermes/profiles/zeus/skills/ops/smartbidding-dashboard-map/references');assert 'gam_custom_criteria' in (skill/'gam-keyvalue-campaign-attribution-limits.md').read_text()
paths=sorted([p for p in P.iterdir() if p.is_file()]+[root/'data/agent-checkpoints.json',skill/'gam-keyvalue-campaign-attribution-limits.md',skill/'route-pack-02.md'])
entry={'id':ident,'agent':'zeus','authorization_message_id':'1547601740734664766','thread_id':'1545426987756298340','updated_at':datetime.now(timezone.utc).isoformat(),'type':'read_only_campaign_attribution_investigation','evidence_directory':str(P),'summary':summary,'report_infra_pending':not bool(report),'paths':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in paths]}
p=root/'data/infra-inventory.json'
with (root/'data/.infra-inventory.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);d=json.loads(p.read_text());a=d.setdefault('runtime_artifacts',[]);a[:]=[r for r in a if r.get('id')!=ident];a.append(entry);tmp=p.with_name(p.name+'.campaign.tmp')
 with tmp.open('w') as o:json.dump(d,o,ensure_ascii=False,indent=2);o.write('\n');o.flush();os.fsync(o.fileno())
 tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p);assert next(r for r in json.loads(p.read_text())['runtime_artifacts'] if r.get('id')==ident)==entry
with (root/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':entry['updated_at'],'agent':'zeus','event':'eggbev_campaign_attribution_investigation','authorization_message_id':'1547601740734664766','summary':summary},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(summary,ensure_ascii=False))
