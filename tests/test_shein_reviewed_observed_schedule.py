"""Exact human-reviewed native copy time; offline only, no writes."""
import copy
import unittest
from ares_campaign_v3 import shein_continuation as m

class ReviewedScheduleTests(unittest.TestCase):
    def fixture(self):
        expected='2026-10-23T16:30:00-04:00'; observed='2026-10-23T16:30:05-04:00'
        spec={'name':'277 - sample','account_id':'123','start_time':expected,'idempotency_key':'slot1'}
        state={'account':{'id':'act_123','timezone_name':'America/New_York'},'request':{'start_time':expected},'manifest':{'campaigns':[spec]},'target_manifest':{'campaigns':[copy.deepcopy(spec)]}}
        checkpoint={'account_id':'123','status':'COMPLETE','bundles':[{'status':'COMPLETE','campaign_ids':['456'],'adset_ids':['789'],'idempotency_keys':['slot1'],'timings':{'adset_copy':{'started_at':'2026-10-23T20:30:04+00:00','finished_at':'2026-10-23T20:30:08+00:00'}},'readback_results':[{'name':'readback_campaign_1','code':200,'body':{'id':'456','account_id':'123','start_time':observed}},{'name':'readback_adsets_1','code':200,'body':{'data':[{'id':'789','start_time':observed}]}}]}]}
        descriptor={'account_id':'123','source_thread_id':'1558134300325716050','preserved_start_time':observed,'schedule_review_prompt_message_id':'1563289172540792914','recovery_review_message_id':'1563289492574445629','recovery_review_content':'sim','late_activation_authorized':True,'reviewed_observed_copy_time':True}
        prompt={'id':descriptor['schedule_review_prompt_message_id'],'channel_id':descriptor['source_thread_id'],'author':{'id':'1508864261504630925','bot':True},'content':'Você autoriza manter **16h30min05s** nas 277 e concluir a ativação agora, sem recriá-las?'}
        def get(path):
            if '?before=' in path:return [prompt]
            return prompt
        return descriptor,state,checkpoint,get
    def test_exact_review_proof_without_mutation(self):
        d,s,c,g=self.fixture();before=copy.deepcopy((d,s,c));p=m.reviewed_schedule_proof(d,s,c,get_message=g)
        self.assertEqual(p['observed'],d['preserved_start_time']);self.assertEqual((d,s,c),before)
    def test_fails_closed(self):
        for mutation in ['no_review','wrong_time','wrong_account','outside_window','wrong_campaign','wrong_adset','manifest_drift','no_copy','wrong_prompt']:
            d,s,c,g=self.fixture()
            if mutation=='no_review':d['late_activation_authorized']=False
            elif mutation=='wrong_time':d['preserved_start_time']='2026-10-23T16:30:06-04:00'
            elif mutation=='wrong_account':s['account']['id']='act_999'
            elif mutation=='outside_window':c['bundles'][0]['timings']['adset_copy']['finished_at']='2026-10-23T20:30:04+00:00'
            elif mutation=='wrong_campaign':c['bundles'][0]['readback_results'][0]['body']['id']='999'
            elif mutation=='wrong_adset':c['bundles'][0]['readback_results'][1]['body']['data'][0]['id']='999'
            elif mutation=='manifest_drift':s['target_manifest']['campaigns'][0]['start_time']='2026-10-23T16:30:01-04:00'
            elif mutation=='no_copy':c['bundles'][0]['status']='IN_PROGRESS'
            elif mutation=='wrong_prompt':g=lambda path:[]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):m.reviewed_schedule_proof(d,s,c,get_message=g)
    def test_only_informational_ares_notice_can_intervene(self):
        for human in [False,True]:
            d,s,c,g=self.fixture();prompt=g('prompt')
            notice={'id':'1563289423876067421','author':{'id':'1055570806945620030' if human else '1508864261504630925','bot':not human},'content':'💾 Self-improvement review: saved'}
            def get(path):return [notice,prompt] if '?before=' in path else prompt
            if human:
                with self.assertRaises(ValueError):m.reviewed_schedule_proof(d,s,c,get_message=get)
            else:self.assertTrue(m.reviewed_schedule_proof(d,s,c,get_message=get))
    def test_exact_pair_only_and_context_required(self):
        d,s,c,g=self.fixture();p=m.reviewed_schedule_proof(d,s,c,get_message=g)
        self.assertFalse(m.schedule_matches(p['expected'],p['observed']))
        marker=m.APPROVED_RESUME.set({'descriptor':d,'state':s,'verified':{'verified':True,'accepted_schedule':p}})
        try:
            self.assertTrue(m.schedule_matches(p['expected'],p['observed']))
            self.assertFalse(m.schedule_matches(p['expected'],'2026-10-23T16:30:06-04:00'))
        finally:m.APPROVED_RESUME.reset(marker)

if __name__=='__main__':unittest.main()
