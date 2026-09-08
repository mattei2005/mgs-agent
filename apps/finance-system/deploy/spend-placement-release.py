import pathlib,sys,json,hashlib,shlex,fcntl
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/spend-placement-1547012165150711858';sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();T='/home/mgsfinance/releases/pg-auth-1545934831664242748';F=T+'/public/app.js';B='/home/zeus/mgs-finance-backups/1547012165150711858-ui';old=json.loads((R/'private/spend-import-1546991137171181578/spend-published.json').read_text())['files']['public/app.js'];new=hashlib.sha256((R/'public/app.js').read_bytes()).hexdigest();assert json.loads((D/'ui-candidate.json').read_text())['pass'];assert ssh('sudo -n sha256sum '+F).split()[0]==old
with (R/'private/quote-sync.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);ssh('test ! -e '+B+' && sudo -n install -d -o zeus -g zeus -m700 '+B+' && sudo -n cp -p '+F+' '+B+'/app.js');assert ssh('sudo -n sha256sum '+B+'/app.js').split()[0]==old
 code='import pathlib,sys,os,hashlib;p=pathlib.Path('+repr(F)+');old='+repr(old)+';new='+repr(new)+';assert hashlib.sha256(p.read_bytes()).hexdigest()==old;b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==new;s=p.stat();q=p.with_suffix(".placement-pending");q.write_bytes(b);os.chmod(q,s.st_mode&0o777);os.chown(q,s.st_uid,s.st_gid);os.replace(q,p);assert hashlib.sha256(p.read_bytes()).hexdigest()==new'
 ssh('sudo -n python3 -c '+shlex.quote(code),(R/'public/app.js').read_bytes());assert ssh('sudo -n sha256sum '+F).split()[0]==new
out={'pass':True,'source_sha256':new,'backup':B+'/app.js','prior_sha256':old,'database_writes':0,'restart':False};(D/'ui-published.json').write_text(json.dumps(out));print(json.dumps(out))
