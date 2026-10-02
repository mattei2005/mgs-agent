"""Reversible release for SMS direct-cost support and isolated DB exercise."""
import base64, fcntl, hashlib, io, json, os, pathlib, pwd, shlex, subprocess, sys, tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import ssh,secret
AUTH='1555422806940983327'
EVID=ROOT/'private'/('sms-direct-'+AUTH)
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
STAGE='/var/tmp/mgs-finance-sms-'+AUTH
BACKUP='/home/zeus/mgs-finance-backups/sms-direct-'+AUTH
DB='mgs_finance_sms_'+AUTH
RUNTIME=['worker.py','direct_costs.py','monthly-review.mjs','simple-review.mjs','period-preview.mjs','sms-direct-cost-cli.mjs']
TESTS=['tests/test_direct_costs.py','tests/monthly-review.test.mjs']
PLAN='private/sms-plan.json'
PGBASE='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
CHECK="SELECT count(*) FROM source_cells; SELECT id,revision,md5(result::text),md5(overrides::text),md5(additions::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;"

def save(name,data):
 EVID.mkdir(parents=True,exist_ok=True,mode=0o700);p=EVID/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2));p.chmod(0o600)
def hashes(remote,files):
 code='import pathlib,hashlib,json;p=pathlib.Path('+repr(remote)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+' if (p/f).exists()}))'
 return json.loads(ssh('sudo -n python3 -c '+shlex.quote(code)))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for name in files:tar.add(ROOT/name,arcname=name)
 return b.getvalue()
def scp_download(remote,local):
 pw=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');r,w=os.pipe();os.write(w,(pw+'\n').encode());os.close(w)
 try:
  p=subprocess.run(['sshpass','-d',str(r),'scp','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','zeus@162.55.28.178:'+remote,str(local)],pass_fds=(r,),capture_output=True,timeout=600)
 finally:os.close(r)
 if p.returncode:raise RuntimeError('SCP failed: '+p.stderr.decode(errors='replace')[-1000:])
 local.chmod(0o600)
def pg(db,sql):return ssh(PGBASE+'psql -h /run/mgs-postgresql18 -U mgs_pg -d '+db+' -v ON_ERROR_STOP=1 -At -c '+shlex.quote(sql),timeout=300).strip()
def local_hashes(files):return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}

