"""Reversible October SMS/prepaid finance release. Authority 1555464947394285580."""
import fcntl,hashlib,io,json,os,pathlib,shlex,subprocess,sys,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'scripts'));from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh,secret
sys.path.insert(0,str(ROOT));from finance_release_guard import lease
AUTH='1555464947394285580';EVID=ROOT/'private'/('sms-usage-prepaid-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STAGE='/var/tmp/mgs-finance-sms-usage-'+AUTH;BACKUP='/home/zeus/mgs-finance-backups/sms-usage-prepaid-'+AUTH;DB='mgs_finance_sms_'+AUTH
EXISTING=['direct_costs.py','worker.py','domain.py','manager-view.mjs','workspace.mjs','finance-ops.mjs','finance_gam_revenue_sync.py','public/app.js','public/app.css','public/financial-summary.js','public/operations.js']
NEW=['sms-usage-core.mjs','sms-usage-cli.mjs','prepaid-credit-cli.mjs'];FILES=EXISTING+NEW
TESTS=['tests/test_direct_costs.py','tests/test_gam_revenue.py','tests/sms-usage-core.test.mjs','tests/financial-summary.test.mjs','tests/ui-review.test.mjs','tests/manager-current-period.test.mjs','tests/manager-layout.test.mjs','tests/workspace.test.mjs']
SMS_PLAN=REPO/'work/finance-sms-automation-20261002/sms-plan-2026-10-01.json';PREPAID_PLAN=REPO/'work/finance-sms-automation-20261002/prepaid-plan-2026-10-01.json';BASELINE_COMMIT='7aff63a707ba051d1447844dd2a085fd99bc125a';phase=sys.argv[1]
PGBASE='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
PG=lambda database,sql:ssh(PGBASE+'psql -h /run/mgs-postgresql18 -U mgs_pg -d '+database+' -v ON_ERROR_STOP=1 -At -c '+shlex.quote(sql),timeout=300).strip()
CHECK="SELECT id,revision,md5(result::text),md5(overrides::text),md5(additions::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;"
def hashes(path,files):
 code='import pathlib,hashlib,json;p=pathlib.Path('+repr(path)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
 return json.loads(ssh('sudo -n python3 -c '+shlex.quote(code)))
def local_hashes(files):return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
def bundle():
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for f in FILES+TESTS:tar.add(ROOT/f,arcname=f)
  tar.add(SMS_PLAN,arcname='private/sms-usage-live-plan.json');tar.add(PREPAID_PLAN,arcname='private/prepaid-live-plan.json')
 return b.getvalue()
def scp_download(remote,local):
 pw=secret('Runcloud Server 01 - 162.55.28.178- zeus Acesso','password');r,w=os.pipe();os.write(w,(pw+'\n').encode());os.close(w)
 try:p=subprocess.run(['sshpass','-d',str(r),'scp','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','zeus@162.55.28.178:'+remote,str(local)],pass_fds=(r,),capture_output=True,timeout=600)
 finally:os.close(r)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1200:])
 local.chmod(0o600)
