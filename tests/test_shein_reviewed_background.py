"""Offline exact-request recovery tests; no network or Meta writes."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from ares_campaign_v3 import shein_reviewed_background as mod
from ares_campaign_v3.shein_continuation import APPROVED_RESUME, content_digest

ROOT = Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1566522041530843238')

class ReviewedBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.state=json.loads((ROOT/'state.before.json').read_text())
        self.checkpoint=json.loads((ROOT/'checkpoint.before.json').read_text())
        self.bound=json.loads((ROOT/'binding.json').read_text())
        self.desc={'reviewed_creative_features':self.bound,'reviewed_creative_features_kind':mod.KIND,
                   'source_message_id':mod.ORIGINAL_ID,'source_message_content':mod.ORIGINAL,
                   'source_thread_id':mod.ORIGIN,'authorized_by':mod.HUMAN}
        self.messages={mid:{'id':mid,'channel_id':mod.ORIGIN,'author':{'id':actor,'bot':bot},
                            'content':text,'edited_timestamp':None}
                       for mid,text,actor,bot in [(mod.ORIGINAL_ID,mod.ORIGINAL,mod.HUMAN,False),
                           (mod.PROMPT_ID,mod.PROMPT,mod.ARES,True),(mod.REVIEW_ID,mod.REVIEW,mod.HUMAN,False)]}
    def get_message(self,path):
        if '/messages?' in path:return [self.messages[mod.PROMPT_ID]]
        return self.messages[path.rsplit('/',1)[-1]]
    def context(self):
        proof={'verified':True,'accepted_creative_features':{'binding_digest':mod.BINDING_DIGEST},
               'descriptor_digest':content_digest(self.desc)}
        return {'descriptor':self.desc,'state':self.state,'checkpoint':self.checkpoint,'verified':proof}
    def test_valid_review(self):
        with patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'source':'test'}) as p:
            proof=mod.validate_review(self.desc,self.state,self.checkpoint,get_message=self.get_message)
        self.assertEqual(proof['binding_digest'],mod.BINDING_DIGEST);p.assert_called_once()
    def test_normal_request_unchanged(self):
        self.assertIsNone(mod.validate_review({},self.state,self.checkpoint,get_message=self.get_message))
        cp=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload']
        self.assertEqual(mod.effective(cp),cp)
    def test_only_one_field_changes_without_mutating_original(self):
        before=copy.deepcopy(self.state);cp=before['manifest']['campaigns'][0]['ads'][0]['creative_payload']
        marker=APPROVED_RESUME.set(self.context())
        try:
            changed=mod.effective(cp);self.assertEqual(mod.effective(changed),changed)
        finally:APPROVED_RESUME.reset(marker)
        self.assertEqual(changed['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen'],{'enroll_status':'OPT_OUT'})
        changed['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']={'enroll_status':'OPT_IN'}
        self.assertEqual(changed,cp);self.assertEqual(self.state,before)
    def test_reject_scope_drift(self):
        for path,value in [('account_id','999'),('request_id','other'),('execution_started_at','later'),('creation_digest','0'*64),('target_digest','0'*64)]:
            with self.subTest(path=path):
                changed=copy.deepcopy(self.desc);changed['reviewed_creative_features'][path]=value
                with self.assertRaises(ValueError):mod.validate_review(changed,self.state,self.checkpoint,get_message=self.get_message)
    def test_reject_shell_lineage_and_seal_drift(self):
        for variant in ['shell','source','manifest','clock']:
            s=copy.deepcopy(self.state);c=copy.deepcopy(self.checkpoint)
            if variant=='shell':c['bundles'][0]['campaign_ids'][0]='999'
            if variant=='source':s['source']['ads'][0]['id']='999'
            if variant=='manifest':s['manifest']['campaigns'][0]['campaign_updates']['daily_budget']='1'
            if variant=='clock':s['execution_started_at']='2026-11-01T18:39:19+00:00'
            with self.subTest(variant=variant),self.assertRaises(ValueError):mod.validate_review(self.desc,s,c,get_message=self.get_message)
    def test_reject_changed_review(self):
        for field,value in [('content','não'),('edited_timestamp','changed'),('channel_id','999')]:
            with self.subTest(field=field):
                original=copy.deepcopy(self.messages[mod.REVIEW_ID]);self.messages[mod.REVIEW_ID][field]=value
                with self.assertRaises(ValueError):mod.validate_review(self.desc,self.state,self.checkpoint,get_message=self.get_message)
                self.messages[mod.REVIEW_ID]=original
    def test_reject_ambiguous_context(self):
        def messages(path):
            if '/messages?' in path:return [self.messages[mod.PROMPT_ID],{'id':str(int(mod.PROMPT_ID)+1),'author':{'id':mod.HUMAN},'content':'other decision'}]
            return self.get_message(path)
        with self.assertRaises(ValueError):mod.validate_review(self.desc,self.state,self.checkpoint,get_message=messages)
    def test_reject_unbound_payload(self):
        cp=copy.deepcopy(self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload']);cp['name']='unexpected'
        marker=APPROVED_RESUME.set(self.context())
        try:
            with self.assertRaises(ValueError):mod.effective(cp)
        finally:APPROVED_RESUME.reset(marker)
    def test_activation_feature_must_be_opt_out(self):
        cp=self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload'];marker=APPROVED_RESUME.set(self.context())
        try:
            changed=mod.effective(cp);mod.verify_creative(changed,cp)
            with self.assertRaises(ValueError):mod.verify_creative(cp,cp)
        finally:APPROVED_RESUME.reset(marker)
    def test_lane_context_propagation(self):
        from concurrent.futures import ThreadPoolExecutor
        from ares_campaign_v3.schema import Manifest
        manifest=Manifest.from_dict(self.state['manifest']);marker=APPROVED_RESUME.set(self.context())
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                result=mod.submit_lane(pool,lambda *args: mod.active_context() is not None,
                    self.bound['account_id'],(),self.bound['request_id'],manifest.digest).result()
                self.assertTrue(result)
                with self.assertRaises(ValueError):mod.submit_lane(pool,lambda *a:None,'999',(),self.bound['request_id'],manifest.digest)
        finally:APPROVED_RESUME.reset(marker)
    def test_resolve_bundle_durable_receipt_before_effective_payload(self):
        from types import SimpleNamespace
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.planning import Planner
        from ares_campaign_v3.progress import CURRENT
        m=Manifest.from_dict(self.state['manifest']);bundle=Planner().build(m).lanes[self.bound['account_id']][0]
        record=copy.deepcopy(self.checkpoint['bundles'][0]);events=[]
        cid=record['campaign_ids'][0];sid=record['adset_ids'][0]
        rows=[SimpleNamespace(name='feature_campaign',code=200,body={'id':cid,'account_id':bundle.account_id,'status':'PAUSED'}),
              SimpleNamespace(name='feature_adset',code=200,body={'id':sid,'account_id':bundle.account_id,'campaign_id':cid,'status':'PAUSED'}),
              SimpleNamespace(name='feature_ads',code=200,body={'data':[]})]
        engine=SimpleNamespace(_batch=lambda *args:rows)
        marker=APPROVED_RESUME.set(self.context());journal=CURRENT.set((record,lambda:events.append(copy.deepcopy(record))))
        try:
            out=mod.resolve_bundle(engine,bundle,None,record)
            self.assertEqual(len(events),1);self.assertIn('reviewed_creative_feature_resolution',events[0])
            self.assertEqual(out.campaigns[0].ads[0].creative_payload,mod.effective(bundle.campaigns[0].ads[0].creative_payload))
            self.assertEqual(bundle.campaigns[0].ads[0].creative_payload,self.state['manifest']['campaigns'][0]['ads'][0]['creative_payload'])
            # Reusing the same receipt is safe; no reseal or second pre-read.
            self.assertEqual(mod.resolve_bundle(engine,bundle,None,record),out)
        finally:CURRENT.reset(journal);APPROVED_RESUME.reset(marker)
    def test_nonzero_ads_blocks_first_resolution(self):
        from types import SimpleNamespace
        from ares_campaign_v3.schema import Manifest
        from ares_campaign_v3.planning import Planner
        from ares_campaign_v3.progress import CURRENT
        m=Manifest.from_dict(self.state['manifest']);bundle=Planner().build(m).lanes[self.bound['account_id']][0]
        record=copy.deepcopy(self.checkpoint['bundles'][0]);cid=record['campaign_ids'][0];sid=record['adset_ids'][0]
        rows=[SimpleNamespace(name='feature_campaign',code=200,body={'id':cid,'account_id':bundle.account_id,'status':'PAUSED'}),
              SimpleNamespace(name='feature_adset',code=200,body={'id':sid,'account_id':bundle.account_id,'campaign_id':cid,'status':'PAUSED'}),
              SimpleNamespace(name='feature_ads',code=200,body={'data':[{'id':'999'}]})]
        marker=APPROVED_RESUME.set(self.context());journal=CURRENT.set((record,lambda:self.fail('must not persist resolution')))
        try:
            with self.assertRaises(ValueError):mod.resolve_bundle(SimpleNamespace(_batch=lambda *args:rows),bundle,None,record)
            self.assertNotIn('reviewed_creative_feature_resolution',record)
        finally:CURRENT.reset(journal);APPROVED_RESUME.reset(marker)
    def test_unknown_kind_fails(self):
        changed=copy.deepcopy(self.desc);changed['reviewed_creative_features_kind']='arbitrary'
        with self.assertRaises(ValueError):mod.validate_review(changed,self.state,self.checkpoint,get_message=self.get_message)

if __name__=='__main__':unittest.main()
