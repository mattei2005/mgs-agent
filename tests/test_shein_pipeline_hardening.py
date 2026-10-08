"""Offline regression for approved SHEIN pipeline hardening; never Meta writes."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3 import shein_single_clone as driver
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport


def flexible():
    r,s,a,_=case(1)
    c=s['ads'][0]['creative'];v=c['object_story_spec']['video_data']
    c['instagram_user_id']='ig-source'
    c['asset_feed_spec']={'videos':[{'video_id':'video-source','adlabels':[{'name':'vertical','id':'output-id'}]}],
        'bodies':[{'text':v['message']}],'titles':[{'text':v['title']}],
        'descriptions':[{'text':'description'}], 'call_to_action_types':['GET_OFFER'],
        'link_urls':[{'website_url':v['call_to_action']['value']['link']}], 'ad_formats':['AUTOMATIC_FORMAT'],
        'asset_customization_rules':[{'video_label':{'name':'vertical','id':'output-id'},'priority':1}],
        'reasons_to_shop':False,'shops_bundle':False}
    c['object_story_spec']={'page_id':a['shein_profile']['page_id']}
    return r,s,a


class HardeningTests(unittest.TestCase):
    def test_flexible_is_compiled_full_media_not_post_only(self):
        r,s,a=flexible();original=copy.deepcopy(s)
        p=compiler.build(r,s,114,a);spec=p['campaigns'][0];cp=spec['ads'][0]['creative_payload']
        self.assertEqual(spec['creative_materialization_route'],'full_media_two_phase')
        self.assertNotIn('object_story_id',cp)
        self.assertEqual(cp['object_story_spec']['instagram_user_id'],'ig-source')
        self.assertEqual(cp['asset_feed_spec']['videos'][0]['video_id'],'video-source')
        self.assertNotIn('id',cp['asset_feed_spec']['videos'][0]['adlabels'][0])
        self.assertIn('c114',cp['asset_feed_spec']['link_urls'][0]['website_url'])
        self.assertEqual(original,s)
        Manifest.from_dict(p)

    def test_flexible_explicit_post_preservation_does_not_get_overridden(self):
        r,s,a=flexible();r['preserve_posts']=True
        with self.assertRaisesRegex(ValueError,'post-preservation'):compiler.build(r,s,114,a)

    def test_single_active_is_created_paused_before_qa(self):
        r,s,a,_=case(1,status='ACTIVE');p=compiler.build(r,s,114,a)
        with tempfile.TemporaryDirectory() as d:
            creation,target,barrier=driver.seal_creation_pair(p,{'accounts':{a['shein_profile']['account_id']:a},'shein_batch_activation':{'enabled':True,'minimum_quantity':1}},MediaRegistry(Path(d)/'registry.json'))
        self.assertTrue(barrier);self.assertEqual(creation['campaigns'][0]['status'],'PAUSED');self.assertEqual(target['campaigns'][0]['status'],'ACTIVE')

    def test_checkpoint_records_uncertain_write_before_abrupt_interrupt(self):
        r,s,a,_=case(1);p=compiler.build(r,s,114,a)
        class StopTransport(FakeBatchTransport):
            def execute(self,operations,stage):
                if stage=='adset_copy':raise KeyboardInterrupt('offline abrupt termination')
                return super().execute(operations,stage)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=a['shein_profile']['account_id'];config={'enabled':True,'write_enabled':True,'accounts':{aid:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            from ares_campaign_v3.prevalidation import prevalidate_payload
            p=prevalidate_payload(p,MediaRegistry(root/'registry.json'))
            with self.assertRaises(KeyboardInterrupt):CampaignEngine(config,transport_factory=lambda _:StopTransport(aid)).execute(Manifest.from_dict(p))
            cp=json.loads(next((root/'state/checkpoints').glob('*.json')).read_text());rec=cp['bundles'][0]
            self.assertTrue(rec.get('campaign_ids'))
            self.assertEqual(rec['write_journal'][-1]['state'],'IN_FLIGHT')
            self.assertEqual(rec['write_journal'][-1]['stage'],'adset_copy')

    def test_outer_http_failure_keeps_current_usage_headers_and_never_retries_post(self):
        import io,urllib.error
        from unittest.mock import patch
        from ares_campaign_v3.transport import GraphBatchTransport,BatchOperation,BatchTransportError
        transport=GraphBatchTransport('100','v26.0','OFFLINE_ONLY')
        transport.last_outer_headers={'x-ad-account-usage':'stale'}
        error=urllib.error.HTTPError('https://graph.invalid/',429,'offline',{'X-Ad-Account-Usage':'fresh-pressure'},io.BytesIO(b'{"error":{"code":4}}'))
        with patch('urllib.request.urlopen',side_effect=error) as network,self.assertRaises(BatchTransportError):
            transport.execute([BatchOperation('write','POST','act_100/campaigns',body={'name':'OFFLINE'})],'offline')
        self.assertEqual(network.call_count,1);self.assertEqual(transport.last_outer_headers['x-ad-account-usage'],'fresh-pressure');error.close()

    def test_registry_cache_is_bound_to_account_asset_checksum(self):
        from ares_campaign_v3.media_registry import MediaNotReady
        with tempfile.TemporaryDirectory() as directory:
            registry=MediaRegistry(Path(directory)/'registry.json')
            registry.register(account_id='100',asset_id='asset',checksum='a'*64,vertical_video_id='ready-id',square_video_id=None,ready=True,upload_edge='ad_account_advideos',association_verified=True)
            self.assertEqual(registry.require_ready('100','asset','a'*64,required_variants=('vertical',))['vertical_video_id'],'ready-id')
            for account,checksum in [('other','a'*64),('100','b'*64)]:
                with self.assertRaises(MediaNotReady):registry.require_ready(account,'asset',checksum,required_variants=('vertical',))

    def test_media_qa_missing_runtime_fails_before_write(self):
        from ares_campaign_v3.preview_renderer import validate_runtime
        with self.assertRaisesRegex(ValueError,'before write'):validate_runtime({'enabled':True,'chrome_path':'/does/not/exist','python_path':'/does/not/exist'})

if __name__=='__main__':unittest.main()
