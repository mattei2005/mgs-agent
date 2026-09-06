"""Inventory and audit the verified monthly catalog/allocation revision."""
import pathlib,json,datetime,hashlib,fcntl,os
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';AUTH='1546184035921829938';STATE=APP/('private/ui-periods-'+AUTH)
checks={n:json.loads((STATE/n).read_text()) for n in ['periods-api-evidence.json','local-periods-browser-evidence.json','public-periods-browser-evidence.json','public-browser-evidence.json','pg-periods-evidence.json','production-readback.json','deploy-evidence.json']}
assert all(v['pass'] for v in checks.values());assert len(checks['production-readback.json']['periods'])==17;assert len(set(checks['production-readback.json']['account_ids']))==78
assert '# pass 19' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text();assert 'Ran 26 tests' in (STATE/'python-tests.log').read_text()
files=['server.mjs','worker.py','workspace.mjs','site_catalog.py','domain.py','periods.py','periods.mjs','accounts.mjs','public/index.html','public/app.js','public/refinements.css','tests/test_periods.py','tests/periods-integration.mjs','tests/periods-browser.mjs','tests/inventory_meta_accounts.py','tests/catalog.test.mjs','tests/ui-browser.mjs','tests/sync-browser.mjs','tests/run-layout-public.py','deploy/ui-periods.py','deploy/register-periods.mjs','deploy/resume-periods-prepare.py','deploy/record-periods-inventory.py']
paths=[APP/f for f in files]+[ROOT/'docs/finance-system-product-direction.md',ROOT/('reports/finance-ui-periods-'+AUTH+'.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/SKILL.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/ui-redesign-and-quote-lifecycle.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/monthly-periods-and-ad-accounts.md')]
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
entry={'id':'zeus-finance-ui-periods-'+AUTH,'agent':'zeus','type':'financial_application_months_and_accounts','owner':'Rodolfo / Zeus','authorization_message_id':AUTH,'thread_id':'1545426987756298340','status':'published_validated_identity_gaps_and_full_product_open','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-ui-periods-'+AUTH+'.md','evidence_path':str(STATE),'tests':{'node':19,'python':26,'viewports':[390,768,1440],'js_errors':0,'periods':17,'new_months':16,'verified_accounts':78,'hidden_empty_slots':229,'real_pg_readback':True,'production_test_writes':0},'runtime':checks['deploy-evidence.json'],'scope':['monthly_periods','active_inactive_groups','continuity','account_catalog','empty_slot_removal','compact_monthly_rates'],'known_gaps':['Seven source account identities without unambiguous Meta ID','Full-product migration, import/source lifecycle and final sheet cutover','Complete revenue/ad-spend conference lifecycle and recurring backup/DR policy'],'retained_artifacts':{'isolated_database':'mgs_finance_periods_'+AUTH,'staging':'/home/mgsfinance/releases/pg-auth-1545934831664242748/private/stage-periods-'+AUTH,'isolated_code':'/var/tmp/mgs-finance-periods-'+AUTH,'evidence':str(STATE)},'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
p=ROOT/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);inv=json.loads(p.read_text());items=inv.setdefault('runtime_artifacts',[]);idx=next((i for i,x in enumerate(items) if x.get('id')==entry['id']),None)
 if idx is None:items.append(entry)
 else:items[idx]=entry
 for old in inv.get('runtime_artifacts',[]):
  if old.get('id')=='zeus-finance-ui-catalog-1546169687346249728':old.update(status='historical_months_accounts_gap_superseded',known_gap_status='Periods and local account CRUD delivered by '+entry['id']+'; seven identities unresolved; full product remains open',updated_at=now)
 for artifact in paths:
  if artifact.suffix not in ['.py','.mjs','.js']:continue
  stat=artifact.stat();meta={'path':str(artifact),'size_bytes':stat.st_size,'modified_at':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),'sha256':entry['files'][str(artifact)],'description':'Finance native catalog/allocation '+AUTH};items=inv.setdefault('scripts',[]);idx=next((i for i,x in enumerate(items) if x.get('path')==str(artifact)),None)
  if idx is None:items.append(meta)
  else:items[idx]=meta
 inv['_meta']['updated_at']=now;tmp=p.with_suffix('.periods-update.tmp')
 with tmp.open('w') as f:json.dump(inv,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_periods_accounts_validated','authorization':AUTH,'inventory_id':entry['id'],'report':entry['report_path'],'known_gaps':entry['known_gaps'],'sheets_writes':0,'production_test_financial_writes':0},ensure_ascii=False)+'\n')
summary={'pass':True,'inventory_readback':True,'inventory_id':entry['id'],'scope':entry['scope'],'tests':entry['tests'],'periods_and_account_crud_delivered':True,'full_product_open':True,'production_test_financial_writes':0,'report':entry['report_path']}
assert len(summary['scope'])==6
(STATE/'final-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
