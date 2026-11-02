import importlib.util,sys,json,tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
p='/root/.hermes/profiles/ares/scripts/shein-g004-cpr-watch-20261102.py'
s=importlib.util.spec_from_file_location('wtest',p);w=importlib.util.module_from_spec(s);sys.modules[s.name]=w;s.loader.exec_module(w)
m=w.load(w.ROOT/'manifest.json');d,delivery=w.helpers()
assert delivery.TID==w.TID==m['thread_id']
assert m['threshold_usd']=='1.30' and len(m['campaigns'])==5
snap={'observed_at':'2026-11-02T10:13:01-05:00','rows':{c['id']:{'number':c['number'],'cpr':'1.31','spend':'2.62','results':'2'} for c in m['campaigns']}}
text=w.text(snap,list(snap['rows']));assert '1,30' in text and 'Yolokfx' in text and '02/11' in text and 'Mavroa' not in text
assert all(c['number'] in text for c in m['campaigns'])
calls=[];remote={};posts=[]
class DC:
 def verify(self,b):assert b==[{'thread_id':m['thread_id'],'channel_id':m['parent_id']}]
 def call(self,method,path,payload=None):
  calls.append((method,path))
  assert path.startswith('/channels/'+m['thread_id']+'/messages')
  if method=='POST':
   assert payload['enforce_nonce'] is True and payload['allowed_mentions']['users']==[w.USER]
   posts.append(payload);remote.update(id='987654321',content=payload['content'],channel_id=m['thread_id'],author={'id':d.BOT_ID});return remote
  return remote
class Fake:
 BOT_ID=d.BOT_ID
 Discord=DC
with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
 run=Path(tmp)
 delivery.deliver(Fake,m,run,[text]);delivery.deliver(Fake,m,run,[text])
 assert len(posts)==1 and len([x for x in calls if x[0]=='GET'])==2
 assert w.load(run/'delivery-0.json')['status']=='GET_VERIFIED'
# Completed-slot replay must stop before scope, collection or posting.
class Args:initial=True;dry_run=False
with patch.object(w,'scope',side_effect=AssertionError('replay invoked scope')):
 result=w.execute(Args());assert result['status']=='COMPLETE'
assert not w.applicable(m,datetime.fromisoformat(m['expires_at']))
print(json.dumps({'status':'PASS','checks':['destination','labels','coverage_5','nonce','exact_GET','delivery_replay','completed_slot_replay','expiry'],'posts_mock_only':len(posts),'external_posts':0}))
