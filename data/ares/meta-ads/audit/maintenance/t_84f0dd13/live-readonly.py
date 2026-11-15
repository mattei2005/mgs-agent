import json,sys,time
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import shein_channel_authority as auth
from ares_campaign_v3 import target_start_revision as rev
old=rev.load(R/'data/ares/meta-ads/audit/maintenance/t_9700e988/handoff.json');receipt=rev.load(old['receipt']);cfg=rev.load(R/'data/ares/meta-ads/engine-v3/config.json');waves=[];started=time.monotonic()
for wave in range(3):
 c=rev.validate_local(receipt['request_path'],cfg,old['same_original_digest'],old['same_original_approval']);g=c['grant'];parent=rev._authority(g)
 path='/channels/'+g['source_thread_id'];t=auth._get(path);assert t['id']==g['source_thread_id'] and t['parent_id']==parent and t['guild_id']=='1185714635991679006'
 rows=[]
 for m in g['messages']:
  d=auth._get(path+'/messages/'+m['id']);assert d['id']==m['id'] and d['channel_id']==g['source_thread_id'] and d['author']['id']==m['author_id'] and bool(d['author'].get('bot'))==m['bot'] and rev.digest(d['content'])==m['content_digest']
  rows.append({'message_id':m['id'],'author_id':m['author_id'],'content_digest':m['content_digest'],'fresh_get_matches':True})
 waves.append({'wave':wave+1,'at':datetime.now(timezone.utc).isoformat(),'thread_fresh':True,'messages':rows})
result={'status':'PASS','waves':waves,'successful_fresh_gets':sum(1+len(w['messages']) for w in waves),'elapsed_seconds':time.monotonic()-started,'authority_cache_used':False,'injected_get_message':False,'rate_deadline_scopes':sorted(auth._READ_DEADLINES),'original_digest':g['approved_digest'],'original_approval':g['approval_message_id'],'asap_instruction':g['instruction_message_id'],'engine_meta_drive_calls':0}
rev.atomic_json(M/'triple-live-authority.json',result);print(json.dumps({k:v for k,v in result.items() if k!='waves'}))
