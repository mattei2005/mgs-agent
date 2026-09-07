"""Additional live Rodolfo request: Wantabrand site display only, no DB/Sheet mutation."""
import pathlib,sys,io,tarfile,shlex,json,hashlib,base64
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/wavesbee-1546607083468623912';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/1546607083468623912/app-before-wantabrand.js';STAGE='/var/tmp/mgs-finance-currency-1546607083468623912'
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
new=(ROOT/'public/app.js').read_text();old=new.replace('// Rodolfo: simplify the site display name; IDs/account bindings/history stay unchanged.\n','').replace("function siteDisplayName(name){return name==='Wantabrand US-CC-ES + Wantabrand BR-CAR-BR'?'Wantabrand':name;}\n",'').replace('esc(siteDisplayName(s.name))','esc(s.name)')
oldhash=hashlib.sha256(old.encode()).hexdigest();newhash=hashlib.sha256(new.encode()).hexdigest();remote=lambda p:ssh('sudo -n sha256sum '+p).split()[0]
assert remote(TARGET+'/public/app.js')==oldhash,'Concurrent frontend change; reconcile';assert '"sites" value="${esc(s.name)}"' in new
assert '# fail 0' in (STATE/'site-display-tests.log').read_text()
ssh('test ! -e '+BACKUP+' && sudo -n cp '+TARGET+'/public/app.js '+BACKUP+' && sudo -n chown zeus:zeus '+BACKUP+' && chmod 600 '+BACKUP)
raw=base64.b64decode(ssh('base64 -w0 '+BACKUP),validate=True);assert hashlib.sha256(raw).hexdigest()==oldhash;(STATE/'app-before-wantabrand.js').write_bytes(raw)
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as t:t.add(ROOT/'public/app.js',arcname='public/app.js')
ssh('sudo -n -u mgs_pg tar -xzf - -C '+STAGE,buf.getvalue());assert remote(STAGE+'/public/app.js')==newhash
code='import pathlib,shutil,os,pwd;t=pathlib.Path('+repr(TARGET+'/public/app.js')+');s=pathlib.Path('+repr(STAGE+'/public/app.js')+');p=t.with_suffix(".js.currency-staged");shutil.copy2(s,p);u=pwd.getpwnam("mgsfinance");os.chown(p,u.pw_uid,u.pw_gid);os.chmod(p,0o600);os.replace(p,t)'
assert remote(TARGET+'/public/app.js')==oldhash;ssh('sudo -n python3 -c '+shlex.quote(code));assert remote(TARGET+'/public/app.js')==newhash
(STATE/'wantabrand-deploy.json').write_text(json.dumps({'pass':True,'display_name':'Wantabrand','previous_name':'Wantabrand US-CC-ES + Wantabrand BR-CAR-BR','old_hash':oldhash,'new_hash':newhash,'backup':BACKUP,'db_writes':0,'sheet_writes':0,'restart':False},indent=2));print('Wantabrand display published/hash readback PASS; no DB/Sheet writes or restart')
