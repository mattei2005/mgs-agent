"""One-shot authorized manager rollout; no source, finance, schema, OS-config or gateway changes."""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64,fcntl
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546858367635685396';STATE=ROOT/('private/manager-access-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;STAGE='/var/tmp/mgs-finance-managers-'+AUTH;DB='mgs_finance_managers_'+AUTH
OLD=['manager-view.mjs','finance-ops.mjs','public/operations.js','public/navigation.js'];FILES=OLD+['manager-layouts.json'];local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x;"
def hashes(target,files=FILES):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def save(n,d):(STATE/n).write_text(json.dumps(d,indent=2))
def bundle(files):
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as t:
  for f in files:t.add(ROOT/f,arcname=f)
 return payload.getvalue()
phase=sys.argv[1]
if phase=='prepare':
 assert not (STATE/'prepared.json').exists();expected=hashes(TARGET,OLD);assert expected=={f:hashlib.sha256((STATE/'before'/f).read_bytes()).hexdigest() for f in OLD};before=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
 ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
 backup={}
 for n in ['code-before.tar.gz','finance-before.dump']:
  data=base64.b64decode(ssh('base64 -w0 '+BACKUP+'/'+n,timeout=180),validate=True);p=STATE/n;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+n).split()[0]==h;backup[n]=h
 ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+BACKUP+'/finance-before.dump',timeout=180)
 assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==before
 files=[str(f.relative_to(ROOT)) for pattern in ['*.py','*.mjs','*-rules.json'] for f in ROOT.glob(pattern)]+[str(f.relative_to(ROOT)) for f in (ROOT/'public').iterdir() if f.is_file()]+['manager-layout.json','manager-layouts.json','finance-ops-schema.sql','tests/manager-access-pg.mjs']
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+STAGE+' && sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle(files));assert hashes(STAGE)==local
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(TARGET)+');t=pathlib.Path('+repr(STAGE)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180)
 save('prepared.json',{'pass':True,'expected':expected,'files':local,'backup':backup,'stage':STAGE,'database':DB,'before':before});print('Dual backup/hash, restored financial data and stage code verified PASS')
elif phase=='exercise':
 assert hashes(STAGE)==local
 print(ssh('sudo -n -u mgs_pg env FINANCE_MANAGER_DATABASE='+DB+' '+STAGE+'/node '+STAGE+'/tests/manager-access-pg.mjs',timeout=480))
 out=json.loads(ssh('sudo -n -u mgs_pg python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(STAGE+'/private/manager-access-stage.json')+').read_text())')));assert out['pass'];save('pg-exercise.json',out)
elif phase=='restage':
 p=json.loads((STATE/'prepared.json').read_text());assert hashes(TARGET,OLD)==p['expected'];ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,bundle(FILES+['tests/manager-access-pg.mjs']));assert hashes(STAGE)==local;print('Stage updated; live code unchanged')
elif phase=='publish':
 p=json.loads((STATE/'prepared.json').read_text());assert hashes(TARGET,OLD)==p['expected'];assert hashes(STAGE)==local;assert json.loads((STATE/'pg-exercise.json').read_text())['pass'];assert json.loads((STATE/'local-tests.json').read_text())['pass']
 with (ROOT/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
  try:
   ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(STAGE)+');t=pathlib.Path('+repr(TARGET)+');u=pwd.getpwnam("mgsfinance");'+ '\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".manager-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(TARGET)==local
   ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  except Exception:
   ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
  after=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip();assert after==before
 save('published.json',{'pass':True,'files':local,'financial_data_unchanged':True,'gateway_restart':False});print('Published5files; source/scenarios/ledger unchanged PASS')
elif phase=='verify':
 assert hashes(TARGET)==local;services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 users=ssh(pg+'-d mgs_finance -c '+shlex.quote('SELECT username,display_name,role,manager_key,enabled FROM finance_users ORDER BY username')).strip();save('deploy-readback.json',{'pass':True,'files':local,'services':services,'users':users});print(json.dumps({'pass':True,'services':services,'users':users},ensure_ascii=False))
else:raise ValueError('Unsupported phase')
