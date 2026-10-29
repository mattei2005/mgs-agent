"""Synthetic offline tests. Patching the maintenance seal is TEST ONLY.

The real frozen descriptor is exercised separately by validate_readonly.py.
No network, credentials, production fixture reads or Meta writes here.
"""
import copy
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from ares_campaign_v3 import shein_continuation as continuation
from ares_campaign_v3 import shein_reviewed_targeting as reviewed
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3 import prevalidation
from ares_campaign_v3.activation import validate_live
from ares_campaign_v3.schema import Manifest
from test_shein_single_clone_route import fixture, live_fixture


class ReviewedTargetingTests(unittest.TestCase):
    def setUp(self):
        req, source, cfg = fixture()
        source['adset']['targeting']['targeting_automation']['individual_setting']['device'] = 1
        creation = route.build_manifest(req, source, 114, cfg)
        creation['campaigns'].append(copy.deepcopy(creation['campaigns'][0]))
        creation['campaigns'][1]['idempotency_key'] += '-two'
        self.trees = []
        for i, spec in enumerate(creation['campaigns']):
            tree = live_fixture({**creation, 'campaigns':[spec]}, source)
            tree['campaign']['id'] = '111'+str(i)
            tree['adsets']['data'][0]['id'] = '222'+str(i)
            tree['ads']['data'][0].update(id='333'+str(i), adset_id='222'+str(i))
            tree['adsets']['data'][0]['targeting']['targeting_automation'].pop('individual_setting')
            self.trees.append(tree)
        target = copy.deepcopy(creation)
        for spec in target['campaigns']: spec['status'] = 'ACTIVE'
        for m in [creation, target]: self.seal(m)
        req.update(status='ACTIVE', quantity=2, authorized_by=reviewed.HUMAN,
                   source_thread_id=reviewed.ORIGIN, source_channel_id='1548150155184701440')
        self.state = {'request':req, 'source':source, 'manifest':creation, 'target_manifest':target,
                      'execution_started_at':'2026-10-29T07:12:14.156000+00:00', 'phase':'POSTPROCESS_PENDING',
                      'account':{'id':'act_'+route.ACCOUNT_ID,'currency':'USD','timezone_name':'America/New_York'}}
        bundle = {'status':'COMPLETE','idempotency_keys':[s['idempotency_key'] for s in creation['campaigns']],
                  'campaign_ids':[t['campaign']['id'] for t in self.trees],
                  'adset_ids':[t['adsets']['data'][0]['id'] for t in self.trees],
                  'ad_ids':[t['ads']['data'][0]['id'] for t in self.trees], 'readback_results':[]}
        for i,t in enumerate(self.trees,1):
            bundle['readback_results'].append({'name':'readback_ads_'+str(i),'code':200,'body':t['ads']})
        self.cp = {'account_id':route.ACCOUNT_ID,'status':'COMPLETE','bundles':[bundle]}
        self.d = {'continuation_of':req['request_id'], 'account':req['account'],'account_id':route.ACCOUNT_ID,
                  'authorized_by':req['authorized_by'],'source_channel_id':req['source_channel_id'],
                  'source_thread_id':req['source_thread_id'],'source_campaign_number':req['source_number'],
                  'budget_usd':req['budget_usd'],'quantity':2,'status':'ACTIVE','start_now':True,
                  'source_message_id':reviewed.NOW_ID,'source_message_content':reviewed.NOW,
                  'existing_campaign_ids':bundle['campaign_ids'][:], 'existing_adset_ids':bundle['adset_ids'][:],
                  'reviewed_targeting':reviewed.binding(self.state,self.cp)}
        self.messages = {}
        for mid,text,actor,bot in [(reviewed.ORIGINAL_ID,reviewed.ORIGINAL,reviewed.HUMAN,False),
                                   (reviewed.NOW_ID,reviewed.NOW,reviewed.HUMAN,False),
                                   (reviewed.PROMPT_ID,reviewed.PROMPT,reviewed.ARES,True),
                                   (reviewed.REVIEW_ID,reviewed.REVIEW,reviewed.HUMAN,False)]:
            self.messages[mid] = {'id':mid,'content':text,'channel_id':reviewed.ORIGIN,'author':{'id':actor,'bot':bot}}
        self.history = [self.messages[reviewed.PROMPT_ID]]
        self.addCleanup(patch.stopall)
        patch.object(reviewed,'BINDING_DIGEST',continuation.content_digest(self.d['reviewed_targeting'])).start()
        op = {'operation_id':'SHEIN-US-DIRECT','channel_authorization_policy':{
            'enabled':True,'approved_by':route.RODOLFO_ID,'channel_ids':[req['source_channel_id']],
            'late_recovery_review':{'enabled':True,'approved_by':route.RODOLFO_ID}}}
        profile = {'account_id':route.ACCOUNT_ID,'channel_id':req['source_channel_id']}
        patch.object(continuation,'_late_review_context',return_value=(op,profile)).start()
        self.auth = patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':True}).start()

    def seal(self,m):
        m['prevalidated']=True
        m['prevalidation']={'content_digest':prevalidation.content_digest(m)}

    def get(self,path):
        return copy.deepcopy(self.history if '?before=' in path else self.messages[path.rsplit('/',1)[1]])

    def proof(self):
        return continuation.validate_descriptor(self.d,self.state,self.cp,get_message=self.get)

    @contextmanager
    def context(self):
        proof=self.proof()
        marker=continuation.APPROVED_RESUME.set({'descriptor':self.d,'state':self.state,'checkpoint':self.cp,'verified':proof})
        try: yield proof
        finally: continuation.APPROVED_RESUME.reset(marker)

    def payload(self,i):
        return {**self.state['manifest'],'campaigns':[self.state['manifest']['campaigns'][i]]}

    def test_exact_review_two_ids_and_live_force_permission_no_mutation(self):
        before=copy.deepcopy((self.d,self.state,self.cp,self.trees))
        with self.context() as proof:
            self.assertEqual(proof['accepted_targeting']['review_message_id'],reviewed.REVIEW_ID)
            for i,tree in enumerate(self.trees):
                self.assertIn('Human review',route.verify_readback(self.payload(i),self.state['source'],tree)[0])
        self.assertEqual(before,(self.d,self.state,self.cp,self.trees))
        self.assertIs(self.auth.call_args.kwargs['force'],True)

    def test_no_context_remains_fail_closed(self):
        with self.assertRaises(ValueError):route.verify_readback(self.payload(0),self.state['source'],self.trees[0])

    def test_wrong_or_edited_question_answer_or_immediate_approval(self):
        for mid in [reviewed.PROMPT_ID,reviewed.REVIEW_ID,reviewed.NOW_ID,reviewed.ORIGINAL_ID]:
            for field in ['content','id','channel_id','actor','bot','edited_timestamp']:
                with self.subTest(mid=mid,field=field):
                    original=copy.deepcopy(self.messages[mid]);m=self.messages[mid]
                    if field=='actor':m['author']['id']='other'
                    elif field=='bot':m['author']['bot']=not m['author']['bot']
                    else:m[field]='different'
                    with self.assertRaises(ValueError):self.proof()
                    self.messages[mid]=original

    def test_unlinked_yes_and_substantive_intervention_denied(self):
        for history in [[],[{'id':str(int(reviewed.PROMPT_ID)+1),'author':{'id':reviewed.HUMAN},'content':'different'},self.messages[reviewed.PROMPT_ID]]]:
            self.history=history
            with self.assertRaises(ValueError):self.proof()

    def test_permission_revocation_denied(self):
        self.auth.side_effect=ValueError('revoked')
        with self.assertRaises(ValueError):self.proof()

    def test_changed_sealed_manifests_source_clock_request_and_receipts_denied(self):
        for change in ['clock','request','source_id','source_targeting','account','campaign_id','adset_id','ad_id','lineage','creation','target','seal','cp_status','binding']:
            with self.subTest(change=change):
                saved=copy.deepcopy((self.state,self.cp,self.d))
                if change=='clock':self.state['execution_started_at']='2030-01-01T00:00:00+00:00'
                elif change=='request':self.state['request']['budget_usd']='31'
                elif change=='source_id':self.state['source']['adset']['id']='other'
                elif change=='source_targeting':self.state['source']['adset']['targeting']['age_min']=25
                elif change=='account':self.cp['account_id']='other'
                elif change in ['campaign_id','adset_id','ad_id']:
                    self.cp['bundles'][0][{'campaign_id':'campaign_ids','adset_id':'adset_ids','ad_id':'ad_ids'}[change]][0]='other'
                elif change=='lineage':self.cp['bundles'][0]['readback_results'][0]['body']['data'][0]['source_ad_id']='other'
                elif change in ['creation','target']:
                    m=self.state['manifest' if change=='creation' else 'target_manifest'];m['campaigns'][0]['campaign_updates']['daily_budget']='3100';self.seal(m)
                elif change=='seal':self.state['manifest']['prevalidation']['content_digest']='other'
                elif change=='cp_status':self.cp['status']='IN_PROGRESS'
                elif change=='binding':self.d['reviewed_targeting']['account_id']='other'
                with self.assertRaises(ValueError):self.proof()
                self.state,self.cp,self.d=saved

    def test_only_exact_device_omission_and_exact_objects(self):
        with self.context():
            for change in ['device0','device1','other_flag','age_min','geo','unknown_age','campaign','adset','ad','lineage','parent','account','budget','bid','schedule','status']:
                with self.subTest(change=change):
                    t=copy.deepcopy(self.trees[0]);s=t['adsets']['data'][0];a=t['ads']['data'][0]
                    if change.startswith('device'):s['targeting']['targeting_automation']['individual_setting']={'device':int(change[-1])}
                    elif change=='other_flag':s['targeting']['targeting_automation']['individual_setting']={'other':1}
                    elif change=='age_min':s['targeting']['age_min']=25
                    elif change=='geo':s['targeting']['geo_locations']={'countries':['CA']}
                    elif change=='unknown_age':s['targeting']['user_age_unknown']=not s['targeting']['user_age_unknown']
                    elif change=='campaign':t['campaign']['id']='other'
                    elif change=='adset':s['id']='other'
                    elif change=='ad':a['id']='other'
                    elif change=='lineage':a['source_ad_id']='other'
                    elif change=='parent':a['campaign_id']='other'
                    elif change=='account':t['campaign']['account_id']='other'
                    elif change=='budget':t['campaign']['daily_budget']='1'
                    elif change=='bid':s['bid_amount']=75
                    elif change=='schedule':s['start_time']='2030-10-08T00:10:00-04:00'
                    elif change=='status':s['status']='ACTIVE'
                    with self.assertRaises(ValueError):route.verify_readback(self.payload(0),self.state['source'],t)

    def test_context_tampering_denied_after_validation(self):
        with self.context():
            self.d['source_message_content']='other'
            with self.assertRaises(ValueError):reviewed.active_context()

    def test_activation_authorization_exact_ads_and_pre_read_targeting(self):
        with self.context():
            creation=Manifest.from_dict(self.state['manifest']);target=Manifest.from_dict(self.state['target_manifest'])
            with patch('ares_campaign_v3.shein_channel_authority._get',side_effect=self.get):
                self.assertTrue(continuation.activation_authorization(target,creation,{'trees':self.trees}))
                bad=copy.deepcopy(self.trees);bad[0]['ads']['data'][0]['id']='other'
                with self.assertRaises(ValueError):continuation.activation_authorization(target,creation,{'trees':bad})
            tree=copy.deepcopy(self.trees[0])
            validate_live(tree,tree,target.campaigns[0],self.d['continuation_of'])
            tree['adsets']['data'][0]['targeting']['user_age_unknown']=False
            # Even a poisoned cached QA tree cannot hide a fresh targeting drift.
            with self.assertRaises(ValueError):validate_live(tree,tree,target.campaigns[0],self.d['continuation_of'])


if __name__=='__main__':unittest.main()
