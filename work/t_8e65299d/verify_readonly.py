"""Foreground read-only verification for the queue-maintenance handoff."""
import json,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3 import shein_request_queue as q, shein_single_clone as d
from ares_campaign_v3.shein_channel_authority import _get
R='shein-1565747351543480374';O='shein-1565261967260647536-c3'
r=json.loads((B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R/'request.json').read_text())
a=q.authorize_queue_request(r,B)
original=_get('/channels/'+r['source_thread_id']+'/messages/'+r['source_message_id'])
assert original['author']['id']==r['authorized_by'] and not original['author'].get('bot')
review=_get('/channels/'+r['source_thread_id']+'/messages/1565343225894666345')
assert review['author']['id']=='1508864261504630925' and review['author'].get('bot')
messages=_get('/channels/'+r['source_thread_id']+'/messages?limit=100')
assert len(messages)<100,'incomplete history; paginate before classifying'
humans=[{'id':x['id'],'content':x['content']} for x in messages if not x['author'].get('bot') and int(x['id'])>int(review['id'])]
config=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text())
common=d._load_common();token,_=common.get_token_from_1password(config['accounts'][r['account']]['token_item'])
s=q.state(B,O);ids=s['engine_result']['campaign_ids'];campaigns=[]
for cid in ids:
    h,live,_=common.graph_get(cid,token,{'fields':'id,account_id,name,status,effective_status,daily_budget,bid_strategy'})
    assert h==200 and live['id']==cid and live['account_id']==r['account'] and live['status']=='PAUSED'
    assert live['daily_budget']=='3500' and live['bid_strategy']=='COST_CAP'
    campaigns.append({k:live.get(k) for k in ['id','account_id','name','status','effective_status','daily_budget','bid_strategy']})
rows=q.selected(r,B);assert len(rows)==16 and all(not x.get('reservation_request_id') for x in rows)
proof={'verified_at':datetime.now(timezone.utc).isoformat(),'request_id':R,'historical_request_id':O,
       'original':{'id':original['id'],'author_id':original['author']['id'],'content_sha256':hashlib.sha256(original['content'].encode()).hexdigest()},
       'review':{'id':review['id'],'author_id':review['author']['id'],'content':review['content']},
       'history_coverage':{'complete':True,'messages':len(messages),'humans_after_review':humans},
       'campaigns':campaigns,'selected_assets':len(rows),'selected_reservations':0,
       'dependencies_before_marker':q.dependencies(r,r['account'],B),'authority_live':'PASS',
       'meta_writes':0,'drive_writes':0,'uploads':0,'inventory_reservations':0}
(B/'work/t_8e65299d/live-readonly.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'authority_live':'PASS','review_content':review['content'],'humans_after_review':humans,'campaigns':campaigns,'selected_assets':len(rows),'deps':proof['dependencies_before_marker']},ensure_ascii=False))
