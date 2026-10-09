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
    def test_copy_normalization_is_accepted_only_in_verified_same_id_resume(self):
        m,d,s,c,g=self.fixture()
        self.assertTrue(callable(getattr(m,'schedule_matches',None)), 'scoped normalization comparator is missing')
        expected='2026-10-09T11:30:00-04:00';observed='2026-10-09T11:30:01-0400'
        d['preserved_start_time']=observed;s['manifest']['campaigns']=[{'start_time':expected}]
        self.assertFalse(m.schedule_matches(expected,observed))
        p=m.validate_descriptor(d,s,c,get_message=g)
        marker=m.APPROVED_RESUME.set({'descriptor':d,'state':s,'checkpoint':c,'verified':p})
        try:
            self.assertTrue(m.schedule_matches(expected,observed))
            self.assertFalse(m.schedule_matches(expected,'2026-10-09T11:30:02-04:00'))
        finally:m.APPROVED_RESUME.reset(marker)
    def test_elapsed_active_parse_is_scoped_to_exact_original_target(self):
        m,d,s,c,g=self.fixture()
        self.assertTrue(callable(getattr(m,'allows_elapsed_campaign',None)), 'scoped elapsed target capability is missing')
        target={'idempotency_key':'same','account_id':'999','status':'ACTIVE','start_time':'2026-10-09T11:30:00-04:00'}
        s['target_manifest']['campaigns']=[target]
        self.assertFalse(m.allows_elapsed_campaign(target))
        p=m.validate_descriptor(d,s,c,get_message=g)
        marker=m.APPROVED_RESUME.set({'descriptor':d,'state':s,'checkpoint':c,'verified':p})
        try:
            self.assertTrue(m.allows_elapsed_campaign(target))
            self.assertFalse(m.allows_elapsed_campaign({**target,'account_id':'other'}))
        finally:m.APPROVED_RESUME.reset(marker)
    def test_no_explicit_now_is_blocked(self):
        m,d,s,c,g=self.fixture();d['start_now']=False
        with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)

class DelegatedLateReviewTests(ContinuationTests):
    def delegated_fixture(self, channel='1548150015275438220', parent_origin=False):
        m,d,s,c,g=self.fixture()
        s['request']['source_channel_id']=channel;d['source_channel_id']=channel
        if parent_origin:
            s['request']['source_thread_id']=channel;d['source_thread_id']=channel
        d['recovery_review_thread_id']=d['source_thread_id']
        d['recovery_review_content']='Pode ativar a campanha!'
        def messages(path):
            row=g(path)
            if path.endswith(d['recovery_review_message_id']):
                row['author']['id']=d['authorized_by']
            return row
        policy={'enabled':True,'approved_by':'344196393512075265','channel_ids':[channel],
                'late_recovery_review':{'enabled':True,'approved_by':'344196393512075265'}}
        op={'operation_id':'SHEIN-US-DIRECT','channel_authorization_policy':policy}
        profile={'account_id':'999','channel_id':channel,'manager_discord_id':'1291113428982693940'}
        return m,d,s,c,messages,op,profile

    def test_geizian_late_review_all_six_parents_and_threads(self):
        from unittest.mock import patch
        channels=['1548149087206121613','1548149300826079333','1548149483039236137',
                  '1548149654926135486','1548150015275438220','1548150155184701440']
        for channel in channels:
            for parent_origin in [False,True]:
                with self.subTest(channel=channel,parent_origin=parent_origin):
                    m,d,s,c,g,op,p=self.delegated_fixture(channel,parent_origin)
                    before=copy.deepcopy(s)
                    with patch.object(m,'_late_review_context',return_value=(op,p)), patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':True}) as v:
                        proof=m.validate_descriptor(d,s,c,get_message=g)
                        self.assertTrue(proof['late_activation_authorized'])
                        self.assertEqual(proof['review_authority']['sender_id'],'321263240782807040')
                        self.assertEqual(proof['original_execution_started_at'],s['execution_started_at'])
                        self.assertEqual(s,before)
                        self.assertIs(v.call_args.kwargs['force'],True)

    def test_revoked_permission_denies_late_review(self):
        from unittest.mock import patch
        m,d,s,c,g,op,p=self.delegated_fixture()
        with patch.object(m,'_late_review_context',return_value=(op,p)), patch('ares_campaign_v3.shein_channel_authority.verify',side_effect=ValueError('revoked')):
            with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)

    def test_cross_thread_review_denied_before_permission_lookup(self):
        from unittest.mock import patch
        m,d,s,c,g,op,p=self.delegated_fixture();d['recovery_review_thread_id']='1558141425541980203'
        with patch.object(m,'_late_review_context',return_value=(op,p)), patch('ares_campaign_v3.shein_channel_authority.verify') as v:
            with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
            v.assert_not_called()

    def test_wrong_account_parent_policy_and_operation_denied(self):
        from unittest.mock import patch
        for change in ['parent','account','disabled','unapproved','operation','channel_not_listed','late_disabled','late_unapproved']:
            with self.subTest(change=change):
                m,d,s,c,g,op,p=self.delegated_fixture()
                if change=='parent':p['channel_id']='1548149300826079333';op['channel_authorization_policy']['channel_ids'].append(p['channel_id'])
                elif change=='account':p['account_id']='998'
                elif change=='disabled':op['channel_authorization_policy']['enabled']=False
                elif change=='unapproved':op['channel_authorization_policy']['approved_by']='other'
                elif change=='operation':op['operation_id']='OTHER'
                elif change=='channel_not_listed':op['channel_authorization_policy']['channel_ids']=[]
                elif change=='late_disabled':op['channel_authorization_policy']['late_recovery_review']['enabled']=False
                elif change=='late_unapproved':op['channel_authorization_policy']['late_recovery_review']['approved_by']='other'
                with patch.object(m,'_late_review_context',return_value=(op,p)), patch('ares_campaign_v3.shein_channel_authority.verify') as v:
                    with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=g)
                    v.assert_not_called()

    def test_bot_and_tampered_review_denied(self):
        for change in ['bot','content','id','channel','actor']:
            with self.subTest(change=change):
                m,d,s,c,g,op,p=self.delegated_fixture()
                def bad(path):
                    row=g(path)
                    if path.endswith(d['recovery_review_message_id']):
                        if change=='bot':row['author']['bot']=True
                        elif change=='actor':row['author']['id']='invalid'
                        elif change=='content':row['content']='different'
                        elif change=='id':row['id']='wrong'
                        elif change=='channel':row['channel_id']='wrong'
                    return row
                with self.assertRaises(ValueError):m.validate_descriptor(d,s,c,get_message=bad)

    def test_no_late_authorization_keeps_sla_path(self):
        m,d,s,c,g,op,p=self.delegated_fixture();d['late_activation_authorized']=False
        proof=m.validate_descriptor(d,s,c,get_message=g)
        self.assertFalse(proof['late_activation_authorized']);self.assertIsNone(proof['review_authority'])

if __name__=='__main__':unittest.main()
