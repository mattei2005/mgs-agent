"""Regression for explicit NOW/inherited budget; no Meta network calls."""
import copy
import unittest
from datetime import datetime,timezone,timedelta
from test_shein_general_runtime import case
from test_shein_single_clone_route import fixture,live_fixture
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3.schema import Manifest,ManifestError

class NowIntentTests(unittest.TestCase):
    def test_request_accepts_now_and_budget_reference_without_manual_lookup(self):
        r,_,_,_=case(1,status='ACTIVE');r.pop('start_time');r.pop('budget_usd');r.update(start_now=True,budget_from_reference=True)
        route.validate_request(r)

    def test_explicit_now_survives_elapsed_technical_buffer_in_schema(self):
        r,s,a,_=case(1,status='ACTIVE');r.update(start_now=True,start_time=(datetime.now(timezone.utc)-timedelta(seconds=60)).replace(microsecond=0).isoformat())
        p=compiler.build(r,s,114,a);self.assertEqual(p['campaigns'][0]['start_intent'],'IMMEDIATE')
        manifest=Manifest.from_dict(p);self.assertEqual(manifest.campaigns[0].start_intent,'IMMEDIATE')

    def test_scheduled_start_expired_still_rejected(self):
        r,s,a,_=case(1,status='ACTIVE');r['start_time']='2000-01-01T00:00:00-04:00'
        with self.assertRaises(ManifestError):Manifest.from_dict(compiler.build(r,s,114,a))

    def test_paused_in_process_does_not_replay_or_reject_valid_media_tree(self):
        r,s,a=fixture();p=route.build_manifest(r,s,114,a);live=live_fixture(p,s);live['campaign']['effective_status']='IN_PROCESS'
        self.assertEqual(route.verify_readback(p,s,live),[])

    def test_resolution_uses_live_budget_and_integer_time_once(self):
        r,s,a,_=case(1,status='ACTIVE');r.pop('start_time');r.pop('budget_usd');r.update(start_now=True,budget_from_reference=True)
        instant=datetime(2026,10,8,16,0,0,987654,tzinfo=timezone.utc)
        resolved=route.resolve_intent(r,s,now=instant)
        self.assertEqual(resolved['budget_usd'],'40')
        self.assertEqual(datetime.fromisoformat(resolved['start_time']).microsecond,0)
        self.assertEqual(r.get('budget_usd'),None)

import test_shein_single_media_activation as single_tests

class NowRunnerTests(single_tests.SingleRunnerQATests):
    def test_inherited_budget_now_completes_same_runner_without_manual_resolution(self):
        self.request.pop('start_time');self.request.pop('budget_usd')
        self.request.update(start_now=True,budget_from_reference=True)
        resolved=route.resolve_intent(self.request,self.source)
        # Simulate QA finishing after the technical start second; intent is still NOW.
        resolved['start_time']=(datetime.now(timezone.utc)-timedelta(seconds=40)).replace(microsecond=0).isoformat()
        draft=route.build_manifest(resolved,self.source,114,self.account)
        creation,target,barrier=route.seal_creation_pair(draft,self.config,route.MediaRegistry(self.root/'registry.json'))
        self.prepare.return_value=({'source':self.source,'account':{},'prerequisites':{},'number':114,'page_id':single_tests.PAGE,'manifest':creation,'target_manifest':target,'batch_barrier':barrier,'resolved_request':resolved},'OFFLINE_PAGE_TOKEN')
        self.live=single_tests.live_fixture(creation,self.source);self.live['ads']['data'][0]['creative']['id']='created-creative';self.live['campaign']['effective_status']='IN_PROCESS'
        result=route.run_request(self.request,confirm_execute=True)
        self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
        self.assertEqual(result['budget_usd'],40)
        self.assertEqual(self.prepare.call_count,1);self.assertEqual(self.engine.execute.call_count,1);self.assertEqual(self.engine.activate_verified.call_count,1)
        self.assertEqual(self.engine.activate_verified.call_args.args[0].campaigns[0].start_intent,'IMMEDIATE')
        self.assertNotIn('start_time',self.state()['request'])

class NowCentralActivationTests(single_tests.SingleCentralActivationTests):
    def setUp(self):
        super().setUp()
        target=copy.deepcopy(self.target.raw);target['campaigns'][0].update(start_intent='IMMEDIATE',start_time=(datetime.now(timezone.utc)-timedelta(seconds=30)).replace(microsecond=0).isoformat());target['request_id']+='-now'
        creation=copy.deepcopy(target);creation['campaigns'][0]['status']='PAUSED'
        from ares_campaign_v3.prevalidation import prevalidate_payload
        from ares_campaign_v3.engine import CampaignEngine
        from ares_campaign_v3.transport import FakeBatchTransport
        self.target=Manifest.from_dict(prevalidate_payload(target,self.registry));self.creation=Manifest.from_dict(prevalidate_payload(creation,self.registry))
        output=CampaignEngine(self.config,transport_factory=lambda aid:FakeBatchTransport(aid)).execute(self.creation)
        tree=self.trees[0];tree['campaign']['id']=output['campaign_ids'][0];tree['campaign']['start_time']=self.target.campaigns[0].start_time;tree['adsets']['data'][0]['start_time']=self.target.campaigns[0].start_time
        self.proof.update(request_id=self.target.request_id,creation_digest=self.creation.digest,target_digest=self.target.digest,trees=copy.deepcopy(self.trees),execution_started_at=datetime.now(timezone.utc).isoformat())
        self.proof['media_qa']={tree['campaign']['id']:{'verified':True,'ad_ids':[a['id'] for a in tree['ads']['data']],'creative_ids':[a['creative']['id'] for a in tree['ads']['data']]}}
        self.config['shein_execution_sla']={'enabled':True,'quantity':1,'target_seconds':144}
        self.transport=single_tests.OfflineActivationTransport(self.trees);self.engine=CampaignEngine(self.config,transport_factory=lambda aid:self.transport)

    def test_elapsed_now_clock_activates_after_bound_media_proof(self):
        out=self.activate();self.assertEqual(out['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len(self.transport.posts),3)

    def test_144_second_target_breach_keeps_root_paused_without_writes(self):
        self.proof['execution_started_at']=(datetime.now(timezone.utc)-timedelta(seconds=145)).isoformat()
        out=self.activate();self.assertEqual(out['status'],'E2E_TARGET_EXCEEDED');self.assertEqual(self.transport.posts,[]);self.assertEqual(self.trees[0]['campaign']['status'],'PAUSED')

# Run only the explicit NOW cases for these fixture subclasses.
for name in list(single_tests.SingleRunnerQATests.__dict__):
    if name.startswith('test_'):setattr(NowRunnerTests,name,None)
for cls in [single_tests.SingleCentralActivationTests,single_tests.activation_tests.BarrierActivationTests]:
    for name in cls.__dict__:
        if name.startswith('test_'):setattr(NowCentralActivationTests,name,None)

del cls

if __name__=='__main__':unittest.main()
