"""Bounded code + month/catalog rollout. No credentials/grants/Sheets/Meta writes."""
import sys,pathlib,json,hashlib,shlex,tarfile,io,argparse,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--publish',action='store_true');a=p.parse_args()
AUTH='1546184035921829938';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STATE=ROOT/('private/ui-periods-'+AUTH);BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE=TARGET+'/private/stage-periods-'+AUTH;DB='mgs_finance_periods_'+AUTH;NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node'
FILES=['server.mjs','worker.py','workspace.mjs','site_catalog.py','domain.py','periods.py','periods.mjs','accounts.mjs','public/index.html','public/app.js','public/refinements.css','deploy/register-periods.mjs'];NEW=['periods.py','periods.mjs','accounts.mjs','deploy/register-periods.mjs'];OLD=[f for f in FILES if f not in NEW];MANIFEST=ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json';manifest=json.loads(MANIFEST.read_text());expected={f:None if f in NEW else manifest['files'].get(f) or hashlib.sha256((STATE/'before'/f).read_bytes()).hexdigest() for f in FILES}
def hashes():
 code='import pathlib,hashlib,json;p=pathlib.Path('+repr(TARGET)+');print(json.dumps({f:(hashlib.sha256((p/f).read_bytes()).hexdigest() if (p/f).exists() else None) for f in '+repr(FILES)+'}))'
 return json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))
def runseed(directory,database,exercise=False):
 result=ssh('sudo -n -u '+('mgs_pg' if exercise else 'mgsfinance')+' env FINANCE_REGISTER_DATABASE='+database+' '+(directory+'/node' if exercise else NODE)+' '+directory+'/deploy/register-periods.mjs'+(' --exercise' if exercise else ''),timeout=600)
 return json.loads(result.strip().splitlines()[-1])
local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
assert hashes()==expected,'Concurrent code change: reconcile before writing'
for f in ['periods-api-evidence.json','local-periods-browser-evidence.json']:assert json.loads((STATE/f).read_text())['pass']
assert '# pass 19' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text();assert 'Ran 26 tests' in (STATE/'python-tests.log').read_text() and '\nOK' in (STATE/'python-tests.log').read_text()
print('Preflight PASS',flush=True)
if a.prepare:
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
 baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip();ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for name in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180),validate=True);(STATE/name).write_bytes(data);(STATE/name).chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h;backup[name]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB);ssh(pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180)
 assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
 payload=io.BytesIO();seed_names=['accounts-to-register.json','account-slot-checklist.json','meta-accounts-live.json']
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for f in FILES:t.add(ROOT/f,arcname=f)
  for f in ['calc.py','expenses.py','ui_model.py','storage.mjs']:t.add(ROOT/f,arcname=f)
  for f in seed_names:t.add(STATE/f,arcname='private/period-seed-'+AUTH+'/'+f)
 ssh('sudo -n -u mgsfinance mkdir '+STAGE+' && sudo -n -u mgsfinance tar -xzf - -C '+STAGE,payload.getvalue(),timeout=90)
 ssh('sudo -n -u mgsfinance ln -s '+TARGET+'/node_modules '+STAGE+'/node_modules && sudo -n -u mgsfinance ln -s '+TARGET+'/private/source.json '+STAGE+'/private/source.json && sudo -n -u mgsfinance ln -s '+TARGET+'/private/ui-model.json '+STAGE+'/private/ui-model.json')
 assert hashes()==expected
 iso='/var/tmp/mgs-finance-periods-'+AUTH
 code='import shutil,pathlib,os,pwd;src='+repr(STAGE)+';dst='+repr(iso)+';shutil.copytree(src,dst,symlinks=False);shutil.copy2('+repr(NODE)+',dst+"/node");u=pwd.getpwnam("mgs_pg");[(os.chown(p,u.pw_uid,u.pw_gid)) for p in [pathlib.Path(dst),*pathlib.Path(dst).rglob("*")]];os.chmod(dst,0o700)'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180)
 result=runseed(iso,DB,True);assert result['pass'] and result['isolated_crud'] and len(result['periods'])==17 and result['accounts']==78
 (STATE/'pg-periods-evidence.json').write_text(json.dumps(result,indent=2));(STATE/'prepared.json').write_text(json.dumps({'pass':True,'files':local,'expected':expected,'backup_hashes':backup,'baseline':baseline,'stage':STAGE,'isolated_database':DB},indent=2));print(json.dumps({'prepared':True,'isolated_pg_months':17,'accounts':78,'production_test_writes':0}),flush=True)
if a.publish:
 prepared=json.loads((STATE/'prepared.json').read_text());assert prepared['files']==local and prepared['expected']==expected
 code='import pathlib,hashlib;p=pathlib.Path('+repr(STAGE)+');expected='+repr(local)+';assert all(hashlib.sha256((p/f).read_bytes()).hexdigest()==h for f,h in expected.items())';ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code))
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.service',timeout=90)
  code='import pathlib,shutil,os;t=pathlib.Path('+repr(TARGET)+');s=pathlib.Path('+repr(STAGE)+');files='+repr(FILES)+';[(shutil.copy2(s/f,t/f),os.chmod(t/f,0o600)) for f in files];shutil.copytree(s/'+repr('private/period-seed-'+AUTH)+',t/'+repr('private/period-seed-'+AUTH)+')'
  ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code));ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=90);assert hashes()==local
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl restart mgs-finance-dash.service',timeout=90);assert all(hashes()[f]==expected[f] for f in OLD);(STATE/'rollback.json').write_text(json.dumps({'restored':True}));raise
 manifest['files'].update(local);MANIFEST.write_text(json.dumps(manifest,indent=2))
 result=runseed(TARGET,'mgs_finance');assert result['pass'] and len(result['periods'])==17 and result['accounts']==78
 services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 assert ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()==prepared['baseline'];assert hashes()==local
 (STATE/'production-readback.json').write_text(json.dumps(result,indent=2));(STATE/'deploy-evidence.json').write_text(json.dumps({'pass':True,'target':TARGET,'backup':BACKUP,'files':local,'services':services,'baseline_preserved':True,'months':17,'accounts':78,'production_test_writes':0},indent=2));print(json.dumps({'published':True,'months':17,'accounts':78,'services':services,'baseline_preserved':True}),flush=True)
