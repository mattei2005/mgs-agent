"""Inventory, audit and verify the published monthly payroll revision."""
import pathlib,json,datetime,hashlib,fcntl,os
from decimal import Decimal as D
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';AUTH='1546380179654451281';STATE=APP/('private/payroll-'+AUTH)
checks={n:json.loads((STATE/n).read_text()) for n in ['local-integration.json','local-browser.json','public-browser.json','pg-exercise.json','production-readback.json','deploy-evidence.json']}
assert all(v['pass'] for v in checks.values())
periods=checks['production-readback.json']['periods'];assert len(periods)==len({p['id'] for p in periods})==17
sep=next(p for p in periods if p['period']=='2026-09');assert sum(abs(D(p['brl'])) for p in sep['personnel'])==D(32000)
assert '# pass 19' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text();assert 'Ran 32 tests' in (STATE/'python-tests.log').read_text() and '\nOK' in (STATE/'python-tests.log').read_text()
files=['expenses.py','worker.py','workspace.mjs','public/app.js','payroll.mjs','deploy/apply-payroll.mjs','deploy/payroll-preflight.py','deploy/payroll-release.py','deploy/record-payroll-inventory.py','tests/test_payroll_policy.py','tests/payroll-integration.mjs','tests/payroll-browser.mjs','tests/run-payroll-public.py']
paths=[APP/f for f in files]+[ROOT/'docs/finance-system-product-direction.md',ROOT/('reports/finance-payroll-'+AUTH+'.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/trial-payroll-review.md')]
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
entry={'id':'zeus-finance-payroll-'+AUTH,'agent':'zeus','type':'financial_application_payroll_policy','owner':'Rodolfo / Zeus','authorization_message_id':AUTH,'thread_id':'1545426987756298340','status':'published_validated','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-payroll-'+AUTH+'.md','evidence_path':str(STATE),'tests':{'node':19,'python':32,'viewports':[390,768,1440],'js_errors':0,'periods':len(periods),'roles_per_month':12,'real_pg_readback':True,'production_test_writes':0},'runtime':checks['deploy-evidence.json'],'known_gaps':['Other 1546212978121117706 parameter/account requests pending','Rafael/Gustavo activation requires explicit result mapping','Full native product migration and Sheet cutover not complete'],'retained_artifacts':{'isolated_database':'mgs_finance_payroll_'+AUTH,'staging':'/var/tmp/mgs-finance-payroll-'+AUTH,'evidence':str(STATE),'backup':checks['deploy-evidence.json']['backup']},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
p=ROOT/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);inv=json.loads(p.read_text());items=inv.setdefault('runtime_artifacts',[]);idx=next((i for i,x in enumerate(items) if x.get('id')==entry['id']),None)
 if idx is None:items.append(entry)
 else:items[idx]=entry
 for artifact in paths:
  if artifact.suffix not in ['.py','.mjs','.js']:continue
  stat=artifact.stat();meta={'path':str(artifact),'size_bytes':stat.st_size,'modified_at':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),'sha256':entry['files'][str(artifact)],'description':'Finance payroll '+AUTH};items=inv.setdefault('scripts',[]);idx=next((i for i,x in enumerate(items) if x.get('path')==str(artifact)),None)
  if idx is None:items.append(meta)
  else:items[idx]=meta
 inv['_meta']['updated_at']=now;tmp=p.with_suffix('.payroll-update.tmp')
 with tmp.open('w') as f:json.dump(inv,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_payroll_validated','authorization':AUTH,'inventory_id':entry['id'],'report':entry['report_path'],'sheets_writes':0,'production_test_financial_writes':0},ensure_ascii=False)+'\n')
summary={'pass':True,'inventory_readback':True,'inventory_id':entry['id'],'tests':entry['tests'],'september_payroll_brl':'32000','full_product_open':True,'report':entry['report_path']}
(STATE/'final-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
