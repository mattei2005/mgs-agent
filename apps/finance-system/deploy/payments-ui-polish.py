"""Bounded polish from public QA: mobile nav/date/scroll and one notice per poll."""
import pathlib,sys,json,io,tarfile,hashlib,shlex
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();state=R/'private/payments-1546642267291394199';target='/home/mgsfinance/releases/pg-auth-1545934831664242748';stage='/var/tmp/mgs-finance-payments-1546642267291394199';backup='/home/zeus/mgs-finance-backups/1546642267291394199';files=['public/operations.js','public/operations.css','deploy/finance-notices.mjs'];manifest=json.loads((state/'published.json').read_text());expected={f:manifest['files'][f] for f in files};current={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in files}
def hashes(where):return json.loads(ssh('sudo -n python3 -c '+shlex.quote('import pathlib,hashlib,json;p=pathlib.Path('+repr(where)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))')))
assert hashes(target)==expected,'Concurrent change; reconcile before modifying'
ssh('test ! -e '+backup+'/ui-polish-before.tar.gz && sudo -n tar -czf '+backup+'/ui-polish-before.tar.gz -C '+target+' '+' '.join(files)+' && sudo -n chown zeus:zeus '+backup+'/ui-polish-before.tar.gz && chmod 600 '+backup+'/ui-polish-before.tar.gz')
import base64
raw=base64.b64decode(ssh('base64 -w0 '+backup+'/ui-polish-before.tar.gz'),validate=True);copy=state/'ui-polish-before.tar.gz';copy.write_bytes(raw);copy.chmod(0o600);assert hashlib.sha256(raw).hexdigest()==ssh('sha256sum '+backup+'/ui-polish-before.tar.gz').split()[0]
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as t:
 for f in files:t.add(R/f,arcname=f)
ssh('sudo -n -u mgs_pg tar -xzf - -C '+stage,payload.getvalue());assert hashes(stage)==current
code='import pathlib,pwd,os;src=pathlib.Path('+repr(stage)+');dst=pathlib.Path('+repr(target)+');u=pwd.getpwnam("mgsfinance")\nfor f in '+repr(files)+':\n p=dst/f;t=p.with_suffix(p.suffix+".polish");t.write_bytes((src/f).read_bytes());os.chmod(t,0o600);os.chown(t,u.pw_uid,u.pw_gid);os.replace(t,p)'
ssh('sudo -n python3 -c '+shlex.quote(code));assert hashes(target)==current;manifest['files'].update(current);manifest['ui_polish']={'files':current,'before':expected,'backup':backup+'/ui-polish-before.tar.gz'};(state/'published.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'pass':True,'files':len(files),'financial_mutations':0}))
