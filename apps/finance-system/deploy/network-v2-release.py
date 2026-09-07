"""Finalize manager-rate closure and Rodolfo's additional SB Rede1 assignments.
Single scoped correction on the existing finance release; no credentials/system config writes.
"""
import pathlib,json,sys,hashlib,shlex,tarfile,io,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
STATE=ROOT/'private/networks-1546579646227943506';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/1546579646227943506';STAGE='/var/tmp/mgs-finance-networks-1546579646227943506';FILES=['networks.py','worker.py','network-migration.mjs','network-rules.json'];phase=sys.argv[1];local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
def hashes(target):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,json,hashlib;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))')))
if phase=='stage':
 expected={f:json.loads((STATE/'deploy-evidence.json').read_text())['files'][f] for f in FILES};assert hashes(TARGET)==expected
 ssh('test ! -e '+BACKUP+'/code-before-network-v2.tar.gz && sudo -n tar -czf '+BACKUP+'/code-before-network-v2.tar.gz -C '+TARGET+' '+' '.join(FILES)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before-network-v2.tar.gz && chmod 600 '+BACKUP+'/code-before-network-v2.tar.gz')
 pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance';ssh(pg+' > '+BACKUP+'/finance-before-network-v2.dump && chmod 600 '+BACKUP+'/finance-before-network-v2.dump',timeout=180)
 backup={}
 for name in ['code-before-network-v2.tar.gz','finance-before-network-v2.dump']:
  value=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180),validate=True);(STATE/name).write_bytes(value);(STATE/name).chmod(0o600);h=hashlib.sha256(value).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h;backup[name]=h
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for f in FILES:t.add(ROOT/f,arcname=f)
 ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,payload.getvalue());assert hashes(STAGE)==local
 (STATE/'v2-staged.json').write_text(json.dumps({'pass':True,'expected':expected,'local':local,'backup':backup},indent=2));print('v2 staged and pre-change backup copies verified')
elif phase=='publish':
 expected=json.loads((STATE/'v2-staged.json').read_text())['expected'];assert hashes(TARGET)==expected and hashes(STAGE)==local
 assert json.loads((STATE/'pg-exercise.json').read_text())['pass'];assert json.loads((STATE/'local-browser.json').read_text())['pass'];assert 'Ran 36 tests' in (STATE/'python-tests.log').read_text() and '\nOK' in (STATE/'python-tests.log').read_text();assert '# pass 23' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text()
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.service',timeout=60)
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");[(shutil.copy2(s/f,t/f),os.chown(t/f,u.pw_uid,u.pw_gid),os.chmod(t/f,0o600)) for f in '+repr(FILES)+']'
  ssh('sudo -n python3 -c '+shlex.quote(code));ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=60);assert hashes(TARGET)==local
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before-network-v2.tar.gz -C '+TARGET+' && sudo -n systemctl restart mgs-finance-dash.service',timeout=60);raise
 (STATE/'v2-published.json').write_text(json.dumps({'pass':True,'files':local,'authorization':['1546579646227943506','1546593628602900673']},indent=2));print('v2 code published, monthly migration pending')
else:raise ValueError('Unknown phase')
