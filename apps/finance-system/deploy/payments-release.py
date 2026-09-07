"""Bounded finance operations release; additive empty tables, fresh isolated restore."""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546642267291394199';STATE=ROOT/('private/payments-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE='/var/tmp/mgs-finance-payments-'+AUTH;DB='mgs_finance_payments_'+AUTH;NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';phase=sys.argv[1]
OLD=['server.mjs','auth.mjs','public/app.js','public/index.html','public/refinements.css'];FILES=OLD+['finance-ops.mjs','finance-ops-schema.sql','manager-view.mjs','manager-layout.json','public/financial-summary.js','public/operations.js','public/operations.html','public/operations.css','deploy/finance-notices.mjs'];local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def save(name,obj):(STATE/name).write_text(json.dumps(obj,indent=2))
schema=(ROOT/'finance-ops-schema.sql').read_text()+'\nGRANT SELECT,INSERT,UPDATE ON finance_users,finance_approvals,finance_ledger TO mgsfinance;\n'
if phase=='prepare':
 assert not (STATE/'prepared.json').exists();expected=hashes(TARGET,OLD)
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
 baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for name in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180),validate=True);p=STATE/name;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h;backup[name]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB);ssh(pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180);assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for pattern in ['*.py','*.mjs','*-rules.json']:
   for f in ROOT.glob(pattern):t.add(f,arcname=f.name)
  for f in (ROOT/'public').iterdir():
   if f.is_file():t.add(f,arcname='public/'+f.name)
  for f in ['manager-layout.json','finance-ops-schema.sql','deploy/meta-lookup-queue.py','deploy/finance-notices.mjs','tests/payments-pg.mjs']:t.add(ROOT/f,arcname=f)
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+STAGE+' && sudo -n -u mgs_pg tar -xzf - -C '+STAGE,payload.getvalue(),timeout=90)
 code='import shutil,pathlib,os,pwd;s=pathlib.Path('+repr(TARGET)+');t=pathlib.Path('+repr(STAGE)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2('+repr(NODE)+',t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(STAGE,FILES)==local;ssh(pg+'-d '+DB,schema.encode());save('prepared.json',{'pass':True,'backup':backup,'baseline':baseline,'expected':expected,'files':local,'stage':STAGE,'database':DB});print('Fresh backups, hash-matched second copy and isolated PostgreSQL restore PASS')
elif phase=='exercise':
 assert hashes(STAGE,FILES)==local
 print(ssh('sudo -n -u mgs_pg env FINANCE_PAYMENTS_DATABASE='+DB+' '+STAGE+'/node '+STAGE+'/tests/payments-pg.mjs',timeout=480));d=json.loads(ssh('sudo -n -u mgs_pg python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(STAGE+'/private/payments-test-readback.json')+').read_text())')));assert d['pass'];save('pg-exercise.json',d)
elif phase=='publish':
 prepared=json.loads((STATE/'prepared.json').read_text());assert hashes(TARGET,OLD)==prepared['expected'],'Concurrent code changed; reconcile';assert hashes(STAGE,FILES)==local and json.loads((STATE/'pg-exercise.json').read_text())['pass']
 assert '# fail 0' in (STATE/'node-tests.log').read_text() and '\nOK' in (STATE/'python-tests.log').read_text()
 before=ssh(pg+'-d mgs_finance -c '+shlex.quote("SELECT json_agg(q) FROM (SELECT id,revision,md5(overrides::text) AS inputs,md5(additions::text) AS additions,md5(result::text) AS result FROM scenarios ORDER BY id) q")).strip();save('production-cutover-before.json',json.loads(before))
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service',timeout=60)
  ssh(pg+'-d mgs_finance',schema.encode())
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");[(shutil.copy2(s/f,t/f),os.chown(t/f,u.pw_uid,u.pw_gid),os.chmod(t/f,0o600)) for f in '+repr(FILES)+']'
  ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET,FILES)==local;ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service',timeout=60)
 except Exception:
  ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service',timeout=90);save('publication-failure.json',{'code_rollback':True,'backup':BACKUP});raise
 after=ssh(pg+'-d mgs_finance -c '+shlex.quote("SELECT json_agg(q) FROM (SELECT id,revision,md5(overrides::text) AS inputs,md5(additions::text) AS additions,md5(result::text) AS result FROM scenarios ORDER BY id) q")).strip();assert json.loads(before)==json.loads(after),'Concurrent data movement; investigate before closure';save('published.json',{'pass':True,'files':local,'production_financial_mutations':0,'database_preserved':True,'additive_tables':['finance_users','finance_approvals','finance_ledger']});print('Code + additive empty tables release; exact scenario/inputs/review readback unchanged PASS')
elif phase=='verify':
 assert hashes(TARGET,FILES)==local;services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3;assert ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()==json.loads((STATE/'prepared.json').read_text())['baseline'];save('deploy-readback.json',{'pass':True,'services':services,'files':local,'backup':BACKUP,'baseline_preserved':True});print('Production services/code/baseline PASS')
else:raise ValueError('Unsupported phase')
