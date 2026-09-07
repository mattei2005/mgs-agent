"""1546607083468623912 currency release: fresh backup, restore, exact-month migration.
One-shot, never rerun completed prepare/apply. No gateway/credentials/system configs.
"""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546607083468623912';STATE=ROOT/('private/wavesbee-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE='/var/tmp/mgs-finance-currency-'+AUTH;DB='mgs_finance_currency_'+AUTH;NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';phase=sys.argv[1]
OLD=['worker.py','workspace.mjs'];FILES=OLD+['currency_bridge.py','currency-migration.mjs','deploy/apply-currency.mjs'];local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def save(name,obj):(STATE/name).write_text(json.dumps(obj,indent=2))
if phase=='prepare':
 assert not (STATE/'prepared.json').exists()
 expected=hashes(TARGET,OLD);oldstate=ROOT/'private/networks-1546579646227943506';e=json.loads((oldstate/'deploy-evidence.json').read_text())['files'];v=json.loads((oldstate/'v2-published.json').read_text())['files'];assert expected=={'worker.py':v['worker.py'],'workspace.mjs':e['workspace.mjs']},'Concurrent code change; reconcile before deployment'
 supporting=['calc.py','domain.py','expenses.py','ui_model.py','periods.py','site_catalog.py','networks.py','storage.mjs','server.mjs','auth.mjs','accounts.mjs','periods.mjs','networks.mjs','network-rules.json'];remote=hashes(TARGET,supporting);assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in remote.items()),'Runtime dependency differs from production'
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
 baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for name in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180),validate=True);p=STATE/name;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h;backup[name]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB)
 ssh(pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180);assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for pattern in ['*.py','*.mjs','*-rules.json']:
   for f in ROOT.glob(pattern):t.add(f,arcname=f.name)
  for f in ['public/app.js','public/refinements.css','deploy/apply-currency.mjs']:t.add(ROOT/f,arcname=f)
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+STAGE+' && sudo -n -u mgs_pg tar -xzf - -C '+STAGE,payload.getvalue(),timeout=90)
 code='import shutil,pathlib,os,pwd;s=pathlib.Path('+repr(TARGET)+');t=pathlib.Path('+repr(STAGE)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2('+repr(NODE)+',t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(STAGE,FILES)==local
 save('prepared.json',{'pass':True,'backup':backup,'baseline':baseline,'expected':expected,'files':local,'stage':STAGE,'database':DB});print('Fresh backups, second-copy hashes, isolated PostgreSQL restore PASS')
elif phase=='exercise':
 assert hashes(STAGE,FILES)==local
 print(ssh('sudo -n -u mgs_pg env FINANCE_CURRENCY_DATABASE='+DB+' '+STAGE+'/node '+STAGE+'/deploy/apply-currency.mjs --exercise',timeout=240))
 d=json.loads(ssh('sudo -n -u mgs_pg python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(STAGE+'/private/wavesbee-'+AUTH+'/db-readback.json')+').read_text())')));assert d['pass'];save('pg-exercise.json',d)
elif phase=='publish':
 prepared=json.loads((STATE/'prepared.json').read_text());assert hashes(TARGET,OLD)==prepared['expected'] and hashes(STAGE,FILES)==local
 assert json.loads((STATE/'pg-exercise.json').read_text())['pass'];assert 'Ran 38 tests' in (STATE/'python-tests.log').read_text() and '\nOK' in (STATE/'python-tests.log').read_text();assert '# pass 25' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text()
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.service',timeout=60)
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");[(shutil.copy2(s/f,t/f),os.chown(t/f,u.pw_uid,u.pw_gid),os.chmod(t/f,0o600)) for f in '+repr(FILES)+']'
  ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET,FILES)==local
  # Migration while the app is stopped; existing session and quote data are preserved.
  print(ssh('sudo -n -u mgsfinance env FINANCE_CURRENCY_DATABASE=mgs_finance '+NODE+' '+TARGET+'/deploy/apply-currency.mjs',timeout=240));ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=60)
 except Exception:
  # Do not restore whole DB or code over a partially committed migration blindly.
  ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=60);save('publication-failure.json',{'requires_review':True,'backup':BACKUP});raise
 d=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(TARGET+'/private/wavesbee-'+AUTH+'/db-readback.json')+').read_text())')));assert d['pass'];save('production-readback.json',d);save('published.json',{'pass':True,'files':local});print('Published and migrated only August/September; independent database readback PASS')
elif phase=='verify':
 assert hashes(TARGET,FILES)==local
 print(ssh('sudo -n -u mgsfinance env FINANCE_CURRENCY_DATABASE=mgs_finance '+NODE+' '+TARGET+'/deploy/apply-currency.mjs --verify',timeout=150))
 services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3;assert ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()==json.loads((STATE/'prepared.json').read_text())['baseline'];save('deploy-readback.json',{'pass':True,'services':services,'files':local,'backup':BACKUP,'baseline_preserved':True});print('Production services/code/baseline verification PASS')
else:raise ValueError('Unknown phase')
