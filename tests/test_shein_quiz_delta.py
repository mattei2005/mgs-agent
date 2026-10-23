"""Offline regressions: explicit SHEIN quiz delta, central core and QA unchanged."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case
from test_shein_single_clone_route import live_fixture
from ares_campaign_v3 import shein_general as general, shein_single_clone as route
from ares_campaign_v3.shein_quiz_delta import apply, target_base
from ares_campaign_v3.creative_media import source_links
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport


def fixture(index=2):
    r,s,a,_=case(index)
    p=a['shein_profile'];old=p['destination_base'];p['destination_base']=old.replace('/sh2-', '/sh3-')
    data=s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']
    data['link']=data['link'].replace('/sh2-', '/sh3-')
    a['pure_clone_setup_policy']='PRESERVE_SOURCE_DEFINITION'
    a['shein_naming']={'enabled':True,'route_regex':r'/quiz/us/sh([123])-g[0-9]{3}/','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}
    r['target_quiz_version']='v2'
    return r,s,a


class QuizDeltaTests(unittest.TestCase):
    def test_all_managers_clone_changes_only_destination_and_name(self):
        for i in range(6):
            r,s,a=fixture(i);before=copy.deepcopy(s);p=general.build(r,s,114,a);c=p['campaigns'][0]
            self.assertEqual(s,before);self.assertIn(' - v2 - ',c['name']);self.assertIn('COPY C110',c['name'])
            self.assertEqual(c['source_campaign_id'],s['campaign']['id']);self.assertNotIn('adset_updates',c)
            cp=c['ads'][0]['creative_payload'];links=source_links(cp,cp['object_story_spec'])
            self.assertTrue(all('/sh2-g' in link and 'c114' in link and 'c110' not in link for link in links))
            self.assertEqual(cp['url_tags'],'');self.assertEqual(cp['object_story_spec']['video_data']['message'],s['ads'][0]['creative']['object_story_spec']['video_data']['message'])
            route.validate_request(r);Manifest.from_dict(p)

    def test_omitted_delta_unchanged(self):
        r,s,a=fixture();r.pop('target_quiz_version');p=general.build(r,s,114,a)['campaigns'][0]
        self.assertIn(' - v3 - ',p['name']);self.assertIn('/sh3-g003/',source_links(p['ads'][0]['creative_payload'],p['ads'][0]['creative_payload']['object_story_spec'])[0])

    def test_invalid_intents_rejected_before_core(self):
        for delta in [{'target_quiz_version':'V2'},{'target_quiz_version':'v4'},{'target_quiz_version':2},{'mode':'clone_prestaged'},{'preserve_posts':True},{'source_account':'other'}]:
            r,s,a=fixture();r.update(delta)
            with self.subTest(delta=delta),self.assertRaises(ValueError):route.validate_request(r)

    def test_no_arbitrary_domain_or_manager_or_query_override(self):
        r,s,a=fixture()
        for base in ['https://yolokfx.com/quiz/us/sh3-g004/','https://yolokfx.com/arbitrary/','http://yolokfx.com/quiz/us/sh3-g003/','https://yolokfx.com/quiz/us/sh3-g003/?x=1']:
            p={**a['shein_profile'],'destination_base':base}
            with self.subTest(base=base),self.assertRaises(ValueError):target_base(r,p)

    def test_post_only_definition_rejected(self):
        r,s,a=fixture()
        with self.assertRaises(ValueError):apply({'object_story_id':'page_post'},r,a['shein_profile'])

    def test_flexible_package_preserves_media_rules_tags(self):
        r,s,a=fixture();base=a['shein_profile']['destination_base'];p={'object_story_spec':{'page_id':'p'},'asset_feed_spec':{'link_urls':[{'website_url':base+'?utm_campaign=c114'}],'videos':[{'video_id':'123','adlabels':[{'name':'vertical'}]}],'asset_customization_rules':[{'video_label':{'name':'vertical'}}]},'url_tags':'utm_campaign=c114'}
        before=copy.deepcopy(p);got=apply(p,r,a['shein_profile']);self.assertEqual(p,before)
        self.assertEqual(got['asset_feed_spec']['videos'],before['asset_feed_spec']['videos']);self.assertEqual(got['asset_feed_spec']['asset_customization_rules'],before['asset_feed_spec']['asset_customization_rules']);self.assertEqual(got['url_tags'],before['url_tags'])
        self.assertIn('/sh2-g003/?utm_campaign=c114',got['asset_feed_spec']['link_urls'][0]['website_url'])

    def test_wrong_destination_rejected_by_existing_QA(self):
        r,s,a=fixture();p=general.build(r,s,114,a)
        fixture_payload=copy.deepcopy(p);fixture_payload['campaigns'][0]['ads'][0]['creative_payload']['object_story_id']='2000000000000002_111'
        live=live_fixture(fixture_payload,s);live['campaign']['account_id']=a['shein_profile']['account_id']
        cp=copy.deepcopy(p['campaigns'][0]['ads'][0]['creative_payload']);cp.update(id='999',effective_object_story_id='2000000000000002_999')
        live['ads']['data'][0]['creative']=cp
        self.assertEqual(route.verify_readback(p,s,live),[])
        vd=live['ads']['data'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value'];vd['link']=vd['link'].replace('/sh2-','/sh3-')
        with self.assertRaises(ValueError):route.verify_readback(p,s,live)

    def test_core_execution_and_idempotent_replay_offline(self):
        r,s,a=fixture();p=general.build(r,s,114,a)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=prevalidate_payload(p,MediaRegistry(root/'media.json'));config={'enabled':True,'write_enabled':True,'accounts':{a['shein_profile']['account_id']:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            engine=CampaignEngine(config,transport_factory=lambda aid:FakeBatchTransport(aid));m=Manifest.from_dict(p);result=engine.execute(m)
            self.assertEqual(result['status'],'COMPLETE_PAUSED');self.assertEqual(result['campaign_ids'],engine.execute(m)['campaign_ids'])

if __name__=='__main__':unittest.main()
