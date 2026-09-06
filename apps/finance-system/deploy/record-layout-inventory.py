"""Inventory and audit the verified static finance layout revision only."""
import pathlib,json,datetime,hashlib,fcntl,os
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';AUTH='1546158286506561578';STATE=APP/('private/ui-layout-'+AUTH)
checks={n:json.loads((STATE/n).read_text()) for n in ['allocation-audit.json','native-allocation-gap.json','local-browser-evidence.json','public-browser-evidence.json','local-sync-evidence.json','public-sync-evidence.json','deploy-evidence.json']}
assert all(v['pass'] for v in checks.values() if 'pass' in v)
assert checks['local-sync-evidence.json']['other_screen_change_observed']
assert not checks['native-allocation-gap.json']['native_extra_redistributes_to_segments']
assert '# pass 17' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text()
assert 'Ran 20 tests' in (STATE/'python-tests.log').read_text()
files=['public/app.js','public/refinements.css','tests/audit-allocation-live.py','tests/sync-browser.mjs','tests/run-layout-public.py','tests/ui-layout.test.mjs','tests/ui-browser.mjs','tests/ui-country-blocks.test.mjs','deploy/record-layout-inventory.py']
paths=[APP/f for f in files]+[ROOT/'docs/finance-system-product-direction.md',ROOT/('reports/finance-ui-layout-'+AUTH+'.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/ui-redesign-and-quote-lifecycle.md')]
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
entry={'id':'zeus-finance-ui-layout-'+AUTH,'agent':'zeus','type':'financial_application_ui_and_audit','owner':'Rodolfo / Zeus','authorization_message_id':AUTH,'thread_id':'1545426987756298340','status':'published_validated_native_allocation_gap_open','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-ui-layout-'+AUTH+'.md','evidence_path':str(STATE),'tests':{'node':17,'python':20,'viewports':[390,768,1440],'js_errors':0,'allocation_blocks':len(checks['allocation-audit.json']['allocation_checks']),'manual_refresh_http':200,'two_screen_isolated_test':True},'runtime':checks['deploy-evidence.json'],'scope':['1','2','3','4','5','5.1','6','7','8'],'known_gap':'No native active-status UI or redistribution of extra company expenses to segments/imported manager results','files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
p=ROOT/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);inv=json.loads(p.read_text());items=inv.setdefault('runtime_artifacts',[]);idx=next((i for i,x in enumerate(items) if x.get('id')==entry['id']),None)
 if idx is None:items.append(entry)
 else:items[idx]=entry
 for artifact in paths:
  if artifact.suffix not in ['.py','.mjs','.js']:continue
  stat=artifact.stat();meta={'path':str(artifact),'size_bytes':stat.st_size,'modified_at':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),'sha256':entry['files'][str(artifact)],'description':'Finance layout/refresh/allocation audit '+AUTH};items=inv.setdefault('scripts',[]);idx=next((i for i,x in enumerate(items) if x.get('path')==str(artifact)),None)
  if idx is None:items.append(meta)
  else:items[idx]=meta
 inv['_meta']['updated_at']=now;tmp=p.with_suffix('.layout-update.tmp')
 with tmp.open('w') as f:json.dump(inv,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);assert next(x for x in json.loads(p.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_layout_refresh_validated','authorization':AUTH,'inventory_id':entry['id'],'report':entry['report_path'],'native_allocation_gap':entry['known_gap'],'sheets_writes':0,'public_financial_writes':0},ensure_ascii=False)+'\n')
summary={'pass':True,'inventory_readback':True,'inventory_id':entry['id'],'scope':entry['scope'],'tests':entry['tests'],'native_allocation_gap_open':True,'public_financial_writes':0,'report':entry['report_path']}
assert len(summary['scope'])==9
(STATE/'final-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
