"""Publish verified selected-month labels only; no restart or database write."""
import pathlib,json,sys,hashlib,shlex
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
STATE=ROOT/'private/networks-1546579646227943506';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/1546579646227943506';STAGE='/var/tmp/mgs-finance-networks-1546579646227943506';f='public/app.js'
assert json.loads((STATE/'local-browser.json').read_text())['pass'];expected=json.loads((STATE/'published-code.json').read_text())['files'][f]
assert ssh('sudo -n sha256sum '+TARGET+'/'+f).split()[0]==expected
ssh('sudo -n cp -p '+TARGET+'/'+f+' '+BACKUP+'/app-before-month-label.js && sudo -n chown zeus:zeus '+BACKUP+'/app-before-month-label.js && chmod 600 '+BACKUP+'/app-before-month-label.js')
old=ssh('python3 -c '+shlex.quote('from pathlib import Path;print(Path('+repr(BACKUP+'/app-before-month-label.js')+').read_text(),end="")'));(STATE/'app-before-month-label.js').write_text(old);assert hashlib.sha256(old.encode()).hexdigest()==expected
payload=(ROOT/f).read_bytes();h=hashlib.sha256(payload).hexdigest()
for target in [TARGET,STAGE]:
 command='import sys,pathlib,os;p=pathlib.Path('+repr(target+'/'+f)+');tmp=p.with_suffix(".network-label-stage");tmp.write_bytes(sys.stdin.buffer.read());st=p.stat();os.chown(tmp,st.st_uid,st.st_gid);os.chmod(tmp,st.st_mode);os.replace(tmp,p)'
 ssh('sudo -n python3 -c '+shlex.quote(command),payload);assert ssh('sudo -n sha256sum '+target+'/'+f).split()[0]==h
(STATE/'month-label-publish.json').write_text(json.dumps({'pass':True,'file':f,'before':expected,'after':h,'backup':BACKUP+'/app-before-month-label.js','restart':False,'database_writes':0},indent=2));print('Selected-month UI labels published; hashes and backup PASS')
