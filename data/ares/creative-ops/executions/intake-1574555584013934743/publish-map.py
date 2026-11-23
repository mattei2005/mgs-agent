#!/usr/bin/env python3
"""Task-only audited map delivery; resumable exact readback, no threads."""
import sys,os,json,pathlib,hashlib,importlib.util,time
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
P=pathlib.Path(__file__).parent
RID='31313c81aa85d531bf1cc780281b2835';THREAD='1574555584013934743';BOT='1508864261504630925'
def sha(x):return hashlib.sha256(b.canonical(x)).hexdigest()
audit=b.read_json(P/'final-audit.json');mapping=b.read_json(P/'rename-map.json');req=b.read_json(b.DATA/'flat-intake-requests.json')['requests'][RID]
expected={s['id'] for s in req['sources']}
assert req['status']=='complete' and audit['status']=='complete' and audit['pending']==0
assert len(mapping)==len(expected)==24 and {x['source_id'] for x in mapping}==expected=={x['source_id'] for x in audit['proofs']}
assert all(x['metadata_clean_verified'] is True and x['permanent_verified'] is True for x in audit['proofs'])
units=[(x['source_id'],f"`{x['original']}`\n→ `{x['final']}`") for x in mapping]
chunks=[];current=[]
for u in units:
 if current and sum(len(x[1])+2 for x in current)+len(u[1])+150>1900:chunks.append(current);current=[]
 current.append(u)
if current:chunks.append(current)
parts=[{'source_ids':[u[0] for u in c],'content':f"**US · SHEIN · EN — mapa dos 24 vídeos ({i}/{len(chunks)})**\n\n"+'\n\n'.join(u[1] for u in c)} for i,c in enumerate(chunks,1)]
assert all(len(p['content'])<=2000 for p in parts)
for p in parts:p.update(sha256=sha(p['content']),nonce=str(int(sha(p['content'])[:15],16)))
assert {sid for p in parts for sid in p['source_ids']}==expected
outpath=P/'delivery-outbox.json';out=b.read_json(outpath)
if out:
 assert out['request_id']==RID and out['audit_sha256']==sha(audit)
 assert [{k:v for k,v in p.items() if k not in ['message_id','verified_at']} for p in out['parts']]==parts
else:
 out={'request_id':RID,'thread_id':THREAD,'audit_sha256':sha(audit),'parts':parts};b.atomic_json(outpath,out)
print('MAP_DRY_RUN_VALID',len(mapping),'sources',len(parts),'parts',flush=True)
if '--apply' not in sys.argv:sys.exit(0)
s=importlib.util.spec_from_file_location('aresposter','/root/mgs-agent/scripts/ares-discord-post-with-thread.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.load_env();token=os.environ['DISCORD_BOT_TOKEN']
def call(method,path,payload=None):
 for _ in range(5):
  status,x=m.discord_request(method,path,token,payload)
  if status==429:time.sleep(float(x['retry_after'])+1);continue
  assert status in [200,201],f'DISCORD_HTTP_{status}'
  return x
 raise RuntimeError('DISCORD_RETRY_LIMIT')
u=call('GET','/users/@me');assert u['id']==BOT and u['bot'] is True
for p in out['parts']:
 if not p.get('message_id'):
  existing=call('GET','/channels/'+THREAD+'/messages?limit=100');matches=[x for x in existing if x['author']['id']==BOT and x['content']==p['content']];assert len(matches)<=1
  msg=matches[0] if matches else call('POST','/channels/'+THREAD+'/messages',{'content':p['content'],'nonce':p['nonce'],'enforce_nonce':True,'allowed_mentions':{'parse':[]}})
  p['message_id']=msg['id'];b.atomic_json(outpath,out)
 msg=call('GET','/channels/'+THREAD+'/messages/'+p['message_id']);assert msg['author']['id']==BOT and msg['channel_id']==THREAD and msg['content']==p['content']
 p.setdefault('verified_at',b.now_iso());b.atomic_json(outpath,out);print('MAP_PART_VERIFIED',p['message_id'],flush=True)
b.atomic_json(P/'delivery-closure.json',{'status':'complete','request_id':RID,'received':24,'mapped':24,'pending':0,'audit_sha256':sha(audit),'message_ids':[p['message_id'] for p in out['parts']],'verified_at':b.now_iso()})
