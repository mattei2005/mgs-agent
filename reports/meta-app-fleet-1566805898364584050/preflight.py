import sys,os,json,asyncio,time
from pathlib import Path
ROOT=Path('/root/.hermes/profiles/zeus/cache/scratch/meta-fleet-20261102')
SCRIPTS=Path('/root/.hermes/profiles/zeus/scripts')
def load(name,marker,stop=None):
 s=(SCRIPTS/name).read_text();a=s.index(marker);b=s.index(stop,a) if stop else s.rindex('\nPY\n');ns={'__name__':'readonly_audit'};exec(compile(s[a:b],name,'exec'),ns);return ns
if sys.argv[1]=='generic':
 ns=load('meta-app-roles-watch.sh','import importlib.util\n','\nstate = load_state()');ns['DRY_RUN']=True
 previous=ns['load_state']()['apps'];rows=ns['load_sheet_rows']();ns['load_sheet_users']()
 (ROOT/'sheet-before.json').write_text(json.dumps(rows,ensure_ascii=False))
 out=json.loads((ROOT/'generic-preflight.json').read_text()) if (ROOT/'generic-preflight.json').exists() else []
 for app,cfg in ns['ACTIVE_APP_CONFIGS'].items():
  if any(x['app_name']==app for x in out):continue
  snap=ns['build_app_snapshot'](cfg['onepassword_item_title'],previous.get(app,{}));snap['operational_roles'],snap['role_identity_reconciliation']=ns['operational_roles_for_app'](app,snap['roles'])
  assert snap['app_name']==app
  assert all(snap['checks'][k].get('ok') for k in ['app_metadata','roles']),(app,snap['checks'])
  snap['credential_health']={'valid':snap['token_info'].get('valid'),'bad_checks':{k:v for k,v in snap['checks'].items() if not v.get('ok')}}
  assert str(snap['token_info']['app_id'])==str(snap['app_id'])
  assert snap['role_identity_resolution']['unresolved_count']==0
  assigned=[r for r in rows if ns['app_key_from_sheet_value'](r.get('NO APP'))==app and not ns['is_verification_ignored_sheet_row'](r)]
  keys=set().union(*(ns['role_identity_keys'](r) for r in snap['operational_roles'])) if snap['operational_roles'] else set()
  # Canonical sheet match functions drive exact parity in separate verifier.
  snap['sheet_assigned_rows']=assigned;snap['sheet_removed']=ns['sheet_removed_roles_for_app'](app)
  out.append(snap);(ROOT/'generic-preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
  print(app,'PASS','roles',len(snap['roles']),'operational',len(snap['operational_roles']),'assigned',len(assigned),'marked',len(snap['sheet_removed']),flush=True)
elif sys.argv[1]=='b013':
 ns=load('b013-dtr-link-watch.sh','import asyncio\n');ns['DRY_RUN']=True
 config=ns['load_config']();app_token=config['app_id']+'|'+config['app_secret']
 # App credential preflight uses canonical Graph transport.
 import inspect
 print('CONFIG_OK',config['app_name'],flush=True)
 original=ns['summarize']
 def summarize(results):
  allowed=['user','segurador','profile_id','pages','linked','verdict','link_status','error','checked_at','invest_profile_names','debug_valid','accounts_status','dtr_pages','graph_pages','connected_pages']
  projected=[{k:r.get(k) for k in allowed if k in r} for r in results]
  (ROOT/'b013-preflight-results.json').write_text(json.dumps(projected,ensure_ascii=False,indent=2))
  return original(results)
 ns['summarize']=summarize
 asyncio.run(ns['main']())