phase=sys.argv[1]
local=local_hashes(RUNTIME+TESTS)
if phase=='prepare':
 if (EVID/'prepared.json').exists():raise RuntimeError('prepared evidence already exists')
 expected=hashes(TARGET,[f for f in RUNTIME if f not in ('direct_costs.py','sms-direct-cost-cli.mjs')])
 with (ROOT/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  before=pg('mgs_finance',CHECK)
  ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(expected)+' && '+PGBASE+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && sudo -n chown zeus:zeus '+BACKUP+'/* && chmod 600 '+BACKUP+'/*',timeout=600)
  remote_hashes=json.loads(ssh('sudo -n sha256sum '+BACKUP+'/code-before.tar.gz '+BACKUP+'/finance-before.dump | python3 -c '+shlex.quote("import sys,json;print(json.dumps({x.split()[1]:x.split()[0] for x in sys.stdin if x.strip()}))")))
 EVID.mkdir(parents=True,exist_ok=True,mode=0o700)
 for name in ['code-before.tar.gz','finance-before.dump']:
  scp_download(BACKUP+'/'+name,EVID/name)
  assert hashlib.sha256((EVID/name).read_bytes()).hexdigest()==remote_hashes[BACKUP+'/'+name]
 ssh(PGBASE+'dropdb -h /run/mgs-postgresql18 -U mgs_pg --if-exists '+DB+' && '+PGBASE+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+PGBASE+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=600)
 assert pg(DB,CHECK)==before
 ssh('sudo -n rm -rf '+STAGE+' && sudo -n cp -a '+TARGET+' '+STAGE+' && sudo -n chown -R mgs_pg:mgs_pg '+STAGE,timeout=300)
 plan=json.loads((ROOT.parent.parent/'work/finance-sms-dash-audit-20261002/sms-plan.json').read_text());(EVID/'sms-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));(EVID/'sms-plan.json').chmod(0o600)
 (ROOT/'private/sms-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));(ROOT/'private/sms-plan.json').chmod(0o600)
 ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle(RUNTIME+TESTS+[PLAN]),timeout=300)
 assert hashes(STAGE,RUNTIME+TESTS)==local
 save('prepared.json',{'pass':True,'authority':AUTH,'target_expected':expected,'candidate':local,'backup':remote_hashes,'before':hashlib.sha256(before.encode()).hexdigest(),'stage':STAGE,'database':DB,'restore_readback':True})
 print('Backup local+remote, isolated restore and candidate stage PASS')
elif phase=='exercise':
 p=json.loads((EVID/'prepared.json').read_text());assert hashes(TARGET,list(p['target_expected']))==p['target_expected'];assert hashes(STAGE,RUNTIME+TESTS)==local
 node=STAGE+'/node';plan=STAGE+'/'+PLAN
 test=ssh('sudo -n -u mgs_pg '+node+' --test '+STAGE+'/tests/monthly-review.test.mjs',timeout=300)
 py=ssh('cd '+STAGE+' && sudo -n -u mgs_pg python3 -m unittest tests.test_direct_costs -v',timeout=300)
 for mode in ['dry-run','fx-test','apply','verify']:
  code='import json,pathlib,subprocess;d=json.loads(pathlib.Path('+repr(plan)+').read_text());d["mode"]='+repr(mode)+';r=subprocess.run(['+repr(node)+','+repr(STAGE+'/sms-direct-cost-cli.mjs')+','+repr(DB)+'],input=json.dumps(d),text=True,capture_output=True,timeout=300);assert r.returncode==0,r.stderr;print(r.stdout)'
  out=ssh('sudo -n -u mgs_pg python3 -c '+shlex.quote(code),timeout=360);save('stage-'+mode+'.json',json.loads(out))
 assert pg(DB,"SELECT count(*) FROM finance_ledger WHERE id IN ('1988c8e3-ef8b-558b-ab5b-625df4ccb834','c4dba803-7d7d-5aae-a9ef-3faca0f8abce','cfc637d7-b143-5ec0-9ba0-c987fc1847ad')")=='3'
 save('stage-tests.json',{'pass':True,'node_tail':test[-2000:],'python_tail':py[-2000:],'dry_run':True,'fx_test':True,'apply':True,'verify':True})
 print('Stage RED/GREEN, dry-run, FX invariance, atomic apply and idempotent verify PASS')
elif phase=='publish':
 p=json.loads((EVID/'prepared.json').read_text());assert hashes(TARGET,list(p['target_expected']))==p['target_expected'];assert hashes(STAGE,RUNTIME)=={k:local[k] for k in RUNTIME};assert json.loads((EVID/'stage-tests.json').read_text())['pass']
 before=pg('mgs_finance',CHECK)
 with (ROOT/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
  try:
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");\nfor f in '+repr(RUNTIME)+':\n p=t/f;q=p.with_name(p.name+".sms-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET,RUNTIME)=={k:local[k] for k in RUNTIME}
   ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  except Exception:
   ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n rm -f '+TARGET+'/direct_costs.py '+TARGET+'/sms-direct-cost-cli.mjs && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
 assert pg('mgs_finance',CHECK)==before
 active=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert active==['active']*3
 save('published.json',{'pass':True,'runtime':{k:local[k] for k in RUNTIME},'data_unchanged_at_cutover':True,'services':active,'rollback':BACKUP+'/code-before.tar.gz'})
 print('Scoped code release published; data unchanged; services active')
else:raise ValueError(phase)
