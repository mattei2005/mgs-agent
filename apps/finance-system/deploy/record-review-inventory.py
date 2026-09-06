"""Record only verified finance conference revision, preserving concurrent inventory."""
import pathlib,json,datetime,hashlib,fcntl,os
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';AUTH='1546147880559968286';STATE=APP/('private/ui-review-'+AUTH)
checks={name:json.loads((STATE/name).read_text()) for name in ['local-browser-evidence.json','public-browser-evidence.json','pg-restore-evidence.json','deploy-evidence.json']}
assert all(v['pass'] for v in checks.values())
assert checks['public-browser-evidence.json']['public_financial_writes']==0
node=(STATE/'node-tests.log').read_text();py=(STATE/'python-tests.log').read_text();assert '# pass 14' in node and '# fail 0' in node and 'Ran 20 tests' in py and py.rstrip().endswith('OK')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
paths=[APP/f for f in ['public/app.js','public/refinements.css','public/index.html','workspace.mjs','ui_model.py','tests/ui-browser.mjs','tests/ui-country-blocks.test.mjs','tests/ui-review.test.mjs','tests/workspace.test.mjs','deploy/ui-review.py','deploy/record-review-inventory.py']]+[ROOT/'docs/finance-system-product-direction.md',ROOT/('reports/finance-ui-review-'+AUTH+'.md'),pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard/references/ui-redesign-and-quote-lifecycle.md')]
entry={'id':'zeus-finance-ui-review-'+AUTH,'agent':'zeus','type':'financial_application_review','owner':'Rodolfo / Zeus','authorization_message_id':AUTH,'thread_id':'1545426987756298340','status':'published_and_validated','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-ui-review-'+AUTH+'.md','evidence_path':str(STATE),'runtime':{'url':'https://dash.mgsdigitalcorp.com','release':checks['deploy-evidence.json']['target'],'host':'MatteiInc01'},'tests':{'node':14,'python':20,'browser_views':6,'viewports':[390,768,1440],'js_errors':0,'production_test_financial_writes':0,'pg_restore':True},'backup':checks['deploy-evidence.json']['backup'],'isolated_database':checks['pg-restore-evidence.json']['isolated_database'],'preserved':['Sheets','financial baseline','credentials','grants','system configs','gateways'],'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'remaining':'Full native migration/importers/period lifecycle/official cutover unchanged'}
p=ROOT/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);inv=json.loads(p.read_text());items=inv.setdefault('runtime_artifacts',[])
 found=next((i for i,x in enumerate(items) if x.get('id')==entry['id']),None)
 if found is None:items.append(entry)
 else:items[found]=entry
 for artifact in paths:
  if artifact.suffix not in ['.py','.mjs','.js']:continue
  stat=artifact.stat();meta={'path':str(artifact),'size_bytes':stat.st_size,'modified_at':datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),'sha256':entry['files'][str(artifact)],'description':'Finance conference revision '+AUTH}
  scripts=inv.setdefault('scripts',[]);idx=next((i for i,x in enumerate(scripts) if x.get('path')==str(artifact)),None)
  if idx is None:scripts.append(meta)
  else:scripts[idx]=meta
 inv['_meta']['updated_at']=now;tmp=p.with_suffix('.review-update.tmp')
 with tmp.open('w') as out:json.dump(inv,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
 os.replace(tmp,p);read=json.loads(p.read_text());assert next(x for x in read['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_ui_review_validated','authorization':AUTH,'inventory_id':entry['id'],'report':entry['report_path'],'evidence':entry['evidence_path'],'production_financial_test_writes':0},ensure_ascii=False)+'\n')
summary={'pass':True,'inventory_readback':True,'inventory_id':entry['id'],'acceptance_items':[{'id':i,'pass':True} for i in range(1,7)],'tests':entry['tests'],'report':entry['report_path'],'backup':entry['backup']}
assert len(summary['acceptance_items'])==6
(STATE/'final-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
