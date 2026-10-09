"""Offline authority tests for an explicit same-ID NOW continuation."""
import copy
import importlib
import importlib.util
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class ContinuationTests(unittest.TestCase):
    def fixture(self):
        spec=importlib.util.find_spec('ares_campaign_v3.shein_continuation')
        self.assertIsNotNone(spec,'audited continuation capability is missing')
        module=importlib.import_module('ares_campaign_v3.shein_continuation')
        original={'request_id':'same','account':'Account','authorized_by':'321263240782807040','source_channel_id':'1548150015275438220','source_thread_id':'1558126286826774711','source_number':88,'quantity':1,'budget_usd':'75','bid_strategy':'COCAP','bid_usd':'0.60','status':'ACTIVE'}
        descriptor={'continuation_of':'same','account':'Account','account_id':'999','authorized_by':original['authorized_by'],'source_channel_id':original['source_channel_id'],'source_thread_id':original['source_thread_id'],'source_campaign_number':88,'quantity':1,'budget_usd':'75','bid_strategy':'COCAP','bid_usd':'0.60','status':'ACTIVE','start_now':True,'existing_campaign_id':'111','existing_adset_id':'222','source_message_id':'1558141001216958505','source_message_content':'Iniciar agora; USD75, COCAP0.60','recovery_review_message_id':'1558142033774776411','recovery_review_thread_id':'1558141425541980203','recovery_review_content':'continue o que ele pediu','late_activation_authorized':True}
        state={'request':original,'phase':'RECOVERY_PENDING','manifest':{'request_id':'same'},'target_manifest':{'request_id':'same'},'execution_started_at':'2026-10-09T15:29:46+00:00'}
        checkpoint={'bundles':[{'campaign_ids':['111'],'adset_ids':['222']}]}
        def get(path):
            is_review=path.endswith(descriptor['recovery_review_message_id'])
            return {'id':descriptor['recovery_review_message_id'] if is_review else descriptor['source_message_id'],'channel_id':descriptor['recovery_review_thread_id'] if is_review else descriptor['source_thread_id'],'author':{'id':'344196393512075265' if is_review else descriptor['authorized_by'],'bot':False},'content':descriptor['recovery_review_content'] if is_review else descriptor['source_message_content'],'timestamp':'2026-10-09T15:36:03+00:00'}
        return module,descriptor,state,checkpoint,get
    def test_valid_continuation_preserves_original_request_manifests_and_clock(self):
        m,d,s,c,g=self.fixture();before=copy.deepcopy(s);p=m.validate_descriptor(d,s,c,get_message=g)
        self.assertTrue(p['verified']);self.assertEqual(s,before);self.assertEqual(p['campaign_ids'],['111'])
    def test_changed_budget_is_blocked(self):
        m,d,s,c,g=self.fixture();d['budget_usd']='76'
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
    def test_wrong_existing_id_is_blocked(self):
        m,d,s,c,g=self.fixture();d['existing_adset_id']='333'
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
    def test_unverified_source_message_is_blocked(self):
        m,d,s,c,g=self.fixture()
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=lambda p:{**g(p),'content':'not the approval'})
    def test_wrong_recovery_review_author_is_blocked(self):
        m,d,s,c,g=self.fixture()
        def wrong(p):
            row=g(p)
            if p.endswith(d['recovery_review_message_id']):row['author']['id']='other'
            return row
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=wrong)
    def test_no_explicit_now_is_blocked(self):
        m,d,s,c,g=self.fixture();d['start_now']=False
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)

if __name__=='__main__':unittest.main()
