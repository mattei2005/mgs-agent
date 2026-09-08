"""Scoped native-history presentation release; snapshots/users/ledger untouched."""
import pathlib,sys,json,hashlib,shlex,io,tarfile,base64,fcntl
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();D=R/'private/history-ui-1546894693135028234';AUTH='1546896342805123125';T='/home/mgsfinance/releases/pg-auth-1545934831664242748';B='/home/zeus/mgs-finance-backups/'+AUTH;S='/var/tmp/mgs-finance-history-ui-'+AUTH;DB='mgs_finance_history_ui_'+AUTH
OLD=['public/app.js','public/operations.js','public/navigation.js','public/index.html','public/operations.html','finance-ops.mjs','history.mjs'];FILES=OLD+['public/history-dashboard.js','public/history-operations.js'];E='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';PG=E+BIN+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
CHECK="SELECT count(*) FROM source_cells; SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;"
def save(n,d):(D/n).write_text(json.dumps(d,indent=2))
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for f in files:tar.add(R/f,arcname=f)
 return b.getvalue()
def copyback(remote,name):
 data=base64.b64decode(ssh('sudo -n base64 -w0 '+remote,timeout=180),validate=True);p=D/name;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sudo -n sha256sum '+remote).split()[0]==h;return h
phase=sys.argv[1];local={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in FILES}
if phase=='prepare':
 assert not (D/'prepared.json').exists();expected=hashes(T,OLD)
 # Snapshot state and backups while the local quote-sync writer is excluded.
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip()
  ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m 700 '+B+' && sudo -n tar -czf '+B+'/code-before.tar.gz -C '+T+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+B+'/code-before.tar.gz && '+E+BIN+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/finance-before.dump && chmod 600 '+B+'/*',timeout=240)
  backups={n:copyback(B+'/'+n,n) for n in ['code-before.tar.gz','finance-before.dump']}
 ssh(E+BIN+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+E+BIN+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/finance-before.dump',timeout=240);assert ssh(PG+'-d '+DB+' -c '+shlex.quote(CHECK)).strip()==before
 prior='private/history-import-1546884731436671056';files=[str(p.relative_to(R)) for pattern in ['*.py','*.mjs','*-rules.json','manager-layout*.json','*-schema.sql'] for p in R.glob(pattern)]+[str(p.relative_to(R)) for p in (R/'public').iterdir() if p.is_file()]+['tests/history-ui-pg.mjs',prior+'/built.json']+[str(p.relative_to(R)) for p in (R/prior/'payloads').glob('*.json')]
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+S+' && sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(sorted(set(files))),timeout=180)
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(T)+');t=pathlib.Path('+repr(S)+');(t/"private").mkdir(exist_ok=True);(t/"private/history-ui-1546894693135028234").mkdir(exist_ok=True);[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(S,FILES)==local
 save('prepared.json',{'pass':True,'expected':expected,'files':local,'backup':backups,'stage':S,'database':DB,'restore_readback':True});print('Dual backup/hash/isolated restore PASS; candidate staged')
elif phase=='exercise':
 assert hashes(S,FILES)==local;print(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/tests/history-ui-pg.mjs',timeout=480));copyback(S+'/private/history-ui-1546894693135028234/stage-pg.json','stage-pg.json')
elif phase=='restage':
 ssh('sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(FILES+['tests/history-ui-pg.mjs']));assert hashes(S,FILES)==local;print('Candidate updated; production untouched')
elif phase=='publish':
 p=json.loads((D/'prepared.json').read_text());assert hashes(T,OLD)==p['expected'];assert hashes(S,FILES)==local
 for f in ['stage-readback.json','stage-pg.json','unit-readback.json']:assert json.loads((D/f).read_text())['pass']
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip()
  try:
   ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(S)+');t=pathlib.Path('+repr(T)+');u=pwd.getpwnam("mgsfinance");'+'\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".native-history-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(T,FILES)==local
   ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  except Exception:
   ssh('sudo -n tar -xzf '+B+'/code-before.tar.gz -C '+T+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
  assert ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip()==before
 save('published.json',{'pass':True,'files':local,'financial_data_history_and_users_unchanged':True,'gateway_restart':False,'rollback_archive':B+'/code-before.tar.gz'});print('Published native views; all financial data/history/users unchanged')
elif phase=='verify':
 assert hashes(T,FILES)==local;services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 grants=ssh(PG+'-d mgs_finance -c '+shlex.quote("SELECT has_table_privilege('mgsfinance','finance_history','SELECT'),has_table_privilege('mgsfinance','finance_history','INSERT'),has_table_privilege('mgsfinance','finance_history','UPDATE'),has_table_privilege('mgsfinance','finance_history','DELETE')")).strip();assert grants=='t|f|f|f'
 save('deploy-readback.json',{'pass':True,'files':local,'services':services,'history_grants':grants});print('Hashes/services/immutable grants PASS')
else:raise ValueError('phase')
