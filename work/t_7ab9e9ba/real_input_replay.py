"""Read-only real-source contract replay; synthetic image registry is test-only.
No manifest is saved or passed to a writer. This is NOT live media readiness.
"""
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
B=Path('/root/mgs-agent');C=B/'work/t_7ab9e9ba/candidate'
sys.path.insert(0,str(C/'scripts'))
from ares_campaign_v3 import shein_single_clone as d, shein_general as g
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload,validate_account_policy
from ares_campaign_v3.engine import CampaignEngine
rpath=B/'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request.json'
before=hashlib.sha256(rpath.read_bytes()).hexdigest();r=json.loads(rpath.read_text());d.validate_request(r)
cfg=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text());a=copy.deepcopy(cfg['accounts'][r['account']]);p=a['shein_profile']
p['channel_authorization_policy']=json.loads((B/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())['channel_authorization_policy'];g.authorize(r,p,force=True)
common=d._load_common();token,_=common.get_token_from_1password(a['token_item']);ro=d.ReadOnlyClient(common)
pre=d._batch(ro,token,[{'name':'account','path':'act_'+r['account'],'params':{'fields':'id,name,currency,timezone_name,account_status,disable_reason,user_tasks'}},{'name':'campaigns','path':'act_'+r['account']+'/campaigns','params':{'fields':'id,name,status','limit':500}}])
import re
all_campaigns=d._complete_edge(pre['campaigns']);sources=[x for x in all_campaigns if (m:=re.match(r'^([0-9]+)\s*-',x.get('name',''))) and int(m[1])==r['source_number']]
assert len(sources)==1
cid=sources[0]['id']
raw=d._batch(ro,token,[{'name':'campaign','path':cid,'params':{'fields':'id,account_id,name,status,objective,daily_budget,bid_strategy,buying_type,special_ad_categories,special_ad_category_country'}},{'name':'adsets','path':cid+'/adsets','params':{'fields':'id,name,status,start_time,bid_amount,bid_constraints,bid_strategy,billing_event,optimization_goal,targeting,attribution_spec,promoted_object,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities','limit':50}},{'name':'ads','path':cid+'/ads','params':{'fields':'id,name,status,source_ad_id,adset_id,creative{id,name,object_story_id,effective_object_story_id,object_story_spec,asset_feed_spec,instagram_user_id,contextual_multi_ads,media_sourcing_spec,url_tags,degrees_of_freedom_spec}','limit':50}}])
sets=[x for x in d._complete_edge(raw['adsets']) if x.get('status') not in {'DELETED','ARCHIVED'}];ads=[x for x in d._complete_edge(raw['ads']) if x.get('status') not in {'DELETED','ARCHIVED'}];assert len(sets)==1
for ad in ads:
    if not ad['creative'].get('object_story_spec'):
        parent=d._batch(ro,token,[{'name':'parent','path':ad['source_ad_id'],'params':{'fields':'id,creative{effective_object_story_id,object_story_spec,asset_feed_spec,instagram_user_id}'}}])['parent']['creative']
        assert parent['effective_object_story_id']==ad['creative']['effective_object_story_id'];ad['_reference_story']=parent['object_story_spec']
s={'campaign':raw['campaign'],'adset':sets[0],'ads':ads};source_before=copy.deepcopy(s)
stories=[ad['creative'].get('object_story_spec') or ad.get('_reference_story') for ad in ads];p['page_id']=stories[0]['page_id']
from ares_campaign_v3.creative_media import source_links
links={link.split('?')[0] for ad,story in zip(ads,stories) for link in source_links(ad['creative'],story)};assert len(links)==1;p['destination_base']=next(iter(links))
names=[f for group in r['campaign_groups'] for f in group['files']]
rows=[json.loads(line) for line in (B/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()];byname={x['canonical_filename']:x for x in rows if x.get('canonical_filename') in names};assert len(byname)==16
assets=[{'asset_id':byname[n]['asset_id'],'checksum':byname[n]['clean_checksum'],'canonical_filename':n,'language':'ES','media_type':'image','image_hash':f'{i+1:032x}','upload_edge':'ad_account_adimages','association_verified':True,'ready':True} for i,n in enumerate(names)]
number=max(int(m[1]) for x in all_campaigns if (m:=re.match(r'^([0-9]+)\s*-',x.get('name',''))))+1
with tempfile.TemporaryDirectory(prefix='shein-img-contract-') as temp:
    root=Path(temp);reg=MediaRegistry(root/'synthetic-registry.json')
    for x in assets:reg.register_image(account_id=r['account'],asset_id=x['asset_id'],checksum=x['checksum'],image_hash=x['image_hash'],ready=True,association_verified=True)
    payload=g.build({**r,'_resolved_assets':assets},s,number,a)
    sealed=prevalidate_payload(payload,reg);manifest=Manifest.from_dict(sealed)
    local=copy.deepcopy(cfg);local['state_root']=str(root/'state');local['audit_root']=str(root/'audit');local['accounts'][r['account']]=a
    validate_account_policy(manifest,local)
    plan=CampaignEngine(local,transport_factory=lambda _:(_ for _ in ()).throw(AssertionError('writer forbidden'))).dry_run(manifest)
    campaigns=payload['campaigns'];assert [len(c['ads']) for c in campaigns]==[2]*8
    assert all(c['campaign_updates']['daily_budget']=='2500' and c['campaign_updates']['bid_strategy']=='COST_CAP' and c['adset_updates']['bid_amount']=='95' for c in campaigns)
    assert all(c['start_time']==r['start_time'] and c['status']=='ACTIVE' for c in campaigns)
    for c,group in zip(campaigns,r['campaign_groups']):
        assert [ad['creative_payload']['object_story_spec']['link_data']['message'] for ad in c['ads']]==[group['primary_text']]*2
    assert source_before==s and before==hashlib.sha256(rpath.read_bytes()).hexdigest()
    receipt={'request_id':r['request_id'],'real_input_unchanged':True,'source_live_campaign_id':cid,'source_adsets':len(sets),'source_ads':len(ads),'account_http_200':pre['account']['id']=='act_'+r['account'],'intake_validation':'PASS','contract_replay':'PASS','campaigns':len(campaigns),'images':len(assets),'daily_budget_minor_each':2500,'daily_budget_minor_total':sum(int(c['campaign_updates']['daily_budget']) for c in campaigns),'bid_strategy':'COST_CAP','bid_amount_minor':95,'original_start_time':r['start_time'],'status_intent':r['status'],'source_unchanged':True,'plan':plan,'IMPORTANT':'Image hashes/readiness/association are SYNTHETIC in an isolated test registry. No ready request or executable manifest saved. Actual prestage, live validation/plan, all-image previews and ACTIVE readback remain Ares work.','meta_writes':0,'drive_writes':0,'inventory_writes':0,'uploads':0}
    (B/'work/t_7ab9e9ba/real-input-contract-replay.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False))
