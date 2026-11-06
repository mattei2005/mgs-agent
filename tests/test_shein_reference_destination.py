"""Destination override canary: complete expectations, restricted transport."""
import copy
import unittest
import tempfile
from pathlib import Path
from ares_campaign_v3 import shein_general as g
from ares_campaign_v3 import shein_reference_destination as r
from ares_campaign_v3.schema import Manifest,ManifestError
from ares_campaign_v3.prevalidation import validate_account_policy
from ares_campaign_v3.planning import Planner
from test_shein_general_runtime import case

class ReferenceDestinationTests(unittest.TestCase):
    def setUp(self):
        self.req,self.source,self.account,_=case(4)
        self.req.update(request_id='destination-canary',authorized_by='344196393512075265',budget_usd='40',quantity=1)
        self.account['pure_clone_setup_policy']='PRESERVE_SOURCE_DEFINITION'
        self.source['ads'][0]['creative']['degrees_of_freedom_spec']={'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_IN'}}}
        other=copy.deepcopy(self.source['ads'][0]);other.update(id='11005',name='AD - 2');other['creative']['id']='11006';self.source['ads'].append(other)
        self.account[r.POLICY]={'enabled':True,'approved_by':'344196393512075265','request_ids':['destination-canary'],'source_campaign_id':'11001','source_adset_id':'11002','source_ad_ids':['11003','11005'],'source_creative_ids':['11004','11006'],'budget_minor':4000}
    def build(self):return g.build(self.req,self.source,114,self.account)
    def test_compiler_binds_exact_reference_ids_with_new_destination(self):
        before=copy.deepcopy(self.source);p=self.build();c=p['campaigns'][0]
        self.assertEqual(c['creative_materialization_route'],r.ROUTE)
        self.assertEqual({a['creative_payload']['creative_id'] for a in c['ads']},{'11004','11006'})
        self.assertTrue(all('c114' in a['creative_payload']['object_story_spec']['video_data']['call_to_action']['value']['link'] for a in c['ads']))
        self.assertEqual(self.source,before)
    def test_other_request_keeps_normal_route(self):
        self.req['request_id']='other';self.assertEqual(self.build()['campaigns'][0]['creative_materialization_route'],'source_definition_two_phase')
    def test_shape_and_policy_reject_unapproved_scope(self):
        p=self.build();m=Manifest.from_dict(p);cfg={'accounts':{m.campaigns[0].account_id:self.account}}
        validate_account_policy(m,cfg)
        for field,value in [('request_id','other'),('status','ACTIVE'),('creative_id','999')]:
            q=copy.deepcopy(p)
            if field=='request_id':q[field]=value
            if field=='status':q['campaigns'][0][field]=value
            if field=='creative_id':q['campaigns'][0]['ads'][0]['creative_payload'][field]=value
            with self.subTest(field=field),self.assertRaises((ValueError,ManifestError)):validate_account_policy(Manifest.from_dict(q),cfg)
    def test_changed_budget_and_quantity_rejected(self):
        for field,value in [('budget_usd','41'),('quantity',2),('status','ACTIVE')]:
            old=copy.deepcopy(self.req);self.req[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.build()
            self.req=old
    def test_initial_transport_and_final_reference_override_are_distinct(self):
        c=Manifest.from_dict(self.build()).campaigns[0];ad=c.ads[0]
        original=copy.deepcopy(ad.creative_payload);initial=r.parameters(c,ad);final=r.update_body(c,ad)
        self.assertEqual(initial['degrees_of_freedom_spec'],{})
        self.assertNotIn('creative_id',initial)
        self.assertEqual(final['creative']['creative_id'],ad.creative_payload['creative_id'])
        self.assertNotIn('degrees_of_freedom_spec',final['creative'])
        self.assertIn('c114',final['creative']['object_story_spec']['video_data']['call_to_action']['value']['link'])
        self.assertEqual(ad.creative_payload,original)
        self.assertEqual(original['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen'],{'enroll_status':'OPT_IN'})
    def test_plan_contains_no_standalone_creative_and_no_active_write(self):
        m=Manifest.from_dict(self.build());plan=Planner().build(m);ops=[o for b in plan.lanes[m.campaigns[0].account_id] for s in b.stages for o in s.operations]
        self.assertFalse(any(o.kind=='creative_create' for o in ops))
        updates=[o for o in ops if o.kind=='ad_name_update'];self.assertEqual(len(updates),2)
        self.assertTrue(all('creative_id' in o.body['creative'] and o.body['status']=='PAUSED' for o in updates))
    def test_normal_name_update_has_no_creative_change(self):
        from dataclasses import replace
        c=Manifest.from_dict(self.build()).campaigns[0];normal=replace(c,creative_materialization_route='inline_copy')
        self.assertEqual(r.update_body(normal,normal.ads[0]),{'name':normal.ads[0].name,'status':'PAUSED'})

if __name__=='__main__':unittest.main()
