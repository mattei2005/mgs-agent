"""Offline native inheritance canary gates, transport, recovery and parity."""
import copy
import tempfile
import unittest
from pathlib import Path
from ares_campaign_v3 import shein_general as general
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport, BatchResult, BatchTransportError
from test_shein_general_runtime import case

ROUTE='source_definition_native_inherit'

class NativeInheritanceTests(unittest.TestCase):
    def setUp(self):
        self.req,self.src,self.account,_=case(4)
        self.req.update(request_id='native-canary-test',quantity=1,budget_usd='100',authorized_by='344196393512075265')
        self.account['pure_clone_setup_policy']='PRESERVE_SOURCE_DEFINITION'
        first=self.src['ads'][0]
        first['creative']['degrees_of_freedom_spec']={'creative_features_spec':{
            'image_background_gen':{'enroll_status':'OPT_IN'},
            'text_optimizations':{'enroll_status':'OPT_IN'},
            'advantage_plus_creative':{'enroll_status':'OPT_OUT'}}}
        first['creative']['contextual_multi_ads']={'enroll_status':'OPT_OUT'}
        first['creative']['media_sourcing_spec']={'videos':[{'video_id':'video-source','source':'multi_media'}]}
        second=copy.deepcopy(first);second.update(id='11005',name='AD - 2');second['creative']['id']='11006';self.src['ads'].append(second)
        self.policy={'enabled':True,'stage':'CANARY_PAUSED_ONLY','approved_by':'344196393512075265',
            'source_message_id':'1568295434081014004','request_ids':['native-canary-test'],
            'source_campaign_ids':['11001'],'source_adset_ids':['11002'],'source_ad_ids':['11003','11005'],
            'budget_minor':10000,'max_campaigns':1,'max_ads':2}
        self.account['source_definition_native_inheritance']=copy.deepcopy(self.policy)
    def build(self):return general.build(self.req,self.src,114,self.account)
    def config(self,root):
        return {'enabled':True,'write_enabled':True,'require_account_registration':True,
            'accounts':{self.account['shein_profile']['account_id']:self.account},
            'state_root':str(root/'state'),'audit_root':str(root/'audit')}
    def test_compiler_selects_native_only_for_exact_canary(self):
        self.assertEqual(self.build()['campaigns'][0]['creative_materialization_route'],ROUTE)
    def test_other_request_keeps_normal_two_phase(self):
        self.req['request_id']='other';self.assertEqual(self.build()['campaigns'][0]['creative_materialization_route'],'source_definition_two_phase')
    def test_invalid_canary_parameters_fail_before_writer(self):
        for key,value in [('status','ACTIVE'),('budget_usd','101'),('quantity',2),('authorized_by','1291113428982693940')]:
            original=copy.deepcopy(self.req);self.req[key]=value
            with self.subTest(key=key),self.assertRaises((ValueError,ManifestError)):self.build()
            self.req=original
    def test_sealed_payload_keeps_all_expected_features_and_source_unchanged(self):
        before=copy.deepcopy(self.src);p=self.build()
        for ad in p['campaigns'][0]['ads']:
            self.assertEqual(ad['creative_payload']['degrees_of_freedom_spec'],self.src['ads'][0]['creative']['degrees_of_freedom_spec'])
        self.assertEqual(self.src,before)
    def test_native_plan_inherits_instead_of_resubmitting_flags(self):
        from ares_campaign_v3.planning import Planner
        p=self.build();m=Manifest.from_dict(p);plan=Planner().build(m);ops=[op for lane in plan.lanes.values() for b in lane for st in b.stages for op in st.operations if op.kind=='ad_copy_with_creative']
        self.assertEqual(len(ops),2)
        for op in ops:
            cp=op.body['creative_parameters'];self.assertNotIn('degrees_of_freedom_spec',cp)
            self.assertNotIn('media_sourcing_spec',cp);self.assertNotIn('contextual_multi_ads',cp)
            self.assertIn('object_story_spec',cp);self.assertIn('url_tags',cp)
            self.assertIn('c114',cp['object_story_spec']['video_data']['call_to_action']['value']['link'])
            self.assertEqual(op.body['status_option'],'PAUSED')
    def test_policy_cannot_admit_wrong_request_source_budget_or_active(self):
        from ares_campaign_v3 import shein_native_inheritance as native
        p=self.build()
        with tempfile.TemporaryDirectory() as directory:
            cfg=self.config(Path(directory));m=Manifest.from_dict(p);validate_account_policy(m,cfg)
            for change in ['request','account','source','budget','status','ads','policy']:
                q=copy.deepcopy(p);c=copy.deepcopy(cfg)
                if change=='request':q['request_id']='other'
                if change=='account':c['accounts'][m.campaigns[0].account_id]['operation']='OTHER'
                if change=='source':q['campaigns'][0]['source_campaign_id']='9'
                if change=='budget':q['campaigns'][0]['campaign_updates']['daily_budget']='10100'
                if change=='status':q['campaigns'][0]['status']='ACTIVE'
                if change=='ads':q['campaigns'][0]['ads'][0]['source_ad_id']='9'
                if change=='policy':c['accounts'][m.campaigns[0].account_id]['source_definition_native_inheritance']['approved_by']='other'
                with self.subTest(change=change),self.assertRaises((ValueError,ManifestError)):
                    validate_account_policy(Manifest.from_dict(q),c)
    def test_schema_rejects_nonvideo_or_missing_feature_and_post_substitution(self):
        p=self.build()
        for kind in ['feature','video','post']:
            q=copy.deepcopy(p);cp=q['campaigns'][0]['ads'][0]['creative_payload']
            if kind=='feature':cp['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']={'enroll_status':'OPT_OUT'}
            if kind=='video':cp['object_story_spec'].pop('video_data')
            if kind=='post':cp['object_story_id']='123_456'
            with self.subTest(kind=kind),self.assertRaises((ValueError,ManifestError)):Manifest.from_dict(q)
    def test_engine_runtime_uses_same_native_payload_and_never_standalone_create(self):
        class Transport(FakeBatchTransport):
            def __init__(self,account):super().__init__(account);self.operations=[]
            def execute(self,operations,stage):
                self.operations.extend(operations)
                return super().execute(operations,stage)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);payload=prevalidate_payload(self.build(),MediaRegistry(root/'registry.json'));aid=self.account['shein_profile']['account_id'];transport=Transport(aid)
            result=CampaignEngine(self.config(root),transport_factory=lambda a:transport).execute(Manifest.from_dict(payload))
            self.assertEqual(result['status'],'COMPLETE_PAUSED')
            copies=[o for o in transport.operations if o.kind=='ad_copy_with_creative'];self.assertEqual(len(copies),2)
            self.assertTrue(all('degrees_of_freedom_spec' not in o.body['creative_parameters'] for o in copies))
            self.assertFalse(any(o.kind=='creative_create' for o in transport.operations))
    def test_native_parameter_helper_does_not_mutate_expected_or_normal_route(self):
        from ares_campaign_v3.shein_native_inheritance import parameters
        c=Manifest.from_dict(self.build()).campaigns[0];before=copy.deepcopy(c.ads[0].creative_payload)
        q=parameters(c,c.ads[0]);self.assertEqual(c.ads[0].creative_payload,before)
        self.assertNotIn('degrees_of_freedom_spec',q)
        from dataclasses import replace
        normal=replace(c,creative_materialization_route='inline_copy');self.assertEqual(parameters(normal,normal.ads[0]),before)

if __name__=='__main__':unittest.main()
