"""Exact reviewed readback omissions; zero network/writes in tests."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from ares_campaign_v3 import shein_reviewed_feature_omissions as mod
from ares_campaign_v3 import shein_reviewed_background_batch as batch
from ares_campaign_v3.shein_continuation import APPROVED_RESUME,content_digest,validate_descriptor

ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1567026734212190352')
OLD=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/feature-review-1567010220134105191')
class ReviewedOmissionTests(unittest.TestCase):
    def setUp(self):
        self.state=json.loads((ROOT/'state.before.json').read_text());self.cp=json.loads((ROOT/'checkpoint.before.json').read_text())
        self.bound=json.loads((ROOT/'binding.json').read_text());self.initial=json.loads((OLD/'binding.json').read_text())
        self.messages={m['id']:m for m in json.loads((ROOT/'review-context.json').read_text())}
        self.messages.update(json.loads((OLD/'messages.json').read_text()))
        self.desc=batch.make_descriptor(self.state,self.initial,reviewed_omissions=self.bound)
        self.trees=json.loads((ROOT/'trees.before.json').read_text())
    def get(self,path):
        if '/messages?' in path:
            if 'before='+batch.REVIEW_ID in path:return [self.messages[batch.PROMPT_ID]]
            return [m for m in self.messages.values() if int(mod.PROMPT_ID)<=int(m['id'])<int(mod.REVIEW_ID)]
        return self.messages[path.rsplit('/',1)[-1]]
    def context(self):
        return {'descriptor':self.desc,'state':self.state,'checkpoint':self.cp,'verified':{
            'verified':True,'descriptor_digest':content_digest(self.desc),
            'accepted_creative_features':{'binding_digest':batch.BINDING_DIGEST},
            'accepted_feature_omissions':{'binding_digest':mod.BINDING_DIGEST,'review_message_id':mod.REVIEW_ID}}}
    def test_real_review_descriptor_validates_without_clock_or_scope_change(self):
        with patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'live':True}):
            v=validate_descriptor(self.desc,self.state,self.cp,get_message=self.get)
        self.assertTrue(v['verified']);self.assertEqual(v['accepted_feature_omissions']['review_message_id'],mod.REVIEW_ID)
        self.assertFalse(v['start_now']);self.assertEqual(v['original_execution_started_at'],self.state['execution_started_at'])
    def test_reject_changed_review_identity_or_text(self):
        for key,value in [('content','não'),('edited_timestamp','later'),('channel_id','9')]:
            saved=copy.deepcopy(self.messages[mod.REVIEW_ID]);self.messages[mod.REVIEW_ID][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):mod.validate(self.bound,self.state,self.cp,get_message=self.get)
            self.messages[mod.REVIEW_ID]=saved
    def test_bindings_reject_other_ids_source_manifest_and_schedule(self):
        for key in ['request_id','account_id','execution_started_at','source_digest']:
            b=copy.deepcopy(self.bound);b[key]='other'
            with self.subTest(key=key),self.assertRaises(ValueError):mod.require_binding(self.state,self.cp,b)
        c=copy.deepcopy(self.cp);c['bundles'][0]['ad_ids'][0]='9'
        with self.assertRaises(ValueError):mod.require_binding(self.state,c,self.bound)
        s=copy.deepcopy(self.state);s['target_manifest']['campaigns'][0]['start_time']='2026-11-04T00:00:00-05:00'
        with self.assertRaises(ValueError):mod.require_binding(s,self.cp,self.bound)
    def test_without_extra_review_original_gate_is_preserved(self):
        old=batch.make_descriptor(self.state,self.initial);context=self.context();context['descriptor']=old
        context['verified']['descriptor_digest']=content_digest(old);context['verified'].pop('accepted_feature_omissions')
        marker=APPROVED_RESUME.set(context)
        try:
            with self.assertRaises(ValueError):self.check_all()
        finally:APPROVED_RESUME.reset(marker)
    def check_all(self):
        from ares_campaign_v3.shein_single_clone import verify_readback
        for tree in self.trees:
            desired=next(c for c in self.state['manifest']['campaigns'] if c['name']==tree['campaign']['name'])
            verify_readback({**self.state['manifest'],'campaigns':[desired]},self.state['source'],tree)
    def test_all_six_live_definitions_pass_with_exact_review_without_mutating_payloads(self):
        before=copy.deepcopy(self.state);marker=APPROVED_RESUME.set(self.context())
        try:self.check_all()
        finally:APPROVED_RESUME.reset(marker)
        self.assertEqual(self.state,before)
    def test_additional_feature_or_explicit_toggle_or_background_opt_in_is_rejected(self):
        tree=self.trees[0];ad=tree['ads']['data'][0];desired=self.state['manifest']['campaigns'][0]
        cp=next(a['creative_payload'] for a in desired['ads'] if a['source_ad_id']==ad['source_ad_id'])
        marker=APPROVED_RESUME.set(self.context())
        try:
            for variant in ['extra_missing','explicit_value','background','other_opt_in','creative_id','media_payload']:
                actual=copy.deepcopy(ad['creative']);expected=copy.deepcopy(cp);f=actual['degrees_of_freedom_spec']['creative_features_spec']
                if variant=='extra_missing':f.pop(next(k for k in cp['degrees_of_freedom_spec']['creative_features_spec'] if k not in mod.OMISSIONS and k!='image_background_gen'))
                if variant=='explicit_value':f['product_browsing']={'enroll_status':'OPT_OUT'}
                if variant=='background':f['image_background_gen']={'enroll_status':'OPT_IN'}
                if variant=='other_opt_in':f['unapproved_feature']={'enroll_status':'OPT_IN'}
                if variant=='creative_id':actual['id']='9'
                if variant=='media_payload':expected['object_story_spec']['link_data']['message']='different'
                with self.subTest(variant=variant),self.assertRaises(ValueError):batch.verify_creative(actual,expected)
        finally:APPROVED_RESUME.reset(marker)
    def test_dialogue_uses_two_gets_not_one_request_per_message(self):
        calls=[]
        def get(path):calls.append(path);return self.get(path)
        with patch('ares_campaign_v3.shein_continuation._authorize_late_reviewer',return_value={'live':True}):
            result=mod.validate(self.bound,self.state,self.cp,get_message=get)
        self.assertEqual(result['review_message_id'],mod.REVIEW_ID)
        self.assertEqual(len(calls),2)
        self.assertTrue(any('/messages?before=' in p for p in calls))

    def test_unexpected_intervening_human_message_blocks(self):
        original=self.get
        def get(path):
            result=original(path)
            if '/messages?before='+mod.REVIEW_ID in path:return result+[{'id':str(int(mod.REVIEW_ID)-1),'author':{'id':mod.HUMAN,'bot':False},'content':'other decision'}]
            return result
        with self.assertRaises(ValueError):mod.validate(self.bound,self.state,self.cp,get_message=get)
    def test_missing_or_forged_verified_review_is_rejected(self):
        for mutation in ['missing','binding','descriptor']:
            context=self.context()
            if mutation=='missing':context['verified'].pop('accepted_feature_omissions')
            if mutation=='binding':context['verified']['accepted_feature_omissions']['binding_digest']='9'
            if mutation=='descriptor':context['descriptor']['reviewed_feature_omissions']['slots'][0]['creative_id']='9'
            marker=APPROVED_RESUME.set(context)
            try:
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.check_all()
            finally:APPROVED_RESUME.reset(marker)
if __name__=='__main__':unittest.main()
