import pathlib,sys,json,hashlib,shlex,tarfile,io,base64,fcntl
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();A='1546991137171181578';D=R/('private/spend-import-'+A);T='/home/mgsfinance/releases/pg-auth-1545934831664242748';B='/home/zeus/mgs-finance-backups/'+A+'-history';S='/var/tmp/mgs-finance-histfresh-'+A;DB='mgs_finance_histfresh_'+A;E='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';PG=E+BIN+'psql -h /run/mgs-postgresql18 -U mgs_pg -At -v ON_ERROR_STOP=1 ';FILES=['history.mjs','history-source-import.mjs','history-source-cli.mjs'];OLD=['history.mjs'];CHECK="SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id;SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x;SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x;"
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as t:
  for f in files:t.add(R/f,arcname=f)
 return b.getvalue()
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;r=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def save(name,x):(D/name).write_text(json.dumps(x))
docs=[json.loads(p.read_text()) for p in sorted((D/'history-payloads').glob('*.json'))];assert len(docs)==40;payload=json.dumps(docs).encode();phase=sys.argv[1];local={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in FILES}
if phase=='prepare':
 assert not (D/'history-prepared.json').exists();before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK));expected=hashes(T,OLD)
 ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m 700 '+B+' && sudo -n tar -czf '+B+'/code.tar.gz -C '+T+' history.mjs && sudo -n chown zeus:zeus '+B+'/code.tar.gz && '+E+BIN+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/data.dump',timeout=240)
 proofs={}
 for n in ['code.tar.gz','data.dump']:
  v=base64.b64decode(ssh('base64 -w0 '+B+'/'+n,timeout=180),validate=True);(D/('history-backup-'+n)).write_bytes(v);proofs[n]=hashlib.sha256(v).hexdigest();assert ssh('sha256sum '+B+'/'+n).split()[0]==proofs[n]
 ssh(E+BIN+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+E+BIN+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/data.dump',timeout=240);assert ssh(PG+'-d '+DB+' -c '+shlex.quote(CHECK))==before
 fs=[str(p.relative_to(R)) for pat in ['*.mjs','*.py','*-rules.json','manager-layout*.json','*-schema.sql'] for p in R.glob(pat)]
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+S+' && sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(fs),timeout=180)
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(T)+');t=pathlib.Path('+repr(S)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(S,FILES)==local;out=json.loads(ssh('sudo -n -u mgs_pg '+S+'/node '+S+'/history-source-cli.mjs '+DB,payload,timeout=240));assert out['pass'] and out['verified']==40;save('history-prepared.json',{'pass':True,'stage':out,'backup':proofs,'expected':expected,'local':local});print('History40source documents: dual backup, restored PG stage and exact source readback PASS')
elif phase=='publish':
 p=json.loads((D/'history-prepared.json').read_text());assert p['pass'] and hashes(T,OLD)==p['expected'] and hashes(S,FILES)==local
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK))
  ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
  try:
   code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(S)+');t=pathlib.Path('+repr(T)+');u=pwd.getpwnam("mgsfinance");'+'\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_suffix(".source-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);q.chmod(0o600);os.replace(q,p)'
   ssh('sudo -n python3 -c '+shlex.quote(code));out=json.loads(ssh('sudo -n -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+T+'/history-source-cli.mjs',payload,timeout=240));assert out['pass'] and out['verified']==40
  finally:ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service')
  assert before==ssh(PG+'-d mgs_finance -c '+shlex.quote(CHECK));assert hashes(T,FILES)==local
 out.update(files=local,backup=B,services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket').split());assert out['services']==['active','active'];save('history-published.json',out);print(json.dumps({k:v for k,v in out.items() if k!='versions'}))
else:raise ValueError('phase')
