from repair_helpers import *
import hashlib,time
W=Path(__file__).parent
# Read protected configuration only into process memory; never emit values.
auth=json.loads(ssh('sudo -u mgsfinance /bin/cat /home/mgsfinance/.config/finance/auth.json'))
assert auth.get('mfa_required') is True and len(auth.get('mfa_key',''))==64
patterns={k:str(auth[k]).encode() for k in ('mfa_key','hash','salt')}
items=op(['item','list','--format','json'])
users=['geizian','icaro','isliago','joe','kelly','nicolas']
vault={}
for user in users:
 found=[x for x in items if x['title'].lower()==f'mgs finance - {user} - dash.mgsdigitalcorp.com']
 assert len(found)==1,user
 item=op(['item','get',found[0]['id'],'--vault',found[0]['vault']['id'],'--format','json']);fields=item['fields']
 username=next(f.get('value') for f in fields if f.get('id')=='username')
 assert username.lower()==user
 assert not item.get('passkeys'), 'Passkey-bearing item needs separate writer'
 vault[user]=item['id']
print('VAULT_IDENTITY_CHECK',json.dumps(vault))
(W/'vault-map.json').write_text(json.dumps(vault))
# One streaming pass over all reachable Git blobs, including historical binaries.
objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd='/root/mgs-agent').splitlines()
ids=list(dict.fromkeys(line.split(b' ',1)[0] for line in objects))
p=subprocess.Popen(['git','cat-file','--batch'],cwd='/root/mgs-agent',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
hits={k:[] for k in patterns};blob_count=0;total=0;t=time.monotonic()
try:
 for oid in ids:
  p.stdin.write(oid+b'\n');p.stdin.flush();header=p.stdout.readline().split();size=int(header[2]);kind=header[1];remaining=size;overlap=b'';matched=set()
  while remaining:
   chunk=p.stdout.read(min(1048576,remaining));assert chunk;remaining-=len(chunk)
   if kind==b'blob':
    content=overlap+chunk
    for k,v in patterns.items():
     if v in content:matched.add(k)
    overlap=content[-256:];total+=len(chunk)
  assert p.stdout.read(1)==b'\n'
  if kind==b'blob':blob_count+=1
  for k in matched:hits[k].append(oid.decode())
finally:
 p.stdin.close();p.wait(timeout=30)
r={'mfa_required':auth['mfa_required'],'reachable_objects':len(ids),'blobs_scanned':blob_count,'bytes_scanned':total,'exact_protected_value_matches':{k:len(v) for k,v in hits.items()},'elapsed_seconds':round(time.monotonic()-t,1),'scope':'all currently reachable local Git refs; exact protected config values; does not exclude untracked remote caches or transformed values'}
(W/'secret-scan.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
assert not any(hits.values()),'Protected configuration found in Git: broader incident requires escalation'
