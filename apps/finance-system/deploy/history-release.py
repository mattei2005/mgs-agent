"""History release1546884731436671056: dual backup, restore test, scoped code+data. No Sheets or gateway writes."""
import pathlib,sys,json,hashlib,shlex,tarfile,io,base64,fcntl
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546884731436671056';D=R/('private/history-import-'+AUTH);T='/home/mgsfinance/releases/pg-auth-1545934831664242748';B='/home/zeus/mgs-finance-backups/'+AUTH;S='/var/tmp/mgs-finance-history-'+AUTH;DB='mgs_finance_history_'+AUTH
OLD=['server.mjs','workspace.mjs','finance-ops.mjs','public/app.js','public/operations.js','public/navigation.js'];FILES=OLD+['history.mjs','public/history.html','public/history.css','public/history.js'];ARTIFACTS=['deploy/history-import.mjs','deploy/history-schema.sql','tests/history-pg.mjs']
E='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';PG=E+BIN+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
CHECK="SELECT count(*) FROM source_cells; SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x;"
def save(n,d):(D/n).write_text(json.dumps(d,indent=2))
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as tar:
  for f in files:tar.add(R/f,arcname=f)
 return b.getvalue()
def copyback(remote,local):
 data=base64.b64decode(ssh('sudo -n base64 -w0 '+remote,timeout=180),validate=True);p=D/local;p.write_bytes(data);p.chmod(0o600);h=hashlib.sha256(data).hexdigest();assert ssh('sudo -n sha256sum '+remote).split()[0]==h;return h
local={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in FILES};phase=sys.argv[1]
if phase=='prepare':
 assert not (D/'prepared.json').exists();expected=hashes(T,OLD);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip()
 ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m 700 '+B+' && sudo -n tar -czf '+B+'/code-before.tar.gz -C '+T+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+B+'/code-before.tar.gz && '+E+BIN+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/finance-before.dump && chmod 600 '+B+'/*',timeout=180)
 backups={n:copyback(B+'/'+n,n) for n in ['code-before.tar.gz','finance-before.dump']}
 ssh(E+BIN+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+E+BIN+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/finance-before.dump',timeout=180);assert ssh(PG+'-d '+DB+' -c '+shlex.quote(CHECK)).strip()==before
 files=[str(p.relative_to(R)) for pattern in ['*.py','*.mjs','*-rules.json','manager-layout*.json','*-schema.sql'] for p in R.glob(pattern)]+[str(p.relative_to(R)) for p in (R/'public').iterdir() if p.is_file()]+ARTIFACTS+['private/history-import-'+AUTH+'/built.json']+[str(p.relative_to(R)) for p in (D/'payloads').glob('*.json')]
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+S+' && sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(sorted(set(files))),timeout=180)
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(T)+');t=pathlib.Path('+repr(S)+');(t/"private").mkdir(exist_ok=True);[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(S,FILES)==local
 save('prepared.json',{'pass':True,'expected':expected,'files':local,'backup':backups,'stage':S,'database':DB,'before':before});print('Backup duplo hash+restore PASS;stage isolado pronto')
elif phase in ['import-stage','import-live']:
 target=DB if phase=='import-stage' else 'mgs_finance'
 if phase=='import-live':assert json.loads((D/'stage-tests.json').read_text())['pass'];assert hashes(T,OLD)==json.loads((D/'prepared.json').read_text())['expected']
 ssh(PG+'-d '+target+' -f '+S+'/deploy/history-schema.sql')
 print(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/deploy/history-import.mjs '+target,timeout=180));copyback(S+'/private/history-import-'+AUTH+'/import-'+target+'.json','import-'+target+'.json')
elif phase=='restage':
 assert hashes(T,OLD)==json.loads((D/'prepared.json').read_text())['expected'];ssh('sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(FILES+ARTIFACTS));assert hashes(S,FILES)==local;print('Stage atualizado;produção preservada')
elif phase=='exercise':
 assert hashes(S,FILES)==local;print(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/tests/history-pg.mjs',timeout=480));copyback(S+'/private/history-import-'+AUTH+'/stage-tests.json','stage-tests.json')
elif phase=='publish':
 p=json.loads((D/'prepared.json').read_text());assert hashes(T,OLD)==p['expected'];assert hashes(S,FILES)==local
 for f in ['stage-tests.json','local-tests.json','import-mgs_finance.json']:assert json.loads((D/f).read_text())['pass']
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip()
  try:
   ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(S)+');t=pathlib.Path('+repr(T)+');u=pwd.getpwnam("mgsfinance");'+'\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_name(p.name+".history-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);os.chmod(q,0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(T,FILES)==local
   ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  except Exception:
   ssh('sudo -n tar -xzf '+B+'/code-before.tar.gz -C '+T+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');raise
  after=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK)).strip();assert before==after
 save('published.json',{'pass':True,'files':local,'existing_financial_data_and_users_unchanged':True,'gateway_restart':False});print('Publicação coerente10arquivos;dados atuais/usuários preservados')
elif phase=='verify':
 assert hashes(T,FILES)==local;services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split();assert services==['active']*3
 counts=ssh(PG+'-d mgs_finance -c '+shlex.quote('SELECT period,count(*),sum(jsonb_array_length(payload->\'cells\')) FROM finance_history GROUP BY period ORDER BY period')).strip();assert len(counts.splitlines())==7
 grants=ssh(PG+'-d mgs_finance -c '+shlex.quote("SELECT has_table_privilege('mgsfinance','finance_history','SELECT'),has_table_privilege('mgsfinance','finance_history','INSERT'),has_table_privilege('mgsfinance','finance_history','UPDATE'),has_table_privilege('mgsfinance','finance_history','DELETE')")).strip();assert grants=='t|f|f|f'
 save('deploy-readback.json',{'pass':True,'services':services,'counts':counts,'history_grants':grants,'files':local});print(json.dumps({'pass':True,'services':services,'counts':counts,'history_grants':grants}))
else:raise ValueError('phase')
