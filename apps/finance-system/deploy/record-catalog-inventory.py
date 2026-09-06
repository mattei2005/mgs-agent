"""Inventory and audit the verified monthly catalog/allocation revision."""
import pathlib,json,datetime,hashlib,fcntl,os
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';AUTH='1546169687346249728';STATE=APP/('private/ui-catalog-'+AUTH)
checks={n:json.loads((STATE/n).read_text()) for n in ['catalog-api-evidence.json','local-browser-evidence.json','public-browser-evidence.json','remote-canary-evidence.json','catalog-pg-evidence.json','manager-allocation-evidence.json','pg-restore-evidence.json','deploy-evidence.json']}
assert all(v['pass'] for v in checks.values() if 'pass' in v)
assert checks['catalog-pg-evidence.json']['readback']['allocation_matches']
assert checks['manager-allocation-evidence.json']['independent_payroll_formula']
assert '# pass 19' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text()
assert 'Ran 23 tests' in (STATE/'python-tests.log').read_text()
files=['server.mjs','worker.py','workspace.mjs','site_catalog.py','public/index.html','public/app.js','public/refinements.css','tests/catalog.test.mjs','tests/test_site_catalog.py','tests/verify_manager_allocation.py','tests/ui-browser.mjs','tests/workspace.test.mjs','deploy/ui-catalog.py','deploy/verify-catalog-pg.py','deploy/record-catalog-inventory.py']
paths=[APP/f for f in files]+[ROOT/'docs/finance-system-product-direction.md',ROOT/('reports/finance-ui-catalog-'+AUTH+'.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/ui-redesign-and-quote-lifecycle.md')]
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
entry={'id':'zeus-finance-ui-catalog-'+AUTH,'agent':'zeus','type':'financial_application_native_catalog_and_allocation','owner':'Rodolfo / Zeus','authorization_message_id':AUTH,'thread_id':'1545426987756298340','status':'published_validated_full_product_open','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-ui-catalog-'+AUTH+'.md','evidence_path':str(STATE),'tests':{'node':19,'python':23,'viewports':[390,768,1440],'js_errors':0,'legacy_sites':41,'legacy_units':43,'native_catalog_crud':True,'real_pg_json_readback':True,'independent_payroll_check':True},'runtime':checks['deploy-evidence.json'],'scope':['1','2','3','4','5','6'],'known_gaps':['Additional native periods / September opening','Ad-account create/rename lifecycle','Full-product migration and final sheet cutover'],'retained_artifacts':{'isolated_database':checks['catalog-pg-evidence.json']['isolated_database'],'staging':'/home/mgsfinance/releases/pg-auth-1545934831664242748/private/stage-review-'+AUTH,'evidence':str(STATE)},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
p=ROOT/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);inv=json.loads(p.read_text());items=inv.setdefault('runtime_artifacts',[]);idx=next((i for i,x in enumerate(items) if x.get('id')==entry['id']),None)
 if idx is None:items.append(entry)
 else:items[idx]=entry
 for old in inv.get('runtime_artifacts',[]):
  if old.get('id')=='zeus-finance-ui-layout-1546158286506561578':old.update(status='historical_allocation_gap_superseded',known_gap_status='Resolved for site/status/company-extra allocation scope by '+entry['id'],updated_at=now)
 for artifact in paths:
  if artifact.suffix not in ['.py','.mjs','.js']:continue
  stat=artifact.stat();meta={'path':str(artifact),'size_bytes':stat.st_size,'modified_at':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),'sha256':entry['files'][str(artifact)],'description':'Finance native catalog/allocation '+AUTH};items=inv.setdefault('scripts',[]);idx=next((i for i,x in enumerate(items) if x.get('path')==str(artifact)),None)
  if idx is None:items.append(meta)
  else:items[idx]=meta
 inv['_meta']['updated_at']=now;tmp=p.with_suffix('.catalog-update.tmp')
 with tmp.open('w') as f:json.dump(inv,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_catalog_allocation_validated','authorization':AUTH,'inventory_id':entry['id'],'report':entry['report_path'],'known_gaps':entry['known_gaps'],'sheets_writes':0,'public_financial_writes':0},ensure_ascii=False)+'\n')
summary={'pass':True,'inventory_readback':True,'inventory_id':entry['id'],'scope':entry['scope'],'tests':entry['tests'],'native_allocation_gap_closed':True,'full_product_open':True,'public_financial_writes':0,'report':entry['report_path']}
assert len(summary['scope'])==6
(STATE/'final-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
