import json,hashlib,os,fcntl,sys,importlib.util
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal as D
from urllib.request import Request,urlopen
P=Path(__file__).parent;root=Path('/root/mgs-agent');ident='zeus-gam-compare-1547589806559731742'
s=json.loads((P/'summary.json').read_text());r=json.loads((P/'claude-reproduction.json').read_text())
assert r['all_groups_reproduced_at_six_decimals'] and r['matched_groups']==466
assert s['all_currency_day_cent_match'] and len(s['currency_days'])==18
for obj in s['manifest'].values():assert hashlib.sha256(Path(obj['path']).read_bytes()).hexdigest()==obj['sha256']
registry=json.loads((root/'data/knowledge-registry.json').read_text())
def records(x):
 if isinstance(x,dict):
  if 'canonical_key' in x:yield x
  else:
   for v in x.values():yield from records(v)
 elif isinstance(x,list):
  for v in x:yield from records(v)
rows=list(records(registry))
for key,id_ in [('finance.revenue.gam.daily-consolidation.mapping','FINANCE-GAM-DAILY-MAPPING-1547589806559731742'),('finance.revenue.traffic-strategy.suffix-semantics','FINANCE-TRAFFIC-STRATEGY-1547589806559731742')]:
 active=[v for v in rows if v['canonical_key']==key and v['status']=='active'];assert len(active)==1 and active[0]['id']==id_
canonical=root/'docs/gam-revenue-claude-yolo-september-2026.md';text=canonical.read_text();assert '`-s` = tráfego direto; `-d` = estratégia do bot.' in text and 'Escalatepower e Mavroa → `g002-d`' in text
skill=Path('/root/.hermes/profiles/zeus/skills/ops/revenue-spend-reporting-pipeline');assert 'direct traffic' in (skill/'SKILL.md').read_text() and '1547589806559731742' in (skill/'references/gam-daily-excel-consolidation.md').read_text()
report_id=sys.argv[1] if len(sys.argv)>1 else None
if report_id:
 spec=importlib.util.spec_from_file_location('poster',root/'scripts/discord-bot-post.py');poster=importlib.util.module_from_spec(spec);spec.loader.exec_module(poster);poster.load_env(poster.DEFAULT_ENV)
 token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
 req=Request(f'https://discord.com/api/v10/channels/1498132022634483894/messages/{report_id}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
 with urlopen(req,timeout=30) as response:msg=json.loads(response.read())
 assert msg['content']=='' and not msg['mentions'] and len(msg['embeds'])==1 and msg['channel_id']=='1498132022634483894'
 fields={f['name']:f['value'] for f in msg['embeds'][0]['fields']};assert '466' in fields['Evidência'] and '1547589806559731742' in fields['Motivo']
verification={'status':'PASS','source_files_unchanged':3,'claude_groups_reproduced':466,'currency_days_reconciled':18,'canonical_decisions_readback':True,'skill_readback':True,'financial_writes':False,'report_infra_message_id':report_id,'report_infra_verified':bool(report_id)}
(P/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2))
paths=sorted([p for p in P.iterdir() if p.is_file()]+[canonical,root/'data/knowledge-registry.json',root/'data/agent-checkpoints.json',skill/'SKILL.md',skill/'references/gam-daily-excel-consolidation.md'])
entry={'id':ident,'agent':'zeus','authorization_message_id':'1547589806559731742','thread_id':'1545426987756298340','type':'financial_comparison_and_confirmed_mapping','updated_at':datetime.now(timezone.utc).isoformat(),'evidence_directory':str(P),'paths':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in paths],'verification':verification,'report_infra_pending':not bool(report_id)}
p=root/'data/infra-inventory.json'
with (root/'data/.infra-inventory.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);data=json.loads(p.read_text());artifacts=data.setdefault('runtime_artifacts',[]);artifacts[:]=[x for x in artifacts if x.get('id')!=ident];artifacts.append(entry)
 tmp=p.with_name(p.name+'.gam-comparison.tmp')
 with tmp.open('w') as o:json.dump(data,o,ensure_ascii=False,indent=2);o.write('\n');o.flush();os.fsync(o.fileno())
 tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p);assert next(v for v in json.loads(p.read_text())['runtime_artifacts'] if v.get('id')==ident)==entry
with (root/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':entry['updated_at'],'agent':'zeus','event':'gam_claude_compare_report_verified' if report_id else 'gam_claude_compare_and_rules_verified','authorization_message_id':'1547589806559731742','artifact_id':ident,'verification':verification},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(verification,ensure_ascii=False))
for v in s['projection_differences']['site_manager']:
 k=v['key'];print(k[-1],f"Zeus {D(v['zeus']):,.2f}",f"Claude {D(v['claude']):,.2f}")
print('BR_SMALL',sum((D(v['original_revenue']) for k,v in r['explanations'].items() if k.startswith('Placement BR')),D(0)))
