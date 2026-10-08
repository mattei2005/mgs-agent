"""Offline parity, isolation and core execution tests for general SHEIN routing."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_general as general
from ares_campaign_v3 import shein_single_clone as driver
from ares_campaign_v3 import shein_media_handoff as media
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.schema import Manifest

MANAGERS = ['409878085807112207','321263240782807040','432898782188011543','1214246869484576890','1291113428982693940','1055570806945620030']
CHANNELS = ['1548149087206121613','1548149300826079333','1548149483039236137','1548149654926135486','1548150015275438220','1548150155184701440']


def case(index=0, language='EN', mode='pure_clone', status='PAUSED'):
    code=f'G{index+1:03d}'; aid=str(1000000000000000+index); page=str(2000000000000000+index)
    prefix=f'b01fb{index+1:02d}'; domain='mavroa.com' if language=='ES' else 'yolokfx.com'
    base=f'https://{domain}/quiz/us/sh2-g{index+1:03d}/'
    alias=f'{"Mavroa" if language=="ES" else "Yolokfx"}-US-SHEIN-{language}-{index+1:02d}-{code}'
    profile={'account_id':aid,'account_name':alias,'manager_code':code,'manager_discord_id':MANAGERS[index],'channel_id':CHANNELS[index],
             'language':language,'timezone':'America/Los_Angeles' if index==0 else 'America/New_York','tracking_prefix':prefix,
             'utm_medium':f'g{index+1:03d}-s','destination_base':base,'page_id':page,'pixel_id':'pixel-test','status':'LIVE_SOURCE_READY'}
    src={'campaign':{'id':'11001','account_id':aid,'name':f'110 - PRODUCT - US-{language} ({prefix}c110) 07/10 event_add_to_wishlist','objective':'OUTCOME_SALES','daily_budget':'4000','bid_strategy':'LOWEST_COST_WITHOUT_CAP'},
         'adset':{'id':'11002','name':f'01 - ADGROUP - VIDEOS ({prefix}c110g01)','promoted_object':{'pixel_id':'pixel-test','custom_event_type':'ADD_TO_WISHLIST'},
                  'optimization_goal':'OFFSITE_CONVERSIONS','billing_event':'IMPRESSIONS','targeting':{'age_min':18,'age_max':65,'geo_locations':{'countries':['US']},'targeting_automation':{'advantage_audience':1}},'is_dynamic_creative':False,'attribution_spec':[{'event_type':'CLICK_THROUGH','window_days':7}]},
         'ads':[{'id':'11003','name':'AD - 1','adset_id':'11002','creative':{'id':'11004','effective_object_story_id':page+'_111',
                  'object_story_spec':{'page_id':page,'video_data':{'video_id':'video-source','title':'CLICK','message':'PRODUCTOS GRATIS' if language=='ES' else 'FREE PRODUCTS',
                  'call_to_action':{'type':'GET_OFFER_VIEW','value':{'link':base+f'?utm_source=facebook&utm_medium=g{index+1:03d}-s&utm_campaign={prefix}c110&utm_adgroup={prefix}c110g01'}}}}}}]}
    req={'request_id':f'general-offline-{code}-{mode}-{status}','account':alias,'source_number':110,'budget_usd':'30','start_time':'2030-10-08T00:00:00-04:00',
         'status':status,'authorized_by':MANAGERS[index],'source_channel_id':CHANNELS[index],'source_thread_id':'1557274000680288307','mode':mode}
    assets=[{'asset_id':f'asset-{index}-{i}','checksum':str(i+1)*64,'vertical_video_id':f'video-{index}-{i}','ready':True,
             'association_verified':True,'upload_edge':'ad_account_advideos','language':language,'canonical_filename':f'SHEIN_US_{language}_VID_FREE_PRODUCT_PV_{i+1:03d}.mp4','thumbnail_url':'https://example.test/thumb'} for i in range(3)]
    if mode!='pure_clone':req['_resolved_assets']=assets
    account={'alias':alias,'operation':'SHEIN-US-DIRECT','app_key':'test-shein-app','timezone':profile['timezone'],'ad_serving_route':'lineage_required_for_new_media',
             'marketing_api_access_tier':'standard_access',
             'supported_modes':['pure_clone','clone_prestaged','from_zero_prestaged'],'pure_clone_tracking_required':True,'shein_profile':profile,
             'campaign_policy':{'by_mode':{'pure_clone':{'pure_clone_allowed_update_keys':['daily_budget','bid_strategy']}}}}
    return req,src,account,assets


class GeneralTests(unittest.TestCase):
    def test_all_six_managers_all_three_modes_both_statuses_use_real_core_offline(self):
        tested=0
        for manager in range(6):
            for mode in ['pure_clone','clone_prestaged','from_zero_prestaged']:
                for status in ['PAUSED','ACTIVE']:
                    with self.subTest(manager=manager,mode=mode,status=status), tempfile.TemporaryDirectory() as directory:
                        root=Path(directory); req,src,account,assets=case(manager, 'ES' if manager==1 else 'EN', mode,status)
                        payload=general.build(req,src,114,account); registry=MediaRegistry(root/'media.json')
                        if mode!='pure_clone':
                            for a in assets:registry.register(account_id=account['shein_profile']['account_id'],asset_id=a['asset_id'],checksum=a['checksum'],vertical_video_id=a['vertical_video_id'],square_video_id=None,ready=True,upload_edge='ad_account_advideos',association_verified=True)
                        config={'enabled':True,'write_enabled':True,'require_account_registration':True,'accounts':{account['shein_profile']['account_id']:account},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
                        payload=prevalidate_payload(payload,registry)
                        result=CampaignEngine(config,transport_factory=lambda aid:FakeBatchTransport(aid)).execute(Manifest.from_dict(payload))
                        self.assertEqual(result['status'],'COMPLETE_PAUSED' if status=='PAUSED' else 'COMPLETE_FUTURE_ACTIVE')
                        self.assertEqual(len(result['campaign_ids']),1)
                        self.assertNotIn('source_campaign_id',payload['campaigns'][0]) if mode=='from_zero_prestaged' else self.assertEqual(payload['campaigns'][0]['source_campaign_id'],src['campaign']['id'])
                        self.assertNotIn('adset_updates',payload['campaigns'][0]);tested+=1
        self.assertEqual(tested,36)

    def test_rodolfo_and_owner_follow_same_compiler_and_payload(self):
        for i in range(6):
            r,s,a,_=case(i); owner=general.build(r,s,114,a)
            global_request={**r,'authorized_by':'344196393512075265'}
            ceo=general.build(global_request,s,114,a)
            self.assertEqual(owner['campaigns'],ceo['campaigns'])

    def test_cross_manager_and_wrong_parent_channel_rejected(self):
        for i in range(6):
            r,s,a,_=case(i)
            wrong={**r,'authorized_by':MANAGERS[(i+1)%6]}
            with self.assertRaises(ValueError):general.build(wrong,s,114,a)
            wrong={**r,'source_channel_id':CHANNELS[(i+1)%6]}
            with self.assertRaises(ValueError):general.build(wrong,s,114,a)

    def test_other_account_site_language_and_tracking_never_fallback(self):
        for change in ['account','site','prefix']:
            r,s,a,_=case(2)
            if change=='account':s['campaign']['account_id']='wrong'
            if change=='site':s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']['link']='https://example.test/'

            if change=='prefix':s['campaign']['name']=s['campaign']['name'].replace('b01fb03','b01fb02')
            with self.subTest(change=change),self.assertRaises(ValueError):general.build(r,s,114,a)

    def test_timezone_and_spanish_payload_are_account_scoped(self):
        r,s,a,_=case(0);p=general.build(r,s,114,a)['campaigns'][0]
        self.assertEqual(p['start_time'],'2030-10-07T21:00:00-07:00')
        self.assertIn('07/10',p['name'])
        r,s,a,_=case(1,'ES','clone_prestaged');p=general.build(r,s,114,a)['campaigns'][0]
        self.assertIn('US-ES',p['name'])
        self.assertEqual(p['ads'][0]['creative_payload']['object_story_spec']['video_data']['message'],'PRODUCTOS GRATIS')
        self.assertIn('g002-s',p['ads'][0]['creative_payload']['url_tags'])

    def test_context_isolation_and_reset(self):
        first=driver.CURRENT_PROFILE.set(case(3)[2]['shein_profile'])
        try:self.assertEqual(driver.account_id(),case(3)[2]['shein_profile']['account_id'])
        finally:driver.CURRENT_PROFILE.reset(first)
        self.assertEqual(driver.account_id(),driver.ACCOUNT_ID)

    def test_quantity_three_uses_two_plus_one_core_bundles(self):
        r,s,a,_=case(4);r['quantity']=3
        payload=general.build(r,s,114,a)
        self.assertEqual(len(payload['campaigns']),3)
        self.assertEqual(len({c['idempotency_key'] for c in payload['campaigns']}),3)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config={'enabled':True,'write_enabled':True,'accounts':{a['shein_profile']['account_id']:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            payload=prevalidate_payload(payload,MediaRegistry(root/'media.json'))
            engine=CampaignEngine(config,transport_factory=lambda aid:FakeBatchTransport(aid))
            plan=engine.dry_run(Manifest.from_dict(payload))
            self.assertEqual(len(plan['plan']['lanes'][a['shein_profile']['account_id']]),2)
            result=engine.execute(Manifest.from_dict(payload))
            self.assertEqual(len(result['campaign_ids']),3)

    def test_legacy_display_padding_and_tokens_remain_literal_in_source(self):
        for suffix, display in [('01','01'),('0101','101')]:
            r,s,a,_=case(4)
            r['source_number']=int(display)
            old='b01fb05c110';literal='b01fb05c'+suffix
            s['campaign']['name']=f'{display} - PRODUCT - US-EN ({literal}) event_add_to_wishlist'
            s['adset']['name']=s['adset']['name'].replace(old,literal)
            v=s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']
            v['link']=v['link'].replace(old,literal)
            before=copy.deepcopy(s);p=general.build(r,s,114,a)
            self.assertEqual(s,before)
            self.assertIn('b01fb05c114',p['campaigns'][0]['ads'][0]['creative_payload']['url_tags'])

    def test_new_name_uses_catalog_language_not_legacy_wrong_label(self):
        r,s,a,_=case(1,'ES')
        s['campaign']['name']=s['campaign']['name'].replace('US-ES','US-EN')
        original=s['campaign']['name'];p=general.build(r,s,114,a)
        self.assertIn('US-ES',p['campaigns'][0]['name'])
        self.assertEqual(s['campaign']['name'],original)
        self.assertEqual(p['campaigns'][0]['ads'][0]['creative_payload']['object_story_id'],s['ads'][0]['creative']['effective_object_story_id'])

    def test_media_language_and_identity_conflicts_fail_closed(self):
        for change in ['language','ready','duplicate','thumb']:
            r,s,a,_=case(2,'EN','from_zero_prestaged')
            if change=='language':r['_resolved_assets'][0]['language']='ES'
            if change=='ready':r['_resolved_assets'][0]['ready']=False
            if change=='duplicate':r['_resolved_assets'][1]['asset_id']=r['_resolved_assets'][0]['asset_id']
            if change=='thumb':r['_resolved_assets'][0]['thumbnail_url']=''
            with self.subTest(change=change),self.assertRaises(ValueError):general.build(r,s,114,a)

    def test_canonical_unreserved_media_rejected_before_drive_or_meta(self):
        r,s,a,assets=case(2,'EN','from_zero_prestaged');r.pop('_resolved_assets');r['asset_refs']=[{'asset_id':'not-reserved','checksum':'a'*64}]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'data/ares/creative-ops/inventory/assets.jsonl';path.parent.mkdir(parents=True);path.write_text(json.dumps({'asset_id':'not-reserved','reservation_request_id':'other-request'})+'\n')
            with patch.object(media,'_ops') as ops,self.assertRaisesRegex(ValueError,'reserved'):
                media.load_ready_assets(r,a['shein_profile'],root,None,None)
            # Credential resolution must not run until local reservation validation succeeds.
            ops.assert_not_called()

if __name__=='__main__':unittest.main()
