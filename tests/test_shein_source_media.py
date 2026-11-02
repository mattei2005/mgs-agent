"""Offline fixtures only. No provider writes or credentials."""
import copy
import fcntl
import json
import sys
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_shein_decision_wait as fixtures
from ares_campaign_v3 import shein_source_media as sm, shein_request_queue as q, shein_decision_wait as dw


class SourceMediaTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DecisionWaitTests()
        self.fixture.setUp()
        f = self.fixture
        self.base = f.base
        self.request = {k:v for k,v in f.request.items() if k != 'campaign_groups'}
        self.request.update(mode='pure_clone', source_number=11)
        f.inv.with_suffix(f.inv.suffix + '.lock').touch()
        cfg = self.base / 'data/ares/meta-ads/engine-v3/config.json'
        q.atomic(cfg, {'state_root':str(f.eroot), 'accounts':{'123':{'token_item':'FIXTURE'}}})
        checkpoint=json.loads(f.cp.read_text())
        checkpoint['bundles']=[{'ad_ids':['OLD-AD-C1','OLD-AD-C2'],'adset_ids':['OLD-SET-C1','OLD-SET-C2']}]
        q.atomic(f.cp,checkpoint);f.seal()
        self.old_live = {cid:{'campaign':{'id':cid,'account_id':'123','status':'PAUSED'},
            'adsets':{'data':[{'id':'OLD-SET-'+cid,'status':'PAUSED'}]},
            'ads':{'data':[{'id':'OLD-AD-'+cid,'status':'PAUSED','creative':{'id':'OLD-CR-'+cid,
                'object_story_spec':{'video_data':{'video_id':'old-video'}}}}]}} for cid in ['C1','C2']}
        self.campaign = {'id':'SOURCE','account_id':'123','name':'011 - fixture','status':'ACTIVE'}
        self.children = {'adsets':{'data':[{'id':'SET','account_id':'123','campaign_id':'SOURCE','status':'ACTIVE'}]},
            'ads':{'data':[{'id':'AD','account_id':'123','campaign_id':'SOURCE','adset_id':'SET','status':'ACTIVE',
                'source_ad_id':'SHARED-TEMPLATE-NOT-MEDIA','creative':{'id':'CR','object_story_spec':{'link_data':{'image_hash':'new-hash'}}}}]}}
        common = Mock(); common.get_token_from_1password.return_value = ('FIXTURE','field')
        self.auth = patch.object(q,'authorize_queue_request',return_value={'account_id':'123'})
        self.loader = patch('ares_campaign_v3.shein_single_clone._load_common',return_value=common)
        self.batch = patch('ares_campaign_v3.shein_single_clone._batch',side_effect=self.read)
        self.historical = patch('ares_campaign_v3.shein_single_clone._readback',side_effect=lambda c,t,cid:copy.deepcopy(self.old_live[cid]))
        self.auth.start(); self.loader.start(); self.batch.start();self.historical.start()
        self.addCleanup(self.auth.stop);self.addCleanup(self.loader.stop);self.addCleanup(self.batch.stop)
        self.addCleanup(self.historical.stop)
        self.addCleanup(f.tearDown)

    def read(self, common, token, requests):
        if requests[0]['name']=='campaigns': return {'campaigns':{'data':[copy.deepcopy(self.campaign)]}}
        return copy.deepcopy(self.children)

    def resolve(self): return sm.resolve(self.request,'123',self.base)
    def deps(self): return q.dependencies(self.request,'123',self.base)

    def test_live_typed_disjoint_proof_releases_only_dependency(self):
        before=[p.read_bytes() for p in [self.fixture.inv,self.fixture.spath,self.fixture.cp,self.fixture.lease]]
        proof=self.resolve()
        self.assertIsInstance(proof,sm.SourceMediaProof)
        self.assertEqual(proof.source_campaign_id,'SOURCE');self.assertEqual(proof.reservations[0]['asset_id'],'NEW')
        self.assertEqual(self.deps(),[])
        self.assertEqual(before,[p.read_bytes() for p in [self.fixture.inv,self.fixture.spath,self.fixture.cp,self.fixture.lease]])
        self.assertFalse(q.terminal(self.fixture.state));self.assertTrue(dw.pending(self.base,self.fixture.owner))

    def test_missing_source_proof_never_treats_empty_as_disjoint(self):
        self.children['ads']['data'][0]['creative']={'id':'CR'}
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_shared_primary_hash_blocks(self):
        self.children['ads']['data'][0]['creative']['object_story_spec']['link_data']['image_hash']='old-video'
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_shared_inventory_checksum_blocks(self):
        self.fixture.rows[0]['clean_checksum']='old-bytes';self.fixture.write_rows()
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_active_reservation_blocks_and_is_never_transferred(self):
        self.fixture.rows[0]['reservation_request_id']='active-owner';self.fixture.write_rows()
        self.assertEqual(self.deps(),['active-owner'])
        before=self.fixture.inv.read_bytes()
        q.claim_terminal(self.request,'123',self.base)
        self.assertEqual(before,self.fixture.inv.read_bytes())

    def test_terminal_reservation_stays_with_original_lineage(self):
        self.fixture.rows[0]['reservation_request_id']='complete-owner';self.fixture.write_rows()
        q.atomic(q.root(self.base)/'single-clone/complete-owner/state.json',{'phase':'COMPLETE','summary':{'campaigns':[{'campaign_id':'C'}]}})
        self.assertEqual(self.deps(),[])
        before=self.fixture.inv.read_bytes();q.claim_terminal(self.request,'123',self.base)
        self.assertEqual(before,self.fixture.inv.read_bytes())

    def test_partition_mismatch_in_reservation_fails_closed(self):
        self.fixture.rows[0]['reservation_request_id']='other-owner';self.fixture.write_rows()
        q.atomic(q.root(self.base)/'single-clone/other-owner/state.json',{'request':{'source_channel_id':'OTHER'}})
        with self.assertRaisesRegex(ValueError,'partition'):self.deps()

    def test_foreign_lease_blocks(self):
        q.atomic(self.fixture.lease,{'account_id':'123','request_id':'other','status':'IN_PROGRESS','blocks_readers':True})
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_account_lock_blocks(self):
        with self.fixture.alock.open('rb') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.deps(),[self.fixture.owner])

    def test_writer_update_lock_blocks(self):
        with self.fixture.lease.with_suffix('.lock').open('rb') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.deps(),[self.fixture.owner])

    def test_inventory_update_lock_blocks(self):
        with self.fixture.inv.with_suffix('.jsonl.lock').open('rb') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.deps(),[self.fixture.owner])

    def test_missing_lock_blocks(self):
        self.fixture.alock.unlink();self.assertEqual(self.deps(),[self.fixture.owner])

    def test_wrong_source_account_blocks(self):
        self.campaign['account_id']='456';self.assertEqual(self.deps(),[self.fixture.owner])

    def test_wrong_child_account_or_parent_blocks(self):
        for field in ['account_id','campaign_id','adset_id']:
            with self.subTest(field=field):
                original=copy.deepcopy(self.children);self.children['ads']['data'][0][field]='OTHER'
                self.assertEqual(self.deps(),[self.fixture.owner]);self.children=original

    def test_missing_or_ambiguous_source_blocks(self):
        self.campaign['name']='012 - wrong';self.assertEqual(self.deps(),[self.fixture.owner])
        with patch('ares_campaign_v3.shein_single_clone._batch',return_value={'campaigns':{'data':[self.campaign,self.campaign]}}):
            self.request['source_number']=12;self.assertEqual(self.deps(),[self.fixture.owner])

    def test_pagination_incomplete_blocks(self):
        self.children['ads']['paging']={'next':'FIXTURE'};self.assertEqual(self.deps(),[self.fixture.owner])

    def test_stale_or_future_proof_rejected(self):
        proof=self.resolve()
        for at in [time.time()-121,time.time()+60]:
            with self.assertRaises(ValueError):replace(proof,observed_at=at).validate(self.request,'123',self.base)

    def test_changed_inventory_rejects_receipt(self):
        proof=self.resolve();self.fixture.inv.write_text(self.fixture.inv.read_text()+'\n')
        with self.assertRaises(ValueError):proof.validate(self.request,'123',self.base)

    def test_wrong_request_account_channel_number_rejects_receipt(self):
        proof=self.resolve()
        for key,value in [('account','456'),('source_channel_id','OTHER'),('source_number',12),('budget_usd','999')]:
            with self.subTest(key=key),self.assertRaises(ValueError):proof.validate({**self.request,key:value},'123',self.base)

    def test_untyped_receipt_never_accepted(self):
        self.assertFalse(dw.inert_for(self.request,self.fixture.state,[],self.base,source_proof=self.resolve().receipt()))

    def test_image_afs_and_video_variants_captured(self):
        self.children['ads']['data'][0]['creative']={'id':'CR','asset_feed_spec':{
            'images':[{'hash':'img'}],'videos':[{'video_id':'vid'}]}}
        self.fixture.rows += [{'asset_id':'IMG','image_hash':'img','checksum':'img-bytes'},
                              {'asset_id':'VID','video_id':'vid','checksum':'vid-bytes'}]
        self.fixture.write_rows()
        proof=self.resolve();self.assertIn(('identity','vid'),proof.identities);self.assertIn(('identity','img'),proof.identities)

    def test_unresolved_inventory_lineage_fails_closed(self):
        self.fixture.rows=[];self.fixture.write_rows()
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_ambiguous_media_alias_lineage_fails_closed(self):
        self.fixture.rows.append({'asset_id':'OTHER','image_hash':'new-hash','checksum':'other'})
        self.fixture.write_rows();self.assertEqual(self.deps(),[self.fixture.owner])

    def test_thumbnail_without_primary_video_is_not_media_proof(self):
        self.children['ads']['data'][0]['creative']={'id':'CR','object_story_spec':{'video_data':{'image_hash':'new-hash'}}}
        self.assertEqual(self.deps(),[self.fixture.owner])

    def test_transitive_alias_closure_independent_of_inventory_order(self):
        rows=[{'image_hash':'bridge','checksum':'old'}, {'image_hash':'new','checksum':'bridge'}]
        identities,linked=sm.expand({('identity','new')},rows)
        self.assertIn(('identity','old'),identities);self.assertEqual(len(linked),2)

    def test_source_lineage_is_not_equivalent_to_media_reuse(self):
        self.fixture.state['source']={'ads':[{'source_ad_id':'SHARED-TEMPLATE-NOT-MEDIA'}]};self.fixture.seal()
        self.assertEqual(self.deps(),[])

    def test_stale_historical_evidence_still_blocks(self):
        self.fixture.spath.write_text('{}');self.assertEqual(self.deps(),[self.fixture.owner])

    def test_live_historical_active_changed_media_or_ids_blocks(self):
        for change in ['status','media','ids']:
            with self.subTest(change=change):
                before=copy.deepcopy(self.old_live)
                if change=='status':self.old_live['C1']['campaign']['status']='ACTIVE'
                elif change=='media':self.old_live['C1']['ads']['data'][0]['creative']['object_story_spec']['video_data']['video_id']='CHANGED'
                else:self.old_live['C1']['ads']['data'][0]['id']='CHANGED'
                self.assertEqual(self.deps(),[self.fixture.owner]);self.old_live=before

    def test_changed_historical_digest_invalidates_proof(self):
        proof=self.resolve();self.fixture.spath.write_text(self.fixture.spath.read_text()+'\n')
        with self.assertRaises(ValueError):proof.validate(self.request,'123',self.base)

    def test_maintenance_hold_and_foreground_still_prevent_dispatch(self):
        q.enqueue(self.request,'campaign',[self.fixture.owner],self.base)
        path=q.job_path(self.base,self.request['request_id']);job=json.loads(path.read_text())
        for gates in [{'maintenance_hold':{'task':'FIXTURE'}},{'dispatch_owner':'foreground'}]:
            q.atomic(path,{**job,**gates})
            with patch.object(q.subprocess,'run') as run,patch.object(q,'notify') as notify:
                q.tick(job,self.base)
            run.assert_not_called();notify.assert_not_called()

    def test_same_resume_lease_allowed_but_foreign_active_writer_still_blocks(self):
        q.atomic(q.root(self.base)/'single-clone'/self.request['request_id']/'state.json',{'request':self.request,'phase':'RECOVERY_PENDING'})
        q.atomic(self.fixture.lease,{'account_id':'123','request_id':self.request['request_id'],'status':'DEFERRED_QUOTA','blocks_readers':True})
        self.assertEqual(self.deps(),[])
        q.atomic(q.root(self.base)/'single-clone/foreign/state.json',{'request':{'account':'123','request_id':'foreign'},'phase':'ENGINE_PENDING'})
        self.assertEqual(self.deps(),['foreign'])

    def test_canonical_defaulted_resume_is_same_immutable_intake(self):
        op=self.base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
        q.atomic(op,{'operation_id':'SHEIN-US-DIRECT','request_defaults':{
            'final_status':'ACTIVE','authority':'344196393512075265','scope':'new_creation_requests_only'}})
        normalized={**self.request,'status':'ACTIVE'}
        q.atomic(q.root(self.base)/'single-clone'/self.request['request_id']/'state.json',{'request':normalized,'phase':'RECOVERY_PENDING'})
        q.atomic(self.fixture.lease,{'account_id':'123','request_id':self.request['request_id'],'status':'DEFERRED_QUOTA','blocks_readers':True})
        self.assertEqual(self.deps(),[])
        normalized['budget_usd']='999'
        q.atomic(q.root(self.base)/'single-clone'/self.request['request_id']/'state.json',{'request':normalized,'phase':'RECOVERY_PENDING'})
        self.assertEqual(self.deps(),[self.fixture.owner])

if __name__=='__main__':unittest.main()
