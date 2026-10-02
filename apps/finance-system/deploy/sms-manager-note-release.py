"""Scoped release for manager SMS explanation card. No financial writes."""
import hashlib,io,json,os,pathlib,pwd,shlex,subprocess,sys,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import ssh,secret
AUTH='1555449010519679079';EVID=ROOT/'private'/('sms-manager-note-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STAGE='/var/tmp/mgs-finance-sms-manager-note-'+AUTH;BACKUP='/home/zeus/mgs-finance-backups/sms-manager-note-'+AUTH;FILES=['manager-view.mjs','public/operations.js','public/operations.css'];TESTS=['tests/manager-current-period.test.mjs','tests/manager-layout.test.mjs'];phase=sys.argv[1]
PG="sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -v ON_ERROR_STOP=1 -At -c "
CHECK="SELECT id,revision,md5(result::text),md5(overrides::text),md5(additions::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;"
def hlocal(files=FILES):return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
def hremote(path,files=FILES):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(path)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as t:
  for f in files:t.add(ROOT/f,arcname=f)
 return b.getvalue()
def scp(remote,local):
 pw=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');r,w=os.pipe();os.write(w,(pw+'\n').encode());os.close(w)
 try:p=subprocess.run(['sshpass','-d',str(r),'scp','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','zeus@162.55.28.178:'+remote,str(local)],pass_fds=(r,),capture_output=True,timeout=300)
 finally:os.close(r)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1000:])
 local.chmod(0o600)
if phase=='prepare':
 EVID.mkdir(parents=True,exist_ok=True,mode=0o700);expected=hremote(TARGET);before=ssh(PG+shlex.quote(CHECK),timeout=300).strip();ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(FILES)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && chmod 600 '+BACKUP+'/code-before.tar.gz');local=EVID/'code-before.tar.gz';scp(BACKUP+'/code-before.tar.gz',local);rh=ssh('sudo -n sha256sum '+BACKUP+'/code-before.tar.gz').split()[0];assert hashlib.sha256(local.read_bytes()).hexdigest()==rh;ssh('sudo -n rm -rf '+STAGE+' && sudo -n cp -a '+TARGET+' '+STAGE+' && sudo -n cp /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+STAGE+'/node && sudo -n chown -R mgs_pg:mgs_pg '+STAGE,timeout=300);ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle(FILES+TESTS));assert hremote(STAGE,FILES+TESTS)==hlocal(FILES+TESTS);(EVID/'prepared.json').write_text(json.dumps({'pass':True,'expected':expected,'candidate':hlocal(),'tests':hlocal(TESTS),'backup_sha256':rh,'data_hash':hashlib.sha256(before.encode()).hexdigest(),'stage':STAGE},indent=2));print('Manager-note backup and stage PASS')
elif phase=='exercise':
 p=json.loads((EVID/'prepared.json').read_text());assert hremote(TARGET)==p['expected'];assert hremote(STAGE,FILES+TESTS)==hlocal(FILES+TESTS);node=STAGE+'/node';out=ssh('sudo -n -u mgs_pg env PATH=/usr/bin:/bin '+node+' --test '+STAGE+'/tests/manager-current-period.test.mjs '+STAGE+'/tests/manager-layout.test.mjs',timeout=180);assert '# fail 0' in out;(EVID/'stage.json').write_text(json.dumps({'pass':True,'test_tail':out[-3000:]},indent=2));print('Manager-note stage tests PASS')
elif phase=='publish':
 p=json.loads((EVID/'prepared.json').read_text());assert hremote(TARGET)==p['expected'];assert hremote(STAGE)==hlocal();assert json.loads((EVID/'stage.json').read_text())['pass'];before=ssh(PG+shlex.quote(CHECK),timeout=300).strip();ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
 try:
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".manager-note-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)';ssh('sudo -n python3 -c '+shlex.quote(code));assert hremote(TARGET)==hlocal();ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
 assert ssh(PG+shlex.quote(CHECK),timeout=300).strip()==before;active=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert active==['active']*3;(EVID/'published.json').write_text(json.dumps({'pass':True,'files':hlocal(),'data_unchanged':True,'services':active,'rollback':BACKUP+'/code-before.tar.gz'},indent=2));print('Manager-note published; data unchanged; services active')
else:raise ValueError(phase)
