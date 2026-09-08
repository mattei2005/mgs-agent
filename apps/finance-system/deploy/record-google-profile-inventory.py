"""Exact inventory/readback for Google account and contact/logo releases."""
import pathlib,json,hashlib,datetime,fcntl,os
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';P=A/'private/google-square-1546702931384991834';G=A/'private/google-accounts-1546702931384991834';K=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/mgs-finance-dashboard')
checks=[P/'square-prepared.json',P/'profile-pg-exercise.json',P/'square-published.json',P/'square-public.json',G/'prepared.json',G/'pg-exercise.json',G/'published.json',G/'public-browser.json',G/'deploy-readback.json',G/'click-hotfix.json']
assert all(json.loads(p.read_text())['pass'] for p in checks)
g=json.loads((G/'public-browser.json').read_text());assert g['registered_verified']==2 and {x['id'] for x in g['accounts']}=={'2780300411','5172498094'};assert g['financial_values_unchanged'] and g['other_accounts_preserved'] and g['js_errors']==0
p=json.loads((P/'square-public.json').read_text());assert p['owner_edit_visible'] and p['my_profile_visible'] and p['users_last'] and p['js_errors']==0
assert '# pass 44' in (G/'node-tests.log').read_text();assert 'Ran 43 tests' in (P/'python-tests.log').read_text();assert 'version: 0.1.27' in (K/'SKILL.md').read_text()
files=['google_ads_inventory.py','google-lookup.mjs','meta-lookup-worker.py','accounts.mjs','finance-ops.mjs','deploy/meta-lookup-queue.py','public/app.js','public/navigation.js','public/navigation.css','public/login.html','public/login.css','public/refinements.css','public/operations.js','public/mgs-logo.png','deploy/build-brand-assets.py','deploy/square-logo-release.py','deploy/google-accounts-release.py','deploy/record-google-profile-inventory.py','tests/test_square_logo.py','tests/self-profile.test.mjs','tests/self-profile-pg.mjs','tests/square-logo-browser.mjs','tests/google-account.test.mjs','tests/google-accounts-pg.mjs','tests/google-accounts-browser.mjs']
paths=[A/f for f in files]+[R/'docs/finance-system-product-direction.md',R/'reports/finance-google-profile-square-1546702931384991834.md',K/'SKILL.md',K/'references/google-mcc-self-profile-square-logo.md',K/'references/billing-origin-meta-id-and-brand.md'];assert len(paths)==len(set(paths))
now=datetime.datetime.now(datetime.timezone.utc).isoformat();entry={'id':'zeus-finance-google-profile-square-1546702931384991834','agent':'zeus','type':'finance_google_accounts_profiles_brand','authorization_message_ids':['1546702931384991834','1546703031033405501','1546705557996699699'],'thread_id':'1545426987756298340','status':'published_verified','updated_at':now,'canonical_source':'docs/finance-system-product-direction.md','report_path':'reports/finance-google-profile-square-1546702931384991834.md','scope':{'google_accounts_registered':g['accounts'],'mcc':'8137016595','discovery':'on_demand_mcc_readonly','spend_import_active':False,'financial_values_changed':False,'sheet_writes':0,'google_platform_mutations':0,'credentials_changed':0,'real_users_created':0,'schema_grants_changed':0,'gateway_restart':False,'nicolas_only_pilot':True,'self_contact_edit':True,'owner_contact_edit':True,'users_last':True,'logo_complete_square':True},'tests':{'profile_node':41,'python':43,'google_node_before_hotfix':44,'focused_google_after_hotfix':4,'pg_real_google_meta_queue':True,'public_browser':True,'js_errors':0},'backup_roots':['/home/zeus/mgs-finance-backups/1546703031033405501','/home/zeus/mgs-finance-backups/1546702931384991834'],'evidence_paths':[str(P),str(G)],'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
inv=R/'data/infra-inventory.json'
with open('/var/lock/infra_discovery.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);d=json.loads(inv.read_text());items=d.setdefault('runtime_artifacts',[]);idx=next((i for i,v in enumerate(items) if v.get('id')==entry['id']),None)
 if idx is None:items.append(entry)
 else:items[idx]=entry
 for f in paths:
  if f.suffix not in ['.py','.js','.mjs']:continue
  scripts=d.setdefault('scripts',[]);row={'path':str(f),'size_bytes':f.stat().st_size,'sha256':entry['files'][str(f)],'modified_at':now,'description':'Finance Google/profile/square 1546702931384991834'};idx=next((i for i,x in enumerate(scripts) if x.get('path')==str(f)),None)
  if idx is None:scripts.append(row)
  else:scripts[idx]=row
 d['_meta']['updated_at']=now;t=inv.with_suffix('.google-profile.tmp')
 with t.open('w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,inv);fd=os.open(inv.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd);assert next(x for x in json.loads(inv.read_text())['runtime_artifacts'] if x.get('id')==entry['id'])==entry
with (R/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':now,'agent':'zeus','event':'finance_google_profile_square_verified','authorization_message_ids':entry['authorization_message_ids'],'inventory_id':entry['id'],'scope':entry['scope'],'report':entry['report_path']})+'\n');f.flush();os.fsync(f.fileno())
out={'pass':True,'inventory_id':entry['id'],'files':len(paths),'accounts_verified':g['registered_verified'],'skill_version':'0.1.27','readback':True};(G/'final-inventory.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
