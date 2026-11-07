"""Offline exact-review regressions; no network or Meta write."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from ares_campaign_v3 import shein_reviewed_background_batch as router
from ares_campaign_v3 import shein_reviewed_background as dispatch
from ares_campaign_v3.shein_continuation import APPROVED_RESUME, content_digest

ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1568723276719591606')
KIND='SHEIN_REVIEWED_BACKGROUND_BATCH_1568723276719591606'

class Yolo03BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.s=json.loads((ROOT/'state.before.json').read_text())
        self.cp=json.loads((ROOT/'checkpoint.before.json').read_text())
        self.bound=json.loads((ROOT/'binding.json').read_text())
        self.messages=json.loads((ROOT/'messages.json').read_text())
    def module(self):
        from ares_campaign_v3 import shein_reviewed_background_yolo03_20261107
        return shein_reviewed_background_yolo03_20261107
    def get(self,path):
        if '/messages?' in path:return [self.messages['1568650825184714936']]
        return self.messages[path.rsplit('/',1)[-1]]
    def context(self):
        mod=self.module();d=mod.make_descriptor(self.s,self.bound)
        return {'state':self.s,'checkpoint':self.cp,'descriptor':d,'verified':{
            'verified':True,'descriptor_digest':content_digest(d),
            'accepted_creative_features':{'binding_digest':mod.BINDING_DIGEST}}}
    def test_exact_router_selects_current_review(self):
        self.assertTrue(router.selected({'reviewed_creative_features_kind':KIND}))
    def test_request_only_smaller_inventory_pages(self):
        self.assertEqual(router.creative_inventory_limit(),500)
        marker=APPROVED_RESUME.set(self.context())
        try:self.assertEqual(router.creative_inventory_limit(),500)
        finally:APPROVED_RESUME.reset(marker)
    def test_valid_review_retains_now_five_slots_and_original_clock(self):
        from ares_campaign_v3.shein_continuation import validate_descriptor
        mod=self.module();d=mod.make_descriptor(self.s,self.bound)
        with patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'live':True}):
            v=validate_descriptor(d,self.s,self.cp,get_message=self.get)
        self.assertTrue(v['start_now']);self.assertFalse(v['late_activation_authorized'])
        self.assertEqual(v['original_execution_started_at'],self.s['execution_started_at'])
        self.assertEqual(d['quantity'],5);self.assertEqual(len(v['campaign_ids']),2)
    def test_immutable_budget_bid_clock_seals_source_and_initial_ids(self):
        mod=self.module()
        for key in ['budget_usd','bid_usd','request_id']:
            s=copy.deepcopy(self.s);s['request'][key]='bad'
            with self.subTest(key=key),self.assertRaises(ValueError):mod.require_binding(s,self.cp,self.bound)
        for key in ['execution_started_at','manifest','source']:
            s=copy.deepcopy(self.s);s[key]='changed'
            with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):mod.require_binding(s,self.cp,self.bound)
        cp=copy.deepcopy(self.cp);cp['bundles'][0]['campaign_ids'][0]='9'
        with self.assertRaises(ValueError):mod.require_binding(self.s,cp,self.bound)
    def test_review_content_identity_edit_and_undeclared_deltas_rejected(self):
        mod=self.module();d=mod.make_descriptor(self.s,self.bound)
        for field,value in [('content','não'),('edited_timestamp','changed'),('channel_id','9')]:
            old=copy.deepcopy(self.messages[mod.REVIEW_ID]);self.messages[mod.REVIEW_ID][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):mod.validate_descriptor(d,self.s,self.cp,get_message=self.get)
            self.messages[mod.REVIEW_ID]=old
        for key,value in [('start_now',False),('quantity',3),('reviewed_feature_omissions',{}),('late_activation_authorized',True)]:
            bad={**d,key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):mod.validate_descriptor(bad,self.s,self.cp,get_message=self.get)
    def test_review_must_reply_to_exact_report(self):
        mod=self.module();d=mod.make_descriptor(self.s,self.bound)
        self.messages[mod.REVIEW_ID]['message_reference']['message_id']='9'
        with self.assertRaises(ValueError):mod.validate_descriptor(d,self.s,self.cp,get_message=self.get)
    def test_only_background_changes_in_all_ten_sealed_ads(self):
        mod=self.module();before=copy.deepcopy(self.s);marker=APPROVED_RESUME.set(self.context())
        try:
            n=0
            for c in self.s['manifest']['campaigns']:
                for ad in c['ads']:
                    p=ad['creative_payload'];out=dispatch.effective(p);n+=1
                    self.assertEqual(out['degrees_of_freedom_spec']['creative_features_spec'][mod.FEATURE],{'enroll_status':'OPT_OUT'})
                    dispatch.verify_creative(out,p)
                    out['degrees_of_freedom_spec']['creative_features_spec'][mod.FEATURE]={'enroll_status':'OPT_IN'}
                    self.assertEqual(out,p)
                    with self.assertRaises(ValueError):dispatch.verify_creative(p,p)
            self.assertEqual(n,10)
        finally:APPROVED_RESUME.reset(marker)
        self.assertEqual(self.s,before)
    def test_normal_path_unchanged_and_threadpool_context_bound(self):
        from ares_campaign_v3.schema import Manifest
        mod=self.module();p=self.s['manifest']['campaigns'][0]['ads'][0]['creative_payload']
        self.assertIs(dispatch.effective(p),p)
        marker=APPROVED_RESUME.set(self.context())
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertTrue(dispatch.submit_lane(pool,lambda *a:mod.active_context() is not None,mod.ACCOUNT,(),mod.REQUEST,Manifest.from_dict(self.s['manifest']).digest).result())
                with self.assertRaises(ValueError):dispatch.submit_lane(pool,lambda *a:None,'9',(),mod.REQUEST,'9')
        finally:APPROVED_RESUME.reset(marker)
    def test_only_original_now_intent_can_pass_schedule_gate(self):
        mod=self.module();mod.require_original_now(self.s)
        for key,value in [('start_now',False),('status','PAUSED')]:
            s=copy.deepcopy(self.s);s['request'][key]=value
            with self.assertRaises(ValueError):mod.require_original_now(s)
        s=copy.deepcopy(self.s);s['target_manifest']['campaigns'][0]['start_intent']='SCHEDULED'
        with self.assertRaises(ValueError):mod.require_original_now(s)
    def test_all_new_slots_require_receipts_and_unique_ids(self):
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.planning import Planner
        mod=self.module();cp=copy.deepcopy(self.cp);cp['status']='COMPLETE'
        groups=Planner().build(Manifest.from_dict(self.s['manifest'])).lanes[mod.ACCOUNT]
        cp['bundles'][0]['status']='COMPLETE'
        cp['bundles'][0]['reviewed_creative_feature_resolution']=mod._receipt(self.bound,cp['bundles'][0]['idempotency_keys'])
        for g in groups[1:]:
            keys=[c.idempotency_key for c in g.campaigns]
            cp['bundles'].append({'index':g.index,'status':'COMPLETE','idempotency_keys':keys,
                'campaign_ids':[str(900000000000000+g.index*10+i) for i in range(len(keys))],
                'adset_ids':[str(800000000000000+g.index*10+i) for i in range(len(keys))],
                'sealed_manifest_digest':Manifest.from_dict(self.s['manifest']).digest,
                'reviewed_creative_feature_resolution':mod._receipt(self.bound,keys)})
        with patch.object(mod,'CHECKPOINT',SimpleNamespace(read_text=lambda:json.dumps(cp))):
            self.assertEqual(len(mod._final_slots(self.context())),5)
            cp['bundles'][1]['campaign_ids'][0]=cp['bundles'][0]['campaign_ids'][0]
            with self.assertRaises(ValueError):mod._final_slots(self.context())

if __name__=='__main__':unittest.main()
