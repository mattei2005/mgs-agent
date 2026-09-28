from repair_helpers import *
import hashlib
W=Path(__file__).parent;R='/home/mgsfinance/backups/security-1551287899746598946'
VAULT='ghkdcenuzsp57w37nzhxuxnkj4'
vault=json.loads((W/'vault-map.json').read_text())
def get_password(item):
 d=op(['item','get',item,'--vault',VAULT,'--format','json'])
 return next(f['value'] for f in d['fields'] if f['id']=='password')
phase=sys.argv[1]
if phase=='prepare':
 ssh('sudo -n install -d -m 700 -o mgsfinance -g mgsfinance '+R)
 data=(W/'rotate-auth.mjs').read_bytes()
 ssh('sudo -u mgsfinance tee '+R+'/rotate-auth.mjs >/dev/null',input_data=data)
 assert ssh('sudo -u mgsfinance sha256sum '+R+'/rotate-auth.mjs').split()[0]==hashlib.sha256(data).hexdigest()
 ssh('sudo -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node --check '+R+'/rotate-auth.mjs')
 print('REMOTE_SCRIPT_VALIDATED')
 phase='check'
if phase=='vault':
 progress=W/'vault-rotation-status.json'
 done=json.loads(progress.read_text()) if progress.exists() else {}
 for user,item in vault.items():
  if user in done:continue
  old=get_password(item)
  op(['item','edit',item,'--vault',VAULT,'--generate-password=letters,digits,40','--format','json'])
  new=get_password(item);assert len(new)==40 and new!=old
  done[user]={'item_id':item,'new_password_readback':True};progress.write_text(json.dumps(done,indent=2))
  print('VAULT_ROTATED',user,flush=True)
elif phase in ['check','rotate']:
 if phase=='rotate':
  assert set(json.loads((W/'vault-rotation-status.json').read_text()))==set(vault)
  assert not any(json.loads((W/'secret-scan.json').read_text())['exact_protected_value_matches'].values())
 payload=json.dumps({'phase':phase,'credentials':{u:get_password(i) for u,i in vault.items()}}).encode()
 try:out=ssh('sudo -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+R+'/rotate-auth.mjs',input_data=payload,timeout=180)
 except Exception:
  print('Remote phase failed; no raw diagnostic emitted because input is sensitive. Reconcile DB audit before retry.');raise SystemExit(1)
 d=json.loads(out);(W/(phase+'-auth-result.json')).write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items() if k!='financial'}))
