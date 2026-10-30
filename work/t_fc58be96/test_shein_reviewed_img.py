"""Offline synthetic regression; real exact 8/8/16 is tested read-only separately."""
import copy
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from ares_campaign_v3 import shein_continuation as continuation
from ares_campaign_v3 import shein_reviewed_targeting as reviewed
from ares_campaign_v3 import shein_reviewed_img as img
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3 import prevalidation
from ares_campaign_v3.activation import validate_live
from ares_campaign_v3.schema import Manifest
from test_shein_single_clone_route import fixture, live_fixture


class ReviewedIMGTests(unittest.TestCase):
    def setUp(self):
        req, source, cfg = fixture()
        source['adset']['targeting']['targeting_automation']['individual_setting'] = {'device':1}
        source['adset']['targeting']['user_age_unknown'] = False
        creation = route.build_manifest(req, source, 114, cfg)
        first = copy.deepcopy(creation['campaigns'][0])
        creation['campaigns'] = []
        self.trees = []
        for i in range(8):
            spec = copy.deepcopy(first)
            spec['idempotency_key'] += '-'+str(i)
            spec['bid_override'] = True
            spec['adset_updates'] = {'bid_amount':'95','bid_constraints':{}}
            spec['campaign_updates']['bid_strategy'] = 'COST_CAP'
            creation['campaigns'].append(spec)
            tree = live_fixture({**creation,'campaigns':[spec]}, source)
            tree['campaign']['id'] = '111'+str(i)
            aset = tree['adsets']['data'][0]
            aset.update(id='222'+str(i), bid_amount=95)
            aset['targeting']['targeting_automation'].pop('individual_setting')
            aset['targeting']['user_age_unknown'] = True
            tree['ads']['data'][0].update(id='333'+str(i),adset_id=aset['id'])
            self.trees.append(tree)
        target = copy.deepcopy(creation)
        for spec in target['campaigns']: spec['status'] = 'ACTIVE'
        for m in [creation,target]:
            m['prevalidated'] = True
            m['prevalidation'] = {'content_digest':prevalidation.content_digest(m)}
        req.update(status='ACTIVE',quantity=8,authorized_by=img.HUMAN,source_message_id=img.ORIGINAL_ID,
                   source_thread_id=img.ORIGIN,source_channel_id='1548150155184701440')
        self.state = {'request':req,'resolved_request':{**req,'start_now':True},'source':source,
                      'manifest':creation,'target_manifest':target,'execution_started_at':'2026-10-30T15:20:58+00:00',
                      'phase':'POSTPROCESS_PENDING','account':{'id':'act_'+route.ACCOUNT_ID,'currency':'USD','timezone_name':'America/New_York'}}
        bundle = {'status':'COMPLETE','idempotency_keys':[s['idempotency_key'] for s in creation['campaigns']],
                  'campaign_ids':[t['campaign']['id'] for t in self.trees],
                  'adset_ids':[t['adsets']['data'][0]['id'] for t in self.trees],
                  'ad_ids':[t['ads']['data'][0]['id'] for t in self.trees], 'readback_results':[],
                  'timings':{'adset_copy':{'started_at':'2026-10-30T16:28:00+00:00','finished_at':'2026-10-30T16:29:00+00:00'}}}
        for i,t in enumerate(self.trees,1):
            for k in ['campaign','adsets','ads']:
                bundle['readback_results'].append({'name':'readback_'+k+'_'+str(i),'code':200,'body':copy.deepcopy(t[k])})
        self.cp = {'account_id':route.ACCOUNT_ID,'status':'COMPLETE','bundles':[bundle]}
        self.d = {k:req[k] for k in ['account','authorized_by','source_thread_id','source_channel_id','budget_usd','quantity','status']}
        self.d.update(continuation_of=req['request_id'],account_id=route.ACCOUNT_ID,source_campaign_number=req['source_number'],
                      start_now=True,source_message_id=img.ORIGINAL_ID,source_message_content=img.ORIGINAL_CONTENT,
                      existing_campaign_ids=bundle['campaign_ids'][:],existing_adset_ids=bundle['adset_ids'][:],
                      late_activation_authorized=True,recovery_review_message_id=img.REVIEW_ID,
                      recovery_review_thread_id=img.ORIGIN,recovery_review_content=img.REVIEW_CONTENT,
                      reviewed_targeting_kind=img.KIND,reviewed_targeting=img.binding(self.state,self.cp))
        self.messages = []
        for i,mid in enumerate(img.MESSAGE_IDS):
            self.messages.append({'id':mid,'channel_id':img.ORIGIN,'content':['original','question','context',img.REVIEW_CONTENT][i],
                                  'timestamp':'2026-10-30T17:29:38+00:00','edited_timestamp':None,
                                  'author':{'id':img.RODOLFO if i==3 else img.HUMAN if i==0 else reviewed.ARES,'bot':True if i in [1,2] else None},
                                  'message_reference':{'message_id':img.MESSAGE_IDS[2]} if i==3 else None})
        self.messages[0]['content'] = img.ORIGINAL_CONTENT
        self.addCleanup(patch.stopall)
        patch.object(img,'BINDING_DIGEST',continuation.content_digest(self.d['reviewed_targeting'])).start()
        patch.object(img,'MESSAGES_DIGEST',continuation.content_digest(self.messages)).start()

    def get(self,path):
        return copy.deepcopy(next(m for m in self.messages if m['id']==path.rsplit('/',1)[1]))

    def proof(self):
        return continuation.validate_descriptor(self.d,self.state,self.cp,get_message=self.get)

    @contextmanager
    def context(self):
        proof = self.proof()
        token = continuation.APPROVED_RESUME.set({'descriptor':self.d,'state':self.state,'checkpoint':self.cp,'verified':proof})
        try: yield proof
        finally: continuation.APPROVED_RESUME.reset(token)

    def payload(self,i):
        return {**self.state['manifest'],'campaigns':[self.state['manifest']['campaigns'][i]]}

    def test_exact_eight_slots_and_manifest_bid_not_source_bid(self):
        before=copy.deepcopy((self.state,self.cp,self.d,self.trees))
        with self.context() as proof:
            self.assertEqual(proof['accepted_targeting']['review_message_id'],img.REVIEW_ID)
            for i,tree in enumerate(self.trees):
                self.assertIn('Human review',route.verify_readback(self.payload(i),self.state['source'],tree)[0])
        self.assertEqual(before,(self.state,self.cp,self.d,self.trees))

    def test_binding_negative_matrix(self):
        for field in ['request','source','account','campaign','adset','ads','lineage','manifest','target','clock','resolved','native','budget','bid','review_kind','descriptor_account','cp_status']:
            with self.subTest(field=field):
                saved=copy.deepcopy((self.state,self.cp,self.d))
                if field=='request': self.state['request']['request_id']='another'
                elif field=='source': self.state['source']['campaign']['id']='another'
                elif field=='account': self.cp['account_id']='999'
                elif field in ['campaign','adset','ads']: self.cp['bundles'][0][{'campaign':'campaign_ids','adset':'adset_ids','ads':'ad_ids'}[field]][0]='999'
                elif field=='lineage': self.cp['bundles'][0]['readback_results'][2]['body']['data'][0]['source_ad_id']='999'
                elif field in ['manifest','target']: self.state['manifest' if field=='manifest' else 'target_manifest']['campaigns'][0]['name']='another'
                elif field=='clock': self.state['execution_started_at']='2030-01-01T00:00:00+00:00'
                elif field=='resolved': self.state['resolved_request']['start_now']=False
                elif field=='native': self.cp['bundles'][0]['timings']['adset_copy']['finished_at']='2030-01-01T00:00:00+00:00'
                elif field in ['budget','bid']: self.d['budget_usd' if field=='budget' else 'bid_usd']='1'
                elif field=='review_kind': self.d['reviewed_targeting_kind']='unknown'
                elif field=='descriptor_account': self.d['account_id']='999'
                elif field=='cp_status': self.cp['status']='PENDING'
                with self.assertRaises((ValueError,KeyError)): self.proof()
                self.state,self.cp,self.d=saved

    def test_discord_authority_content_and_reply_negative_matrix(self):
        for index in range(4):
            for field in ['id','channel_id','content','timestamp','edited_timestamp','author','message_reference']:
                with self.subTest(index=index,field=field):
                    old=copy.deepcopy(self.messages[index])
                    if field=='author': self.messages[index][field]={'id':'999','bot':False}
                    elif field=='message_reference': self.messages[index][field]={'message_id':'999'}
                    else: self.messages[index][field]='changed'
                    with self.assertRaises((ValueError,StopIteration)): self.proof()
                    self.messages[index]=old

    def test_exact_two_deltas_only_and_live_identity_budget_bid_clock(self):
        with self.context():
            for field in ['age','unknown','device','extra_device','geo','advantage','campaign','account','adset','ad','lineage','budget','bid','constraints','clock','attribution','paging']:
                with self.subTest(field=field):
                    tree=copy.deepcopy(self.trees[0]);s=tree['adsets']['data'][0];a=tree['ads']['data'][0]
                    if field=='age': s['targeting']['age_min']=25
                    elif field=='unknown': s['targeting']['user_age_unknown']=False
                    elif field=='device': s['targeting']['targeting_automation']['individual_setting']={'device':1}
                    elif field=='extra_device': s['targeting']['targeting_automation']['individual_setting']={'device':0,'age':1}
                    elif field=='geo': s['targeting']['geo_locations']={'countries':['CA']}
                    elif field=='advantage': s['targeting']['targeting_automation']['advantage_audience']=0
                    elif field=='campaign': tree['campaign']['id']='999'
                    elif field=='account': tree['campaign']['account_id']='999'
                    elif field=='adset': s['id']='999'
                    elif field=='ad': a['id']='999'
                    elif field=='lineage': a['source_ad_id']='999'
                    elif field=='budget': tree['campaign']['daily_budget']='1'
                    elif field=='bid': s['bid_amount']=90
                    elif field=='constraints': s['bid_constraints']={'x':1}
                    elif field=='clock': s['start_time']='2030-01-01T00:00:00+00:00'
                    elif field=='attribution': s['attribution_spec']=[]
                    elif field=='paging': tree['ads']['paging']={'next':'more'}
                    with self.assertRaises(ValueError): reviewed.validate_tree(reviewed.active_context(),tree)

    def test_no_context_and_legacy_kind_cannot_accept_new_diff(self):
        with self.assertRaises(ValueError):route.verify_readback(self.payload(0),self.state['source'],self.trees[0])
        self.d.pop('reviewed_targeting_kind')
        with self.assertRaises(ValueError):self.proof()

    def test_activation_pre_read_and_poisoned_cached_proof(self):
        with self.context():
            creation=Manifest.from_dict(self.state['manifest']);target=Manifest.from_dict(self.state['target_manifest'])
            with patch('ares_campaign_v3.shein_channel_authority._get',side_effect=self.get):
                self.assertTrue(continuation.activation_authorization(target,creation,{'trees':self.trees}))
            tree=copy.deepcopy(self.trees[0])
            validate_live(tree,tree,target.campaigns[0],self.d['continuation_of'])
            tree['adsets']['data'][0]['targeting']['age_min']=25
            with self.assertRaises(ValueError):validate_live(tree,tree,target.campaigns[0],self.d['continuation_of'])
            self.d['source_message_content']='tampered'
            with self.assertRaises(ValueError):reviewed.active_context()

if __name__=='__main__':unittest.main()
