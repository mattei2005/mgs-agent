"""Rodolfo1546719646919434370/1546720000134483970: frontend-only manager/totals polish.
One-shot release, no auth/backend/financial mutation; rollback only these three assets.
"""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546719646919434370';STATE=ROOT/'private/manager-layout-1546719646919434370';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE='/var/tmp/mgs-finance-manager-'+AUTH;DB='mgs_finance_manager_'+AUTH
FILES=['public/operations.css','public/navigation.css','public/operations.js'];local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id;"
def hashes(target):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))')))
def save(n,d):(STATE/n).write_text(json.dumps(d,indent=2))
phase=sys.argv[1]
if phase=='prepare':
 assert not (STATE/'prepared.json').exists();expected=hashes(TARGET);assert expected=={f:hashlib.sha256((STATE/(pathlib.Path(f).name+'.before')).read_bytes()).hexdigest() for f in FILES},'Concurrent asset change: reconcile';before=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(FILES)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for n in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+n,timeout=180),validate=True);p=STATE/n;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+n).split()[0]==h;backup[n]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180);assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==before
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for f in FILES:t.add(ROOT/f,arcname=f)
 ssh('sudo -n install -d -o mgsfinance -g mgsfinance -m 700 '+STAGE+' && sudo -n -u mgsfinance tar -xzf - -C '+STAGE,payload.getvalue());assert hashes(STAGE)==local
 save('prepared.json',{'pass':True,'expected':expected,'files':local,'backup':backup,'stage':STAGE,'database':DB,'before':before});print('Fresh code/PG dual backup and hashes, isolated PG restore and stage PASS')
elif phase=='publish':
 p=json.loads((STATE/'prepared.json').read_text());assert hashes(TARGET)==p['expected'],'Concurrent asset change: reconcile';assert hashes(STAGE)==local;assert json.loads((STATE/'stage-browser.json').read_text())['pass'];assert json.loads((STATE/'decimal-total-audit.json').read_text())['pass'];assert '# fail 0' in (STATE/'node-tests.log').read_text()
 before=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 try:
  # Compatible CSS first, JS last, atomic replacements. Static handlers read files per request.
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");'+ '\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".manager-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
  ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET)==local
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET);raise
 after=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip();assert after==before,'Concurrent data movement: reconcile'
 save('published.json',{'pass':True,'files':local,'financial_data_unchanged':True,'restart':False,'backend_or_auth_changed':False});print('Three frontend assets published; remote hashes and unchanged financial state PASS')
elif phase=='verify':
 assert hashes(TARGET)==local;services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 save('deploy-readback.json',{'pass':True,'files':local,'services':services});print('Frontend hashes and services PASS')
else:raise ValueError('Unsupported phase')
