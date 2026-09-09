"""Bounded release/backup/stage verification for Rodolfo1547240897752604704."""
import sys,pathlib,json,hashlib,shlex,tarfile,io,base64,fcntl
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R));sys.path.insert(0,'/root/mgs-agent/scripts')
from finance_media_spend_sync import ssh,PG
from mgs_google_workspace_auth import load_env
load_env();A='1547240897752604704';D=R/'private'/('company-expenses-'+A);T='/home/mgsfinance/releases/pg-auth-1545934831664242748';B='/home/zeus/mgs-finance-backups/'+A+'-company-expenses';S='/var/tmp/mgs-finance-expenses-'+A;DB='mgs_finance_expenses_'+A
E='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';P=E+BIN+'psql -h /run/mgs-postgresql18 -U mgs_pg -At -v ON_ERROR_STOP=1 '
FILES=['public/app.js','company-expense-basis-cli.mjs'];CHECK="SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id;SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book;SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x;SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x;"
def save(n,x):
 p=D/n;p.write_text(json.dumps(x,ensure_ascii=False,indent=2));p.chmod(0o600)
def hashes(target,files):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;r=pathlib.Path('+repr(target)+');print(json.dumps({f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
def bundle(files):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as t:
  for f in files:t.add(R/f,arcname=f)
 return b.getvalue()
def run(target,database,mode,periods):
 owner='mgsfinance' if database=='mgs_finance' else 'mgs_pg';node='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node' if owner=='mgsfinance' else S+'/node';payload=json.dumps({'plan':json.loads((D/'plan.json').read_text()),'periods':periods,'mode':mode}).encode();return json.loads(ssh('sudo -n -u '+owner+' '+node+' '+target+'/company-expense-basis-cli.mjs '+database,payload,timeout=570))
phase=sys.argv[1];local={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in FILES};periods=json.loads((D/'plan.json').read_text())['periods']
if phase=='prepare':
 assert not (D/'prepared.json').exists();expected=hashes(T,['public/app.js']);lines=(R/'public/app.js').read_text().splitlines();old="function expenseOrder(a,b){return expenseDisplayName(a.label).localeCompare(expenseDisplayName(b.label),'pt-BR',{sensitivity:'base'});}"
 reverse='\n'.join(old if x.startswith('function expenseOrder(') else x for x in lines)+'\n';assert hashlib.sha256(reverse.encode()).hexdigest()==expected['public/app.js'],'Concurrent app origin needs reconciliation'
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(P+'-d mgs_finance -c '+shlex.quote(CHECK));ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m 700 '+B+' && sudo -n tar -czf '+B+'/code.tar.gz -C '+T+' public/app.js && sudo -n chown zeus:zeus '+B+'/code.tar.gz && '+E+BIN+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/data.dump',timeout=240)
 proofs={}
 for n in ['code.tar.gz','data.dump']:
  v=base64.b64decode(ssh('base64 -w0 '+B+'/'+n,timeout=180),validate=True);p=D/('backup-'+n);p.write_bytes(v);p.chmod(0o600);proofs[n]=hashlib.sha256(v).hexdigest();assert ssh('sha256sum '+B+'/'+n).split()[0]==proofs[n]
 ssh(E+BIN+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+E+BIN+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/data.dump',timeout=240);assert ssh(P+'-d '+DB+' -c '+shlex.quote(CHECK))==before
 files=[str(p.relative_to(R)) for pat in ['*.mjs','*.py','*-rules.json','manager-layout*.json','*-schema.sql'] for p in R.glob(pat)]+[str(p.relative_to(R)) for p in (R/'public').iterdir() if p.is_file()]
 ssh('sudo -n install -d -o mgs_pg -g mgs_pg -m 700 '+S+' && sudo -n -u mgs_pg tar -xzf - -C '+S,bundle(files),timeout=180)
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(T)+');t=pathlib.Path('+repr(S)+');(t/"private").mkdir();[shutil.copy2(s/"private"/f,t/"private"/f) for f in ["source.json","ui-model.json","source-sha256.txt","live-quotes.json"]];shutil.copytree(s/"node_modules",t/"node_modules");shutil.copy2("/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node",t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180);assert hashes(S,FILES)==local;save('prepared.json',{'pass':True,'expected':expected,'local':local,'backup':proofs,'before':before,'stage':S,'stage_database':DB});print('Dual-host backup hashes and exact isolated restore PASS')
elif phase=='stage':
 assert hashes(S,FILES)==local
 for mode,targets in [('apply',periods),('verify',periods),('fx-test',['2026-09','2027-12'])]:
  out=run(S,DB,mode,targets);save('stage-'+mode+'.json',out);assert out['pass'];print(json.dumps(out))
elif phase=='publish':
 p=json.loads((D/'prepared.json').read_text());assert hashes(T,['public/app.js'])==p['expected'];assert all(json.loads((D/('stage-'+m+'.json')).read_text())['pass'] for m in ['apply','verify','fx-test']);assert hashes(S,FILES)==local
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(S)+');t=pathlib.Path('+repr(T)+');u=pwd.getpwnam("mgsfinance");'+'\nfor f in '+repr(FILES)+':\n p=t/f;q=p.with_suffix(".company-pending");shutil.copy2(s/f,q);os.chown(q,u.pw_uid,u.pw_gid);q.chmod(0o600);os.replace(q,p)'
 before=ssh(P+'-d mgs_finance -c '+shlex.quote(CHECK));ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(T,FILES)==local;assert before==ssh(P+'-d mgs_finance -c '+shlex.quote(CHECK));save('published.json',{'pass':True,'files':local,'backup':B,'database_unchanged':True});print('Public file hash/readback PASS; no service restart')
elif phase=='apply':
 assert json.loads((D/'published.json').read_text())['pass'];targets=sys.argv[2:];assert targets and all(t in periods for t in targets)
 with (R/'private/quote-sync.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);out=run(T,'mgs_finance','apply',targets)
 save('live-apply-'+targets[0]+'.json',out);print(json.dumps(out))
elif phase=='verify':
 out=run(T,'mgs_finance','verify',periods);save('live-verify.json',out);print(json.dumps(out));print('services',ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket').split())
else:raise ValueError('phase')
