"""Bounded finance payroll release; only finance app service, no gateway."""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','exercise','publish','migrate','verify']);a=p.parse_args()
AUTH='1546380179654451281';STATE=ROOT/('private/payroll-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE='/var/tmp/mgs-finance-payroll-'+AUTH;DB='mgs_finance_payroll_'+AUTH;NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node'
FILES=['expenses.py','worker.py','workspace.mjs','public/app.js','payroll.mjs','deploy/apply-payroll.mjs'];OLD=FILES[:4];expected=json.loads((STATE/'expected.json').read_text());local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
def hashes(target,files):
 code='import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
 return json.loads(ssh('sudo -n python3 -c '+shlex.quote(code)))
def save(name,obj): (STATE/name).write_text(json.dumps(obj,indent=2))
if a.phase=='prepare':
 assert hashes(TARGET,OLD)==expected
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
 baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for name in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180),validate=True);(STATE/name).write_bytes(data);(STATE/name).chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h;backup[name]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB)
 ssh(pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180)
 assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for f in list(ROOT.glob('*.py'))+list(ROOT.glob('*.mjs')):t.add(f,arcname=f.name)
  for f in ['public/app.js','deploy/apply-payroll.mjs']:t.add(ROOT/f,arcname=f)
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+STAGE+' && sudo -n -u mgs_pg tar -xzf - -C '+STAGE,payload.getvalue(),timeout=90)
 code='import shutil,pathlib,os,pwd;s=pathlib.Path('+repr(TARGET)+');t=pathlib.Path('+repr(STAGE)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2('+repr(NODE)+',t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180)
 assert hashes(STAGE,FILES)==local
 save('prepared.json',{'pass':True,'backup':backup,'baseline':baseline,'local':local,'stage':STAGE,'database':DB});print('Backup, second copy and isolated restore PASS')
elif a.phase=='exercise':
 assert hashes(STAGE,FILES)==local
 print(ssh('sudo -n -u mgs_pg env FINANCE_PAYROLL_DATABASE='+DB+' '+STAGE+'/node '+STAGE+'/deploy/apply-payroll.mjs --exercise',timeout=600),flush=True)
 d=json.loads(ssh('sudo -n -u mgs_pg python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(STAGE+'/private/payroll-'+AUTH+'/pg-readback.json')+').read_text())')));assert d['pass'];save('pg-exercise.json',d)
elif a.phase=='publish':
 assert json.loads((STATE/'local-integration.json').read_text())['pass']
 assert json.loads((STATE/'local-browser.json').read_text())['pass']
 assert json.loads((STATE/'pg-exercise.json').read_text())['pass']
 assert hashes(TARGET,OLD)==expected and hashes(STAGE,FILES)==local
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.service',timeout=90)
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");[(shutil.copy2(s/f,t/f),os.chown(t/f,u.pw_uid,u.pw_gid),os.chmod(t/f,0o600)) for f in '+repr(FILES)+']'
  ssh('sudo -n python3 -c '+shlex.quote(code));ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=90)
  assert hashes(TARGET,FILES)==local
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl restart mgs-finance-dash.service',timeout=90);assert hashes(TARGET,OLD)==expected;save('code-rollback.json',{'restored':True});raise
 save('published-code.json',{'pass':True,'files':local});print('Code published, data migration still pending')
elif a.phase=='migrate':
 assert hashes(TARGET,FILES)==local
 print(ssh('sudo -n -u mgsfinance env FINANCE_PAYROLL_DATABASE=mgs_finance '+NODE+' '+TARGET+'/deploy/apply-payroll.mjs',timeout=600),flush=True)
 d=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(TARGET+'/private/payroll-'+AUTH+'/pg-readback.json')+').read_text())')));assert d['pass'];save('production-readback.json',d)
elif a.phase=='verify':
 assert hashes(TARGET,FILES)==local
 print(ssh('sudo -n -u mgsfinance env FINANCE_PAYROLL_DATABASE=mgs_finance '+NODE+' '+TARGET+'/deploy/apply-payroll.mjs --verify',timeout=180))
 services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 assert ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()==json.loads((STATE/'prepared.json').read_text())['baseline']
 manifest_path=ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json';m=json.loads(manifest_path.read_text());m['files'].update(local);manifest_path.write_text(json.dumps(m,indent=2))
 save('deploy-evidence.json',{'pass':True,'files':local,'services':services,'backup':BACKUP,'baseline_preserved':True});print('Production independent readback PASS')
