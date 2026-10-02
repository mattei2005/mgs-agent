"""Scoped UI visibility release for archived/reclassified expenses."""
import hashlib,io,json,os,pathlib,pwd,shlex,subprocess,sys,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import ssh,secret
AUTH='1555422806940983327';EVID=ROOT/'private'/('sms-direct-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STAGE='/var/tmp/mgs-finance-sms-'+AUTH;BACKUP='/home/zeus/mgs-finance-backups/sms-direct-'+AUTH;FILES=['workspace.mjs','public/app.js'];phase=sys.argv[1]
PG="sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -v ON_ERROR_STOP=1 -At -c "
CHECK="SELECT id,revision,md5(result::text),md5(overrides::text),md5(additions::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;"
def hlocal():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
def hremote(path):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(path)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))')))
def bundle():
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as t:
  for f in FILES:t.add(ROOT/f,arcname=f)
 return b.getvalue()
def scp(remote,local):
 pw=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');r,w=os.pipe();os.write(w,(pw+'\n').encode());os.close(w)
 try:p=subprocess.run(['sshpass','-d',str(r),'scp','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','zeus@162.55.28.178:'+remote,str(local)],pass_fds=(r,),capture_output=True,timeout=300)
 finally:os.close(r)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1000:])
 local.chmod(0o600)
if phase=='prepare':
 expected=hremote(TARGET);before=ssh(PG+shlex.quote(CHECK),timeout=300).strip();ssh('sudo -n tar -czf '+BACKUP+'/ui-visibility-before.tar.gz -C '+TARGET+' '+' '.join(FILES)+' && sudo -n chown zeus:zeus '+BACKUP+'/ui-visibility-before.tar.gz && chmod 600 '+BACKUP+'/ui-visibility-before.tar.gz');local=EVID/'ui-visibility-before.tar.gz';scp(BACKUP+'/ui-visibility-before.tar.gz',local);rh=ssh('sudo -n sha256sum '+BACKUP+'/ui-visibility-before.tar.gz').split()[0];assert hashlib.sha256(local.read_bytes()).hexdigest()==rh;ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle());assert hremote(STAGE)==hlocal();(EVID/'ui-prepared.json').write_text(json.dumps({'pass':True,'expected':expected,'candidate':hlocal(),'backup_sha256':rh,'data_hash':hashlib.sha256(before.encode()).hexdigest()},indent=2));print('UI backup and stage overlay PASS')
elif phase=='exercise':
 p=json.loads((EVID/'ui-prepared.json').read_text());assert hremote(TARGET)==p['expected'];assert hremote(STAGE)==hlocal();node=STAGE+'/node';out=ssh('sudo -n -u mgs_pg env PATH=/usr/bin:/bin '+node+' --test '+STAGE+'/tests/ui-review.test.mjs',timeout=180);assert '# fail 0' in out;(EVID/'ui-stage.json').write_text(json.dumps({'pass':True,'test_tail':out[-2000:]},indent=2));print('UI stage test PASS')
elif phase=='publish':
 p=json.loads((EVID/'ui-prepared.json').read_text());assert hremote(TARGET)==p['expected'];assert hremote(STAGE)==hlocal();assert json.loads((EVID/'ui-stage.json').read_text())['pass'];before=ssh(PG+shlex.quote(CHECK),timeout=300).strip();ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
 try:
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".ui-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)';ssh('sudo -n python3 -c '+shlex.quote(code));assert hremote(TARGET)==hlocal();ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/ui-visibility-before.tar.gz -C '+TARGET+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
 assert ssh(PG+shlex.quote(CHECK),timeout=300).strip()==before;active=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert active==['active']*3;(EVID/'ui-published.json').write_text(json.dumps({'pass':True,'files':hlocal(),'data_unchanged':True,'services':active,'rollback':BACKUP+'/ui-visibility-before.tar.gz'},indent=2));print('UI visibility release published; data unchanged; services active')
else:raise ValueError(phase)
