"""Explicitly offline tests for SHEIN staged creation/global-QA/activation."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_shein_general_runtime import case
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.transport import FakeBatchTransport, BatchResult, BatchTransportError
from ares_campaign_v3.quota import QuotaBlocked
from ares_campaign_v3 import shein_general as compiler


class OfflineActivationTransport:
    def __init__(self, trees):
        self.trees = trees; self.calls=[];self.posts=[];self.last_outer_headers={}
        self.fail_post_number: int | None=None;self.apply_then_fail=False;self.fail_final_read=False

    def execute(self, operations, stage):
        self.calls.append(stage);results=[]
        for op in operations:
            path=op.relative_url.split('?',1)[0]
            if op.method=='GET':
                if self.fail_final_read and stage=='activation_readback':
                    self.fail_final_read=False;raise BatchTransportError(stage,{'error':'offline read failure'})
                found=None
                for tree in self.trees:
                    if path==tree['campaign']['id']:found=tree['campaign']
                    elif path==tree['campaign']['id']+'/adsets':found=tree['adsets']
                    elif path==tree['campaign']['id']+'/ads':found=tree['ads']
                if found is None:raise AssertionError('unexpected GET path')
                results.append(BatchResult(op.name,200,copy.deepcopy(found)))
            else:
                self.posts.append((path,dict(op.body)))
                fail=self.fail_post_number==len(self.posts)
                if fail and not self.apply_then_fail:
                    self.fail_post_number=None;raise BatchTransportError(stage,{'error':'offline write uncertain'})
                for tree in self.trees:
                    nodes=[tree['campaign']]+tree['adsets']['data']+tree['ads']['data']
                    for node in nodes:
                        if node['id']==path:node['status']='ACTIVE';node['configured_status']='ACTIVE'
                if fail:
                    self.fail_post_number=None;raise BatchTransportError(stage,{'error':'offline response lost after effect'})
                results.append(BatchResult(op.name,200,{'success':True}))
        return results


class BarrierActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        req,src,account,_=case(1);req['status']='ACTIVE';req['quantity']=2
        target=compiler.build(req,src,114,account);self.registry=MediaRegistry(self.root/'media.json')
        self.target=Manifest.from_dict(prevalidate_payload(target,self.registry))
        creation=copy.deepcopy(target)
        for c in creation['campaigns']:c['status']='PAUSED'
        self.creation=Manifest.from_dict(prevalidate_payload(creation,self.registry))
        aid=account['shein_profile']['account_id']
        self.config={'enabled':True,'write_enabled':True,'require_prevalidated_manifest':True,'accounts':{aid:account},'state_root':str(self.root/'state'),'audit_root':str(self.root/'audit')}
        created=CampaignEngine(self.config,transport_factory=lambda a:FakeBatchTransport(a)).execute(self.creation)
        self.trees=[]
        for idx,cid in enumerate(created['campaign_ids']):
            spec=self.creation.campaigns[idx]
            self.trees.append({'campaign':{'id':cid,'account_id':aid,'name':spec.name,'status':'PAUSED','configured_status':'PAUSED','effective_status':'PAUSED','daily_budget':'3000','bid_strategy':'LOWEST_COST_WITHOUT_CAP','start_time':spec.start_time},
                'adsets':{'data':[{'id':f'set-{idx}','name':spec.adset_name,'status':'PAUSED','configured_status':'PAUSED','start_time':spec.start_time,'promoted_object':{'pixel_id':'pixel-test','custom_event_type':'ADD_TO_WISHLIST'}}]},
                'ads':{'data':[{'id':f'ad-{idx}','name':spec.ads[0].name,'adset_id':f'set-{idx}','status':'PAUSED','configured_status':'PAUSED','source_ad_id':spec.ads[0].source_ad_id,'creative':{'id':f'creative-{idx}','effective_object_story_id':spec.ads[0].creative_payload['object_story_id'],'object_story_id':spec.ads[0].creative_payload['object_story_id'],'url_tags':spec.ads[0].creative_payload['url_tags']}}]}})
        self.proof={'verified':True,'request_id':self.target.request_id,'creation_digest':self.creation.digest,'target_digest':self.target.digest,'trees':copy.deepcopy(self.trees)}
        self.transport=OfflineActivationTransport(self.trees)
        self.engine=CampaignEngine(self.config,transport_factory=lambda a:self.transport)

    def activate(self):
        return self.engine.activate_verified(self.target,self.creation,self.proof)

    def test_success_only_status_writes_and_preserves_budget_schedule(self):
        out=self.activate();self.assertEqual(out['status'],'COMPLETE_FUTURE_ACTIVE')
        self.assertTrue(all(body=={'status':'ACTIVE'} for _,body in self.transport.posts))
        self.assertEqual(len(self.transport.posts),6)
        self.assertTrue(all(t['campaign']['daily_budget']=='3000' for t in self.trees))
        before=len(self.transport.posts);self.activate();self.assertEqual(len(self.transport.posts),before)

    def test_no_qa_barrier_no_writes(self):
        self.proof['verified']=False
        with self.assertRaises(ValueError):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_digest_tampering_no_writes(self):
        self.proof['target_digest']='wrong'
        with self.assertRaises(ValueError):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_missing_tree_no_activation(self):
        self.proof['trees'].pop()
        with self.assertRaises(ValueError):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_mid_children_failure_keeps_root_paused_and_resumes_missing_only(self):
        self.transport.fail_post_number=2
        with self.assertRaises(BatchTransportError):self.activate()
        self.assertTrue(all(t['campaign']['status']=='PAUSED' for t in self.trees))
        self.activate()
        self.assertEqual(sum(path=='set-0' for path,_ in self.transport.posts),1)
        self.assertTrue(all(t['campaign']['status']=='ACTIVE' for t in self.trees))

    def test_uncertain_root_success_is_read_back_not_reposted(self):
        self.transport.fail_post_number=3;self.transport.apply_then_fail=True
        with self.assertRaises(BatchTransportError):self.activate()
        cid=self.trees[0]['campaign']['id'];self.assertEqual(self.trees[0]['campaign']['status'],'ACTIVE')
        self.activate();self.assertEqual(sum(path==cid for path,_ in self.transport.posts),1)

    def test_final_read_failure_never_replays_confirmed_status_writes(self):
        self.transport.fail_final_read=True
        with self.assertRaises(BatchTransportError):self.activate()
        self.activate();self.assertEqual(len(self.transport.posts),6)

    def test_quota_deferral_zero_post_then_same_request_resume(self):
        original=self.engine.quota.reserve
        def denied(*a,**k):raise QuotaBlocked({'retry_after_seconds':1})
        self.engine.quota.reserve=denied
        out=self.activate();self.assertEqual(out['status'],'ACTIVATION_DEFERRED');self.assertEqual(self.transport.posts,[])
        self.engine.quota.reserve=original
        out=self.activate();self.assertEqual(out['status'],'COMPLETE_FUTURE_ACTIVE')

    def test_immutable_drift_after_qa_rejected_before_status_write(self):
        self.trees[0]['campaign']['daily_budget']='4000'
        with self.assertRaises(ValueError):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_renderer_thumbnail_url_rotation_is_not_copy_or_media_drift(self):
        story={'page_id':'page','video_data':{'video_id':'same-video','message':'same copy','image_url':'https://example.test/old'}}
        self.proof['trees'][0]['ads']['data'][0]['creative']['object_story_spec']=copy.deepcopy(story)
        self.trees[0]['ads']['data'][0]['creative']['object_story_spec']=copy.deepcopy(story)
        self.trees[0]['ads']['data'][0]['creative']['object_story_spec']['video_data']['image_url']='https://example.test/new'
        self.assertEqual(self.activate()['status'],'COMPLETE_FUTURE_ACTIVE')

if __name__=='__main__':unittest.main()
