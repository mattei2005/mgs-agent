"""Single-campaign QA/activation regressions; offline transports only."""
import copy
import json
import unittest
from unittest.mock import patch
import test_shein_batch_barrier_activation as activation_tests
import test_shein_single_clone_route as route_tests
OfflineActivationTransport=activation_tests.OfflineActivationTransport
live_fixture=route_tests.live_fixture
PAGE=route_tests.PAGE
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.engine import CampaignEngine,ExecutionFailed
from ares_campaign_v3.transport import FakeBatchTransport
from ares_campaign_v3 import shein_single_clone as driver
from ares_campaign_v3.shein_qa import verify_media as REAL_MEDIA_QA
from test_shein_media_qa import PLAYABLE,CHROME


class SingleCentralActivationTests(activation_tests.BarrierActivationTests):
    def setUp(self):
        super().setUp()
        self.config['shein_media_qa']={'enabled':True}
        target=copy.deepcopy(self.target.raw);target['request_id']+='-single';target['campaigns']=target['campaigns'][:1]
        creation=copy.deepcopy(target);creation['campaigns'][0]['status']='PAUSED'
        self.target=Manifest.from_dict(prevalidate_payload(target,self.registry));self.creation=Manifest.from_dict(prevalidate_payload(creation,self.registry))
        result=CampaignEngine(self.config,transport_factory=lambda aid:FakeBatchTransport(aid)).execute(self.creation)
        self.trees=self.trees[:1];self.trees[0]['campaign']['id']=result['campaign_ids'][0]
        self.proof={'verified':True,'request_id':self.target.request_id,'creation_digest':self.creation.digest,'target_digest':self.target.digest,'trees':copy.deepcopy(self.trees),
            'media_qa':{t['campaign']['id']:{'verified':True,'ad_ids':[a['id'] for a in t['ads']['data']],'creative_ids':[a['creative']['id'] for a in t['ads']['data']]} for t in self.trees}}
        self.transport=OfflineActivationTransport(self.trees);self.engine=CampaignEngine(self.config,transport_factory=lambda aid:self.transport)

    # Base class assumes two trees; override count/index-sensitive cases only.
    def test_success_only_status_writes_and_preserves_budget_schedule(self):
        self.assertEqual(self.activate()['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len(self.transport.posts),3)
        self.assertTrue(all(body=={'status':'ACTIVE'} for _,body in self.transport.posts))
        self.activate();self.assertEqual(len(self.transport.posts),3)

    def test_final_read_failure_never_replays_confirmed_status_writes(self):
        self.transport.fail_final_read=True
        from ares_campaign_v3.transport import BatchTransportError
        with self.assertRaises(BatchTransportError):self.activate()
        self.activate();self.assertEqual(len(self.transport.posts),3)

    def test_missing_rendered_media_proof_blocks_every_status_write(self):
        self.proof.pop('media_qa')
        with self.assertRaisesRegex(ValueError,'media QA proof'):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_full_media_drift_after_proof_blocks_activation(self):
        self.proof['trees'][0]['ads']['data'][0]['creative']['asset_feed_spec']={'videos':[{'video_id':'expected'}]}
        self.trees[0]['ads']['data'][0]['creative']['asset_feed_spec']={'videos':[{'video_id':'wrong'}]}
        with self.assertRaisesRegex(ValueError,'flexible media'):self.activate()
        self.assertEqual(self.transport.posts,[])

    def test_direct_active_creation_cannot_bypass_media_barrier(self):
        with self.assertRaisesRegex(ExecutionFailed,'remain PAUSED'):self.engine.execute(self.target)
        self.assertEqual(self.transport.posts,[])


class SingleRunnerQATests(PipelineTests):
    def setUp(self):
        super().setUp()
        self.request.update(status='ACTIVE',quantity=1)
        self.account['shein_profile']={'account_id':'7840111366055613','account_name':self.request['account'],'manager_code':'G002','manager_discord_id':'321263240782807040','channel_id':'1548149300826079333','language':'EN','timezone':'America/New_York','tracking_prefix':'b01fb01','utm_medium':'g002-s','destination_base':'https://yolokfx.com/quiz/us/sh2-g002/','page_id':PAGE}
        self.config['shein_batch_activation']={'enabled':True,'minimum_quantity':1};self.config['shein_media_qa']={'enabled':True,'chrome_path':CHROME}
        (self.root/'data/ares/meta-ads/engine-v3/config.json').write_text(json.dumps(self.config))
        draft=driver.build_manifest(self.request,self.source,114,self.account);creation,target,barrier=driver.seal_creation_pair(draft,self.config,driver.MediaRegistry(self.root/'registry.json'))
        self.prepare.return_value=({'source':self.source,'account':{},'prerequisites':{},'number':114,'page_id':PAGE,'manifest':creation,'target_manifest':target,'batch_barrier':barrier},'OFFLINE_PAGE_TOKEN')
        self.live=live_fixture(creation,self.source);self.live['ads']['data'][0]['creative']['id']='created-creative'
        self.readback.side_effect=lambda *args:copy.deepcopy(self.live)
        self.media_qa.side_effect=REAL_MEDIA_QA
        self.renderer=self.stack.enter_context(patch('ares_campaign_v3.shein_qa.render_previews',return_value=[PLAYABLE]))
        def reads(token,requests):
            rows=[]
            for q in requests:
                if q['name']=='budgets':body={'data':[]}
                elif q['path'].endswith('/previews'):body={'data':[{'body':'<iframe src="https://business.facebook.com/ads/api/preview_iframe.php?d=OFFLINE"></iframe>'}]}
                else:raise AssertionError(q)
                rows.append({'name':q['name'],'code':200,'body':body})
            return 200,rows,{}
        self.common.graph_batch_get.side_effect=reads
        def activated(target,creation,proof):
            self.assertTrue(proof['media_qa']['target-campaign']['verified'])
            for node in [self.live['campaign']]+self.live['adsets']['data']+self.live['ads']['data']:node.update(status='ACTIVE',effective_status='ACTIVE')
            return {'status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':['target-campaign']}
        self.engine.activate_verified.side_effect=activated

    # Only run the scenario-specific tests, not inherited legacy PAUSED assumptions.
    def test_single_run_no_media_never_activates(self):
        self.renderer.return_value=[{'videos':[],'images':[]}]
        with self.assertRaisesRegex(ValueError,'playable video'):driver.run_request(self.request,confirm_execute=True)
        self.engine.activate_verified.assert_not_called();self.assertEqual(self.state()['phase'],'POSTPROCESS_PENDING')
        self.assertTrue(all(c.status=='PAUSED' for c in self.engine.execute.call_args.args[0].campaigns))

    def test_single_run_valid_media_activates_after_real_qa_function(self):
        result=driver.run_request(self.request,confirm_execute=True)
        self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(self.engine.execute.call_count,1);self.assertEqual(self.engine.activate_verified.call_count,1)
        self.assertTrue(self.state()['media_qa']['target-campaign']['verified'])

# Avoid inheriting duplicate PAUSED orchestration tests whose fixture intentionally differs.
for name in list(PipelineTests.__dict__):
    if name.startswith('test_'):setattr(SingleRunnerQATests,name,None)

if __name__=='__main__':unittest.main()
