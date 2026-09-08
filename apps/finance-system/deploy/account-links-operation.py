"""Scoped data reconciliation; no app code, credentials, service or Meta writes."""
import pathlib,sys,json,shlex,hashlib,base64
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();AUTH='1546752274989191230';D=R/'private'/('account-links-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';B='/home/zeus/mgs-finance-backups/'+AUTH;S='/var/tmp/mgs-finance-account-links-'+AUTH;P='/home/mgsfinance/account-links-'+AUTH;DB='mgs_finance_links_'+AUTH;N='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';pe='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';pb='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';pg=pe+pb+'psql -h /run/mgs-postgresql18 -U mgs_pg -At -v ON_ERROR_STOP=1 ';check="SELECT id,revision,md5(overrides::text),md5(additions::text),md5(result::text) FROM scenarios ORDER BY id;"
def save(n,x):(D/n).write_text(json.dumps(x,indent=2))
phase=sys.argv[1]
if phase=='prepare':
 before=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip();assert not (D/'prepared.json').exists()
 ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m700 '+B+' && sudo -n tar -czf '+B+'/code-before.tar.gz -C '+TARGET+' accounts.mjs meta-lookup.mjs storage.mjs workspace.mjs && sudo -n chown zeus:zeus '+B+'/code-before.tar.gz && '+pe+pb+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+B+'/finance-before.dump && chmod 600 '+B+'/*',timeout=160)
 hashes={}
 for name in ['code-before.tar.gz','finance-before.dump']:
  raw=base64.b64decode(ssh('base64 -w0 '+B+'/'+name),validate=True);(D/name).write_bytes(raw);(D/name).chmod(0o600);h=hashlib.sha256(raw).hexdigest();assert ssh('sha256sum '+B+'/'+name).split()[0]==h;hashes[name]=h
 ssh(pe+pb+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB+' && '+pe+pb+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB+' < '+B+'/finance-before.dump',timeout=150);assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==before
 code='import pathlib,shutil,os,pwd;s=pathlib.Path('+repr(TARGET)+');t=pathlib.Path('+repr(S)+');t.mkdir(mode=0o700);[(shutil.copy2(f,t/f.name)) for f in s.glob("*.mjs")];shutil.copytree(s/"node_modules",t/"node_modules");(t/"private").mkdir();shutil.copytree(s/"private/meta-account-lookups",t/"private/meta-account-lookups");shutil.copy2('+repr(N)+',t/"node");u=pwd.getpwnam("mgs_pg");[os.chown(p,u.pw_uid,u.pw_gid) for p in [t,*t.rglob("*")]]'
 ssh('sudo -n python3 -c '+shlex.quote(code),timeout=100)
 for remote,user in [(S,'mgs_pg'),(P,'mgsfinance')]:
  if remote==P:ssh('sudo -n install -d -o mgsfinance -g mgsfinance -m700 '+P)
  for name in ['catalog-before.json','verified.json']:
   ssh('sudo -n -u '+user+' tee '+remote+'/'+name+' >/dev/null',(D/name).read_bytes())
  ssh('sudo -n -u '+user+' tee '+remote+'/link.mjs >/dev/null',(R/'deploy/reconcile-account-links.mjs').read_bytes())
 save('prepared.json',{'pass':True,'dual_backup_hashes':hashes,'restored_database':DB,'stage':S,'production_operation':P,'financial_before':before});print('Fresh dual backup/hash + isolated restore PASS')
elif phase in ['stage','apply']:
 assert json.loads((D/'prepared.json').read_text())['pass']
 if phase=='apply':assert json.loads((D/'stage-readback.json').read_text())['pass']
 stage=phase=='stage';remote=S if stage else P;user='mgs_pg' if stage else 'mgsfinance';app=S if stage else TARGET;node=S+'/node' if stage else N
 out=json.loads(ssh('sudo -n -u '+user+' env FINANCE_APP_ROOT='+app+' FINANCE_EVIDENCE_DIR='+remote+(' FINANCE_STAGE_DB='+DB if stage else '')+' '+node+' '+remote+'/link.mjs',timeout=90));assert out['pass'];save(phase+'-readback.json',out);print(json.dumps(out))
else:raise ValueError('Unknown phase')
