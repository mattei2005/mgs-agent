"""Bounded account-manager release: dual backup, isolated restore, rehearsal, guarded publish."""
import pathlib,sys,json,hashlib,shlex,tarfile,io,fcntl,base64
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
from runcloud_ops import ssh
AUTH='1547052028663169105';D=R/('private/account-managers-'+AUTH);T='/home/mgsfinance/releases/pg-auth-1545934831664242748';S='/var/tmp/mgs-finance-assign-'+AUTH;DB='mgs_finance_assign_'+AUTH;B='/home/zeus/mgs-finance-backups/'+AUTH
OLD=['accounts.mjs','media-spend.mjs','workspace.mjs','site_catalog.py','worker.py','manager-view.mjs','public/app.js'];FILES=OLD+['account_manager_costs.py','account-assignment.mjs','account-assignment-cli.mjs']
E='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';PG=E+BIN+'psql -h /run/mgs-postgresql18 -U mgs_pg -At -v ON_ERROR_STOP=1 '
CHECK="SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id;SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x;SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x;"
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;r=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for f in files:tar.add(R/f,arcname=f)
 return b.getvalue()
def save(name,obj):(D/name).write_text(json.dumps(obj,ensure_ascii=False))
local={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in FILES};state=json.loads(pathlib.Path('/root/mgs-agent/data/finance-media-spend-state.json').read_text());payload=json.dumps({'plan':json.loads((D/'plan.json').read_text()),'collection':json.loads(pathlib.Path(state['last_collection_path']).read_text())}).encode();phase=sys.argv[1]
if phase=='prepare':
 assert not (D/'prepared.json').exists();expected=hashes(T,OLD)
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK));ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m 700 '+B+' && sudo -n tar -czf '+B+'/code.tar.gz -C '+T+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+B+'/code.tar.gz && '+E+BIN+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/data.dump',timeout=240)
 proofs={}
 for name in ['code.tar.gz','data.dump']:
  raw=base64.b64decode(ssh('base64 -w0 '+B+'/'+name,timeout=180),validate=True);p=D/('backup-'+name);p.write_bytes(raw);p.chmod(0o600);proofs[name]=hashlib.sha256(raw).hexdigest();assert ssh('sha256sum '+B+'/'+name).split()[0]==proofs[name]
 ssh(E+BIN+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+E+BIN+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/data.dump',timeout=240);assert ssh(PG+'-d '+DB+' -c '+shlex.quote(CHECK))==before
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(T)+');t=pathlib.Path('+repr(S)+');t.mkdir(mode=0o700);'+ '\nfor p in s.iterdir():\n if p.is_file() and p.suffix in (".mjs",".py",".json",".sql"):shutil.copy2(p,t/p.name)\n'+ '(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copytree(s/"public",t/"public");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=240);ssh('sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(FILES),timeout=180);assert hashes(S,FILES)==local;save('prepared.json',{'pass':True,'expected':expected,'files':local,'backup':proofs});print('Dual backups, exact restore and isolated stage PASS')
elif phase in ('test','retest'):
 if phase=='retest':ssh('sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(FILES),timeout=180)
 assert hashes(S,FILES)==local;out=json.loads(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/account-assignment-cli.mjs '+DB,payload,timeout=480));save('stage.json',out);assert out['pass'];print(json.dumps(out))
elif phase=='publish':
 p=json.loads((D/'prepared.json').read_text());assert p['pass'] and json.loads((D/'stage.json').read_text())['pass'];assert hashes(T,OLD)==p['expected'] and hashes(S,FILES)==local
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(S)+');t=pathlib.Path('+repr(T)+');u=pwd.getpwnam("mgsfinance");'+'\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".assignment-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);q.chmod(0o600);os.replace(q,p)'
  ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(T,FILES)==local
  # Scoped finite application-service restart only, never any agent gateway.
  ssh('sudo -n systemctl restart mgs-finance-dash.service');out=json.loads(ssh('sudo -n -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+T+'/account-assignment-cli.mjs mgs_finance',payload,timeout=480));assert out['pass'];save('production.json',out)
 services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3;save('published.json',{'pass':True,'files':local,'services':services,'backup':B});print(json.dumps(out))
else:raise ValueError('phase')
