"""Exercise only pure build against saved receipts; no prepare, plans or API."""
import copy
import hashlib
import importlib.util
import json
import socket
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path('/root/mgs-agent')
sys.path.insert(0,str(ROOT/'scripts'))
module_path=Path(sys.argv[1]);receipt=Path(sys.argv[2]);baseline='--baseline' in sys.argv
from importlib.machinery import SourceFileLoader
spec=importlib.util.spec_from_loader('cta_receipt_probe',SourceFileLoader('cta_receipt_probe',str(module_path)))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
home=ROOT/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937'
load=lambda p:json.loads(p.read_text())
q=load(home/'request.json');source=load(home/'source-live.json');page=load(home/'target-page-live.json');assets=load(home/'selected-assets.json')
ledger_path=ROOT/m.naming.load_policy()['ledger_path'];allocation=load(ledger_path)['allocations'][q['request_id']]
old=copy.deepcopy([q,source,page,assets,allocation])
registry=m.MediaRegistry(ROOT/'data/ares/meta-ads/engine-v3/media-registry.json')
with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')),patch.object(m.subprocess,'run',side_effect=AssertionError('commands forbidden')):
    try:
        out=m.build(q,source,page,assets,registry,allocation)
    except ValueError as error:
        assert baseline and str(error)=='source CTA must be read exactly before rematerialization'
        result={'phase':'BASELINE_REPRODUCED','expected_error':str(error),'live_prepare':False,'meta_writes':0}
    else:
        assert not baseline
        c=out['campaigns'][0];assert len(out['campaigns'])==1 and len(c['ads'])==3
        assert c['name']==allocation['names'][0]=='304 - Viewer Loan - ENG - US - (pg_23189) - C01'
        assert c['campaign_create']['daily_budget']=='3500'
        assert c['start_time']==q['start_time']=='2026-11-15T00:02:00-05:00'
        assert c['mode']==m.MODE=='clone_target_prestaged'
        assert c['source_campaign_id']=='120251175890330629'
        assert c['source_adset_id']==source['adset']['id']
        checks=[]
        for a,original,asset in zip(c['ads'],source['ads'],assets):
            assert a['source_ad_id']==original['id']
            media=registry.require_ready(m.ACCOUNT,asset['asset_id'],asset['clean_checksum'])
            assert a['media']=={k:media[k] for k in ['asset_id','checksum','vertical_video_id','square_video_id','ready','upload_edge','association_verified']}
            creative=a['creative_payload'];afs=creative['asset_feed_spec']
            assert afs['call_to_action_types']==['APPLY_NOW']
            assert afs['call_to_actions']==[{'type':'APPLY_NOW','value':{'app_destination':'MESSENGER'}}]
            assert afs['bodies']==[{'text':q['copy']['primary_text']}]
            assert [t['text'] for t in afs['titles']]==[q['copy']['headline']]
            assert afs['descriptions']==[{'text':q['copy']['description']}]
            assert creative['object_story_spec']['page_id']==page['id']=='1355561690982225'
            assert creative['url_tags']==original['creative']['url_tags'].replace('utm_campaign=pg_23187','utm_campaign=pg_23189')
            checks.append({'source_ad_id':original['id'],'creative_id':original['creative']['id'],'cta':afs['call_to_action_types'][0],'media':a['media']})
        assert [q,source,page,assets,allocation]==old
        result={'phase':'OFFLINE_BUILD_VERIFIED','request_id':q['request_id'],'source_campaign_id':c['source_campaign_id'],'source_slot_order_preserved':True,'source_input_unchanged':True,'name':c['name'],'start_time':c['start_time'],'budget_minor':c['campaign_create']['daily_budget'],'mode':c['mode'],'ads':checks,'live_prepare':False,'meta_writes':0,'drive_writes':0,'reserve_calls':0,'uploads':0,'plans_or_manifests_written':False}
result['runner_sha256']=hashlib.sha256(module_path.read_bytes()).hexdigest()
receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
