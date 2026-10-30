"""GET-only diagnostic of the exact real request; no executable manifests.
Uses central resolver on a diagnostic COPY of checkpoint, never production state.
"""
import copy,json,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl
B=Path('/root/mgs-agent');W=B/'work/t_9bf5723f'
sys.path[:0]=([str(W/'stage/scripts')] if '--stage' in sys.argv else [])+[str(B/'scripts')]
from ares_campaign_v3 import shein_single_clone as d, shein_request_queue as q, progress
from ares_campaign_v3.shein_channel_authority import _get
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.prevalidation import verify_prevalidation
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import BatchOperation,BatchResult
from ares_campaign_v3.image_sourcing import resolve_operations,effective,digest
R='shein-1565747351543480374';A='937846586033361'
intake=B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R
original=json.loads((intake/'request.json').read_text());ready=json.loads((intake/'request-ready.json').read_text())
assert hashlib.sha256((intake/'request.json').read_bytes()).hexdigest()=='7ff01bbaa739f9422d869e6a0419ea8def04209ee9d9cc16fff9af9950844faf'
assert all(ready.get(k)==v for k,v in original.items())
auth=q.authorize_queue_request(original,B)
message=_get('/channels/'+original['source_thread_id']+'/messages/'+original['source_message_id'])
assert message['author']['id']==original['authorized_by'] and not message['author'].get('bot')
confirmation=_get('/channels/'+original['source_thread_id']+'/messages/1565763298602000577')
assert confirmation['author']['id']=='344196393512075265'
state_path=B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/R/'state.json'
s=json.loads(state_path.read_text());assert s['request']==ready and s['phase']=='RECOVERY_PENDING'
assert s['manifest']==json.loads((state_path.parent/'manifest-sealed.json').read_text())
m=Manifest.from_dict(s['manifest']);target=Manifest.from_dict(s['target_manifest'])
assert verify_prevalidation(m.raw) and verify_prevalidation(target.raw)
assert len(m.campaigns)==8 and all(c.status=='PAUSED' and len(c.ads)==2 for c in m.campaigns)
assert all(c.status=='ACTIVE' for c in target.campaigns)
assert all(c.source_campaign_id=='120250750964580629' and c.campaign_updates['daily_budget']=='2500' and c.campaign_updates['bid_strategy']=='COST_CAP' and c.adset_updates['bid_amount']=='95' for c in m.campaigns)
config=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text());common=d._load_common()
token,_=common.get_token_from_1password(config['accounts'][A]['token_item'])
http_count=0
class GETOnly:
    def get(self,path,params):
        global http_count
        http_count+=1
        h,body,_=common.graph_get(path,token,params)
        if h!=200:raise RuntimeError('read-only Meta read failed HTTP '+str(h))
        return body
    def graph_get(self,path,token_unused,params):return 200,self.get(path,params),{}
    def graph_batch_get(self,token_unused,ops):
        return 200,[{'name':o['name'],'code':200,'body':self.get(o['path'],o.get('params') or {})} for o in ops],{}
client=GETOnly()
class ReadOnlyEngine:
    def __init__(self):self.config=config;self.calls=[]
    def _batch(self,bundle,transport,ops,stage):
        assert all(o.method=='GET' for o in ops),'mutation forbidden in maintenance'
        self.calls.append(stage);result=[]
        for op in ops:
            path,_,query=op.relative_url.partition('?')
            result.append(BatchResult(op.name,200,client.get(path,dict(parse_qsl(query)))))
        return result
live=[]
for cid in ['120250943717650629','120250943717660629','120250921178510629','120250921178500629']:
    c=client.get(cid,{'fields':'id,account_id,name,status,daily_budget,bid_strategy'})
    assert c['account_id']==A and c['status']=='PAUSED'
    sets=client.get(cid+'/adsets',{'fields':'id,campaign_id,account_id,status,bid_amount','limit':50})
    ads=client.get(cid+'/ads',{'fields':'id,name,status,source_ad_id,adset_id','limit':50})
    assert not sets.get('paging',{}).get('next') and not ads.get('paging',{}).get('next')
    new=cid.startswith('120250943717')
    assert c['daily_budget']==('2500' if new else '3500') and c['bid_strategy']=='COST_CAP'
    assert len(sets['data'])==1 and sets['data'][0]['status']=='PAUSED' and sets['data'][0]['bid_amount']==(95 if new else 90)
    if new:assert ads['data']==[]
    live.append({'campaign':c,'adsets':sets['data'],'ad_ids':[x['id'] for x in ads['data']]})
# Source is already sealed; fresh exact source ad GET verifies the causal fields only.
src=[]
for ad in s['source']['ads']:
    row=client.get(ad['id'],{'fields':'id,account_id,creative{id,object_story_spec,media_sourcing_spec}'})
    assert row['account_id']==A
    cr=row['creative'];spec=cr.get('media_sourcing_spec') or {}
    src.append({'ad_id':row['id'],'creative_id':cr['id'],'story_kind':'video' if (cr.get('object_story_spec') or {}).get('video_data') else 'other','sourcing_keys':sorted(spec),'sourcing_video_ids':[x['video_id'] for x in spec.get('videos',[])]})
