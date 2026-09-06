"""Publish only reviewed static assets; preserve prior copies and verify hashes."""
import sys,pathlib,json,shlex,hashlib,argparse,re
parser=argparse.ArgumentParser();parser.add_argument('--change-id',required=True);args=parser.parse_args();assert re.fullmatch(r'[0-9]{18,20}',args.change_id);backup_suffix='.before-'+args.change_id
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';STATE=ROOT/'private/ui-redesign-1546005809845243944';manifest=json.loads((STATE/'deploy-evidence.json').read_text());files=['public/app.js','public/refinements.css'];expected={f:manifest['files'][f] for f in files}
check='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+'}))'
assert json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(check)))==expected
for f in files:
 content=(ROOT/f).read_bytes();h=hashlib.sha256(content).hexdigest()
 if h==expected[f]:continue
 code='import pathlib,sys,os,hashlib; p=pathlib.Path('+repr(TARGET+'/'+f)+'); data=sys.stdin.buffer.read(); assert hashlib.sha256(data).hexdigest()=='+repr(h)+'; backup_dir=p.parent.parent/"private"/"ui-static-backups"; backup_dir.mkdir(exist_ok=True); backup=backup_dir/(p.name+'+repr(backup_suffix)+'); assert not backup.exists(); backup.write_bytes(p.read_bytes()); backup.chmod(0o600); t=p.with_suffix(p.suffix+".pending"); t.write_bytes(data); t.chmod(0o600); os.replace(t,p); print(hashlib.sha256(p.read_bytes()).hexdigest())'
 assert ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),content).strip()==h;manifest['files'][f]=h
(STATE/'deploy-evidence.json').write_text(json.dumps(manifest,indent=2));print('static_asset_hash_readback_PASS')
