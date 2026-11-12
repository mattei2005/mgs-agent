"""Offline coordination-only contract; provider writes are forbidden."""
import copy
import fcntl
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import test_shein_manual_takeover as fixtures
from ares_campaign_v3 import shein_manual_observation as obs, shein_manual_takeover as manual
from ares_campaign_v3 import shein_source_media as sm, shein_request_queue as q, shein_single_clone as driver


class ObservationTests(unittest.TestCase):
    setUp = fixtures.ManualTakeoverTests.setUp
    close = fixtures.ManualTakeoverTests.close
    rec = fixtures.ManualTakeoverTests.rec

    def prepare(self):
        self.close()
        self.original_receipt = manual.path(self.base,self.rid).read_bytes()
        self.original_state = self.spath.read_bytes()
        self.campaigns[0]['daily_budget']='12300'
        self.campaigns[1]['adsets'][0]['bid_amount']=105
        return self.register()

    def register(self, **delta):
        pp=obs.policy_path(self.base)
        args={'expected_parent_sha256':manual.sha(manual.path(self.base,self.rid)),
              'expected_job_sha256':manual.sha(self.jp),'expected_lease_sha256':manual.sha(self.lease),
              'expected_policy_sha256':manual.sha(pp) if pp.exists() else None,'maintenance_task_id':'FIXTURE'}
        args.update(delta)
        return obs.register(self.base,self.newrequest,self.rid,**args)

    def test_exact_successor_only_and_parent_immutable_no_qa(self):
        result=self.prepare()
        self.assertEqual(len(result['commercial_deltas']),2)
        self.assertFalse(result['qa_certified']);self.assertEqual(result['campaign_writes'],0)
        self.assertEqual(self.original_receipt,manual.path(self.base,self.rid).read_bytes())
        self.assertEqual(self.original_state,self.spath.read_bytes())
        with self.assertRaises(ValueError):manual.verify_live(self.base,self.rid,None,None)
        result=manual.verify_live(self.base,self.rid,None,None,resume_request=self.newrequest)
        self.assertTrue(result['coordination_observation_sha256'])
        for key,value in [('request_id','OTHER'),('budget_usd','30'),('quantity',10),('source_number',18),
                          ('account','OTHER'),('authorized_by','OTHER'),('start_time','OTHER'),('source_thread_id','OTHER')]:
            with self.subTest(key=key):
                with self.assertRaises((ValueError,OSError,KeyError)):
                    obs.verify(self.base,{**self.newrequest,key:value},self.rid,self.campaigns)
        self.assertNotIn(manual.STATUS,q.TERMINAL)
        with self.assertRaises(ValueError):manual.deny_replay(self.base,self.rid)

    def test_strict_identity_config_media_and_later_commercial_change(self):
        self.prepare()
        mutations=[lambda c:c[0].update(daily_budget='12301'),lambda c:c[0].update(bid_strategy='OTHER'),
            lambda c:c[0].update(start_time='OTHER'),lambda c:c[0].update(name='OTHER'),
            lambda c:c[0]['adsets'][0].update(id='OTHER'),lambda c:c[0]['adsets'][0].update(bid_amount=106),
            lambda c:c[0]['ads'][0].update(creative_id='OTHER'),
            lambda c:c[0]['ads'][0].update(primary_media=[['identity','OTHER']]),
            lambda c:c[0]['ads'][0].update(status='DELETED')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                current=copy.deepcopy(self.campaigns);mutate(current)
                with self.assertRaises(ValueError):obs.verify(self.base,self.newrequest,self.rid,current)
        for index,mutate in enumerate(mutations):
            if index in {0,5}:  # New observation can capture budget/bid; committed receipt cannot drift.
                continue
            current=copy.deepcopy(self.campaigns);mutate(current)
            with self.assertRaises(ValueError):obs.commercial_deltas(self.rec()['campaigns'],current)

    def test_review_pause_mutable_but_does_not_rewrite_first_observation(self):
        self.prepare();p=obs.receipt_path(self.base,self.newrequest,self.rid);before=p.read_bytes()
        self.campaigns[0]['ads'][0].update(status='PAUSED',effective_status='WITH_ISSUES',issue_codes=[1487083])
        obs.verify(self.base,self.newrequest,self.rid,self.campaigns)
        self.register();self.assertEqual(before,p.read_bytes())

    def test_cas_job_policy_parent_lease_and_missing_live_approval(self):
        self.close();self.campaigns[0]['daily_budget']='12300'
        for key in ['expected_parent_sha256','expected_job_sha256','expected_lease_sha256','expected_policy_sha256']:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,'CAS'):self.register(**{key:'WRONG'})
        self.get_messages['1569530861022355457']['author']['id']='OTHER'
        with self.assertRaises(ValueError):self.register()
        self.assertFalse(obs.receipt_path(self.base,self.newrequest,self.rid).exists())

    def test_real_locks_and_job_owner_conflicts(self):
        self.close();self.campaigns[0]['daily_budget']='12300'
        for p in [self.alock,self.jp.with_suffix('.dispatch.lock'),self.jp.with_suffix('.lock'),self.lease.with_suffix('.lock')]:
            with p.open('a+') as h:
                fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):self.register()
        for delta in [{'maintenance_hold':False},{'attempts':1},{'notification':'OTHER'},{'dispatch_owner':'worker'}]:
            q.atomic(self.jp,{**self.job,**delta})
            with self.assertRaises(ValueError):self.register()
        q.atomic(self.jp,self.job)
        self.store.claim(self.account,'FOREIGN')
        with self.assertRaises(ValueError):self.register()

    def test_crash_before_grant_fails_closed_and_recovers_idempotently(self):
        self.close();self.campaigns[0]['daily_budget']='12300'
        real_atomic=q.atomic
        def fail_policy(p,v):
            if p==obs.policy_path(self.base):raise RuntimeError('fixture-crash')
            return real_atomic(p,v)
        with patch.object(q,'atomic',side_effect=fail_policy):
            with self.assertRaises(RuntimeError):self.register()
        p=obs.receipt_path(self.base,self.newrequest,self.rid);before=p.read_bytes()
        with self.assertRaises(OSError):obs.validate(self.base,self.newrequest,self.rid)
        self.register();self.assertEqual(before,p.read_bytes())
        policy_before=obs.policy_path(self.base).read_bytes();self.register()
        self.assertEqual(policy_before,obs.policy_path(self.base).read_bytes())

    def test_receipt_or_grant_tamper_rejected(self):
        self.prepare();p=obs.receipt_path(self.base,self.newrequest,self.rid);before=p.read_bytes()
        r=manual.read(p);r['qa_certified']=True;q.atomic(p,r)
        with self.assertRaises(ValueError):obs.validate(self.base,self.newrequest,self.rid)
        p.write_bytes(before);policy=manual.read(obs.policy_path(self.base));policy['grants'][self.new][self.rid]['receipt_sha256']='WRONG'
        q.atomic(obs.policy_path(self.base),policy)
        with self.assertRaises(ValueError):obs.validate(self.base,self.newrequest,self.rid)

    def test_real_engine_replay_fence_with_current_manifest_shape(self):
        from types import SimpleNamespace
        from ares_campaign_v3.engine import CampaignEngine
        self.prepare()
        manifest=SimpleNamespace(request_id=self.rid,operation='SHEIN-US-DIRECT',raw={})
        with self.assertRaisesRegex(ValueError,'manual takeover'):
            CampaignEngine.execute.__wrapped__(SimpleNamespace(config={'state_root':str(self.eroot)}),manifest)

    def test_successor_authority_denied_before_any_observation(self):
        self.close();self.campaigns[0]['daily_budget']='12300'
        with patch.object(q,'authorize_queue_request',side_effect=ValueError('denied')):
            with self.assertRaises(ValueError):self.register()
        self.assertFalse(obs.receipt_path(self.base,self.newrequest,self.rid).exists())

    def test_typed_resolver_integration_reservations_shared_media_ttl_and_digest(self):
        self.prepare();self.inv.with_suffix('.jsonl.lock').touch()
        source={'id':'FIXTURE-SOURCE','account_id':self.account,'name':'049 - FIXTURE','status':'ACTIVE'}
        children={'adsets':{'data':[{'id':'NEWSET','account_id':self.account,'campaign_id':source['id'],'status':'ACTIVE'}]},
            'ads':{'data':[{'id':'NEWAD','account_id':self.account,'campaign_id':source['id'],'adset_id':'NEWSET','status':'ACTIVE',
                'creative':{'id':'NEWCREATIVE','object_story_spec':{'link_data':{'image_hash':'new-hash'}}}}]}}
        def batch(common,token,queries):
            return {'campaigns':{'data':[source]}} if queries[0]['name']=='campaigns' else copy.deepcopy(children)
        with patch.object(driver,'_batch',side_effect=batch):
            proof=sm.resolve(self.newrequest,self.account,self.base)
            self.assertEqual(q.dependencies(self.newrequest,self.account,self.base),[])
            with self.assertRaises(ValueError):replace(proof,observed_at=proof.observed_at-121).validate(self.newrequest,self.account,self.base)
            row=json.loads(self.inv.read_text());row['reservation_request_id']=self.rid;self.inv.write_text(json.dumps(row)+'\n')
            self.assertEqual(q.dependencies(self.newrequest,self.account,self.base),[self.rid])
            row.pop('reservation_request_id');row['video_id']='old-video-0-0';self.inv.write_text(json.dumps(row)+'\n')
            self.assertEqual(q.dependencies(self.newrequest,self.account,self.base),[self.rid])
            row.pop('video_id');self.inv.write_text(json.dumps(row)+'\n')
            proof=sm.resolve(self.newrequest,self.account,self.base)
            policy=manual.read(obs.policy_path(self.base));policy['grants'].clear();q.atomic(obs.policy_path(self.base),policy)
            with self.assertRaises(ValueError):proof.validate(self.newrequest,self.account,self.base)
            self.assertEqual(q.dependencies(self.newrequest,self.account,self.base),[self.rid])


if __name__=='__main__':unittest.main()