registry=json.loads(Path(config['media_registry']).read_text())['records'];inventory={x['asset_id']:x for x in q.selected(ready,B)}
slots=[]
for ci,c in enumerate(m.campaigns,1):
    for ai,ad in enumerate(c.ads,1):
        md=ad.media;record=registry[A+'|'+md.asset_id+'|'+md.checksum]
        assert record['image_hash']==md.image_hash and record['ready'] and record['association_verified']
        assert record['media_type']=='image' and record['upload_edge']=='ad_account_adimages'
        assert inventory[md.asset_id]['reservation_request_id']==R
        cp=effective(ad.creative_payload)
        assert cp['media_sourcing_spec']['images'][0]['hash']==md.image_hash
        slots.append({'campaign_slot':ci,'ad_slot':ai,'idempotency_key':c.idempotency_key,'asset_id':md.asset_id,'checksum':md.checksum,'image_hash':md.image_hash,'sealed_creative_digest':digest(ad.creative_payload),'effective_creative_digest':digest(cp)})
assert len(slots)==16 and len({x['asset_id'] for x in slots})==16 and len({x['image_hash'] for x in slots})==16
library=client.get('act_'+A+'/adimages',{'fields':'hash,name,width,height','hashes':json.dumps([x['image_hash'] for x in slots]),'limit':100})
assert not library.get('paging',{}).get('next')
assert {x['hash'] for x in library.get('data',[])}=={x['image_hash'] for x in slots}
assert all(x.get('width',0)>0 and x.get('height',0)>0 for x in library['data'])
checkpoint=json.loads((Path(config['state_root'])/'checkpoints'/(R+'-'+A+'.json')).read_text())
bundle=CampaignEngine(config,transport_factory=lambda _:None).planner.build(m).lanes[A][0]
record=copy.deepcopy(checkpoint['bundles'][0]);record['sealed_manifest_digest']=m.digest
ops=[]
for ci,c in enumerate(bundle.campaigns,1):
    for ai,ad in enumerate(c.ads,1):
        ops.append(BatchOperation(f'recovery_ad_copy_{ci}_{ai}','POST',f'{ad.source_ad_id}/copies',body={'adset_id':record['adset_ids'][ci-1],'status_option':'PAUSED','creative_parameters':ad.creative_payload,'rename_options':{'rename_strategy':'NO_RENAME'}},kind='ad_copy_with_creative'))
prior=next(x for x in record['write_journal'] if x['stage']=='ad_copy_with_creative')
assert len(prior['operations'])==4
for op in ops:
    oldname=op.name.removeprefix('recovery_')
    logged=next(x for x in prior['operations'] if x['name']==oldname)
    assert logged['path']==op.relative_url
    assert logged['body_digest']==hashlib.sha256(json.dumps(op.body,sort_keys=True).encode()).hexdigest()
saves=[];marker=progress.CURRENT.set((record,lambda:saves.append(copy.deepcopy(record['image_sourcing_resolutions']))))
try:resolved=resolve_operations(ReadOnlyEngine(),bundle,None,record,ops)
finally:progress.CURRENT.reset(marker)
assert len(resolved)==4 and len(saves)==1 and len(saves[0])==4
plan=CampaignEngine(config,transport_factory=lambda _:None).dry_run(m)
job=json.loads((B/'data/ares/meta-ads/state/shein-campaigns/queue/jobs'/(R+'.json')).read_text())
assert job.get('dispatch_owner')=='foreground'
proof={'at':datetime.now(timezone.utc).isoformat(),'request_id':R,'authority_live':'PASS','original_author':message['author']['id'],'rodolfo_confirmation_id':confirmation['id'],'original_input_sha256':hashlib.sha256((intake/'request.json').read_bytes()).hexdigest(),'request_ready_sha256':hashlib.sha256((intake/'request-ready.json').read_bytes()).hexdigest(),'sealed_manifest_digest':m.digest,'target_manifest_digest':target.digest,'phase':s['phase'],'live':live,'source':src,'slots':slots,'first_bundle_resolution_receipts_DIAGNOSTIC_ONLY_NOT_EXECUTABLE':saves[0],'plan':plan,'queue_dispatch_owner':job['dispatch_owner'],'http_gets':http_count,'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,'production_state_writes':0,'meta_acceptance_verified':False,'serving_verified':False}
(W/'real-readonly-readiness.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:proof[k] for k in ['request_id','authority_live','phase','sealed_manifest_digest','http_gets','meta_writes','drive_writes','meta_acceptance_verified']}));print('validated real16 slots/registry/reservations; original8x2; existing2xPAUSED/zero ads; same manifest recovery4 slots; no executable manifest written')