def save(name,value):EVID.mkdir(parents=True,exist_ok=True,mode=0o700);p=EVID/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2));p.chmod(0o600)
if phase=='prepare':
 EVID.mkdir(parents=True,exist_ok=True,mode=0o700);expected=hashes(TARGET,EXISTING);assert all(ssh('test ! -e '+TARGET+'/'+f+' && echo absent').strip()=='absent' for f in NEW);before=PG('mgs_finance',CHECK)
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(EXISTING)+' && '+PGBASE+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && sudo -n chown zeus:zeus '+BACKUP+'/* && chmod 600 '+BACKUP+'/*',timeout=600)
 remote_hash={name:ssh('sudo -n sha256sum '+BACKUP+'/'+name).split()[0] for name in ['code-before.tar.gz','finance-before.dump']}
 for name in remote_hash:scp_download(BACKUP+'/'+name,EVID/name);assert hashlib.sha256((EVID/name).read_bytes()).hexdigest()==remote_hash[name]
 subprocess.run(['git','show',BASELINE_COMMIT+':scripts/sync-smsfunnel-cost-daily.py'],cwd=REPO,check=True,stdout=(EVID/'sync-smsfunnel-cost-daily.before.py').open('wb'));(EVID/'sync-smsfunnel-cost-daily.before.py').chmod(0o600)
 (EVID/'crontab.before').write_text(subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout);(EVID/'crontab.before').chmod(0o600)
 ssh(PGBASE+'dropdb -h /run/mgs-postgresql18 -U mgs_pg --if-exists '+DB+' && '+PGBASE+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+PGBASE+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=600);assert PG(DB,CHECK)==before
 ssh('sudo -n rm -rf '+STAGE+' && sudo -n cp -a '+TARGET+' '+STAGE+' && sudo -n cp /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+STAGE+'/node && sudo -n chown -R mgs_pg:mgs_pg '+STAGE,timeout=300);ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle(),timeout=300);assert hashes(STAGE,FILES+TESTS)==local_hashes(FILES+TESTS)
 save('prepared.json',{'pass':True,'authority':AUTH,'target_expected':expected,'candidate':local_hashes(FILES),'tests':local_hashes(TESTS),'backup':remote_hash,'before_data_sha256':hashlib.sha256(before.encode()).hexdigest(),'stage':STAGE,'database':DB,'isolated_restore':True});print('SMS usage/prepaid backup, isolated restore and stage PASS')
elif phase=='exercise':
 p=json.loads((EVID/'prepared.json').read_text());assert hashes(TARGET,EXISTING)==p['target_expected'];assert hashes(STAGE,FILES+TESTS)==local_hashes(FILES+TESTS);node=STAGE+'/node'
 node_tests=['tests/sms-usage-core.test.mjs','tests/financial-summary.test.mjs','tests/ui-review.test.mjs','tests/manager-current-period.test.mjs','tests/manager-layout.test.mjs']
 out=ssh('cd '+STAGE+' && sudo -n -u mgs_pg '+node+' --test '+' '.join(node_tests),timeout=300);assert '# fail 0' in out
 py=ssh('cd '+STAGE+' && sudo -n -u mgs_pg /usr/bin/python3 -m unittest tests.test_direct_costs tests.test_gam_revenue.GamRevenuePlanTests.test_intake_and_finalize_slots_and_spend_gate tests.test_gam_revenue.GamRevenuePlanTests.test_run_sms_step_uses_exact_revenue_date_and_validates_state -v',timeout=300);assert 'OK' in py
 prepaid=ssh('set -e; cd '+STAGE+'; for x in rehearse apply verify; do sudo -n -u mgs_pg '+node+' prepaid-credit-cli.mjs "$x" '+DB+' < private/prepaid-live-plan.json; done',timeout=300)
 sms=ssh('set -e; cd '+STAGE+'; for x in rehearse apply verify; do sudo -n -u mgs_pg '+node+' sms-usage-cli.mjs "$x" '+DB+' < private/sms-usage-live-plan.json; done',timeout=600)
 for output in [prepaid,sms]:
  rows=[json.loads(x) for x in output.splitlines() if x.startswith('{')];assert len(rows)==3 and all(x['pass'] for x in rows) and rows[-1]['phase']=='verify'
 save('stage.json',{'pass':True,'node_tail':out[-2000:],'python_tail':py[-2000:],'prepaid':[json.loads(x) for x in prepaid.splitlines() if x.startswith('{')],'sms':[json.loads(x) for x in sms.splitlines() if x.startswith('{')]});print('SMS usage/prepaid stage tests and isolated financial writes PASS')
elif phase=='publish':
 p=json.loads((EVID/'prepared.json').read_text());assert json.loads((EVID/'stage.json').read_text())['pass'];assert hashes(TARGET,EXISTING)==p['target_expected'];assert hashes(STAGE,FILES+TESTS)==local_hashes(FILES+TESTS);before=PG('mgs_finance',CHECK)
 with lease(ROOT,exclusive=True,timeout=600):
  ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
  try:
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");\nfor f in '+repr(FILES)+':\n p=t/f;p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+".sms-usage-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET,FILES)==local_hashes(FILES);ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  except Exception:
   ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n rm -f '+' '.join(TARGET+'/'+f for f in NEW)+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
 assert PG('mgs_finance',CHECK)==before;active=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert active==['active']*3;health=ssh("curl --silent --show-error --fail --unix-socket /run/mgs-finance-dash/app.sock http://localhost/login >/dev/null && echo ok").strip();assert health=='ok'
 save('published.json',{'pass':True,'files':local_hashes(FILES),'data_unchanged':True,'services':active,'health':health,'rollback':BACKUP});print('SMS usage/prepaid code published; data unchanged; services active')
else:raise ValueError(phase)
