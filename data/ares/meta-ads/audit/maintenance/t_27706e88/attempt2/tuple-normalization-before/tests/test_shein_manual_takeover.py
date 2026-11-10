"""Offline fixtures only; never a provider writer or a real campaign execution."""
import copy
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import shein_manual_takeover as m, shein_prewrite_amendment as amend
from ares_campaign_v3 import shein_request_queue as q, shein_decision_wait as dw, shein_single_clone as driver
from ares_campaign_v3.coordination import AccountWriterLeaseStore, WriterLeaseConflict, reader_block_reason
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.activation import activate


class ManualTakeoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.eroot=self.base/'data/ares/meta-ads/engine-v3/state'
        self.account=m.ACCOUNT;self.rid=m.REQUEST;self.new='shein-1569495587005530205-c049'
        all_messages=json.loads((Path(__file__).parent/'fixtures/shein-manual-takeover-messages.json').read_text())
        self.messages=[x for x in all_messages if x['id'] in m.APPROVALS]
        self.get_messages={x['id']:{**x,'author':{'id':x['author_id']}} for x in all_messages}
        self.request={'request_id':self.rid,'account':m.ACCOUNT,'source_channel_id':m.CHANNEL,'source_thread_id':m.THREAD,'authorized_by':'1055570806945620030'}
        self.newrequest={'request_id':self.new,'account':m.ACCOUNT,'source_channel_id':m.CHANNEL,'source_thread_id':m.THREAD,
                         'authorized_by':'1055570806945620030','source_message_id':'1569495587005530205',
                         'mode':'pure_clone','source_number':49,'quantity':4,'budget_usd':'45',
                         'start_time':'2026-11-10T00:03:00-05:00','status':'ACTIVE'}
        self.cids=['FIXTURE-C'+str(i) for i in range(9)]
        self.campaigns=[]
        for i,cid in enumerate(self.cids):
            ads=[{'id':cid+'-AD'+str(j),'adset_id':cid+'-SET','creative_id':cid+'-CR'+str(j),
                  'status':'PAUSED' if i in [2,6] and j==1 else 'ACTIVE','effective_status':'WITH_ISSUES' if i in [2,6] and j==1 else 'ACTIVE',
                  'primary_media':[['identity','old-video-'+str(i)+'-'+str(j)]],
                  'issue_codes':[2490468] if i in [2,6] and j==1 else [],'ad_review_feedback':None} for j in range(2)]
            self.campaigns.append({'id':cid,'name':str(102+i)+' - FIXTURE','status':'ACTIVE','effective_status':'ACTIVE',
                                   'daily_budget':'3500' if i==1 else '4375','bid_strategy':'COST_CAP','start_time':'FIXTURE',
                                   'adsets':[{'id':cid+'-SET','status':'ACTIVE','effective_status':'ACTIVE','bid_amount':90,'start_time':'FIXTURE'}],'ads':ads})
        self.state={'request':self.request,'phase':'ACTIVATION_PENDING','execution_started_at':'2026-11-09T20:00:00+00:00',
                    'engine_result':{'campaign_ids':self.cids},'manifest':{'campaigns':[{'ads':[{'video_id':'old-video-'+str(i)+'-'+str(j)} for j in range(2)]} for i in range(9)]}}
        self.spath=q.root(self.base)/'single-clone'/self.rid/'state.json'
        q.atomic(self.spath,self.state)
        q.atomic(self.spath.parent/'manifest-sealed.json',{'sealed':'FIXTURE ONLY'})
        q.atomic(self.eroot/'checkpoints'/(self.rid+'-'+self.account+'.json'),{'bundles':[{'ad_ids':[a['id'] for c in self.campaigns for a in c['ads']],
                      'adset_ids':[a['id'] for c in self.campaigns for a in c['adsets']]}]})
        q.atomic(self.eroot/'activation'/(self.rid+'-'+self.account+'.json'),{'phase':'ACTIVATION_PENDING','error':'FIXTURE'})
        q.atomic(self.base/'data/ares/meta-ads/engine-v3/config.json',{'state_root':str(self.eroot),'audit_root':str(self.eroot.parent/'audit'),
                    'accounts':{self.account:{'token_item':'FIXTURE'}}})
        q.atomic(self.base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json',{'profiles':{self.account:{'channel_id':m.CHANNEL}}})
        q.atomic(self.base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json',{'request_defaults':{}})
        self.store=AccountWriterLeaseStore(self.eroot);self.store.claim(self.account,self.rid,status='ACTIVATION_PENDING')
        self.lease=self.store.path(self.account);self.lease_sha=m.sha(self.lease)
        self.alock=q.root(self.base)/'single-clone'/('account-'+self.account+'.lock');self.alock.touch()
        self.job={'request_id':self.new,'request':copy.deepcopy(self.newrequest),'command':'campaign','status':'WAITING','attempts':0,'notification':None,
                  'enqueued_at':'2026-11-09T23:37:17+00:00','maintenance_hold':{'task_id':'t_27706e88'},'dispatch_owner':'foreground','delivery_owner':'ares'}
        self.jp=q.job_path(self.base,self.new);q.atomic(self.jp,self.job)
        self.newsp=q.root(self.base)/'single-clone'/self.new/'state.json'
        q.atomic(self.newsp,{'request':copy.deepcopy(self.newrequest),'phase':'PREPARED','execution_started_at':'ORIGINAL-CLOCK',
                            'manifest':{'sealed':'FIXTURE-45'},'target_manifest':{'sealed':'FIXTURE-45-ACTIVE'},'new_media_assets':[]})
        q.atomic(self.newsp.parent/'manifest-sealed.json',{'sealed':'FIXTURE-45'})
        self.inv=self.base/'data/ares/creative-ops/inventory/assets.jsonl';self.inv.parent.mkdir(parents=True)
        self.inv.write_text(json.dumps({'asset_id':'NEW','canonical_filename':'new.png','checksum':'new-checksum','image_hash':'new-hash'})+'\n')
        self.pins={str(p.relative_to(self.base)):m.sha(p) for p in m.pinned_paths(self.base,self.rid,self.eroot)}
        self.auth=patch.object(q,'authorize_queue_request',return_value={'account_id':self.account});self.auth.start();self.addCleanup(self.auth.stop)
        self.verify=patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':True});self.verify.start();self.addCleanup(self.verify.stop)
        self.get=patch('ares_campaign_v3.shein_channel_authority._get',side_effect=lambda p:copy.deepcopy(self.get_messages[p.rsplit('/',1)[-1]]));self.get.start();self.addCleanup(self.get.stop)
        common=Mock();common.get_token_from_1password.return_value=('FIXTURE-NOT-A-TOKEN','field')
        self.loader=patch.object(driver,'_load_common',return_value=common);self.loader.start();self.addCleanup(self.loader.stop)
        self.capture=patch.object(m,'capture_live',side_effect=lambda *args:copy.deepcopy(self.campaigns));self.capture.start();self.addCleanup(self.capture.stop)
        self.env=patch.dict(os.environ,{'HERMES_PROFILE':'ares'});self.env.start();self.addCleanup(self.env.stop)

    def close(self):return m.reconcile(self.base,self.messages,expected_pins=self.pins,expected_lease_sha256=self.lease_sha)
    def rec(self):return m.read(m.path(self.base,self.rid))
    def seal_record(self,record):q.atomic(m.path(self.base,self.rid),record)
    def selected_request(self):return {**self.newrequest,'campaign_groups':[{'files':['new.png']}]}
    def deps(self):return q.dependencies(self.selected_request(),self.account,self.base)
    def revised(self):
        inp=self.base/'input30.json';q.atomic(inp,{**self.newrequest,'budget_usd':'30'});return inp

    def test_close_is_not_qa_terminal_and_preserves_all_historical_bytes(self):
        originals={p:p.read_bytes() for p in m.pinned_paths(self.base,self.rid,self.eroot)+[self.inv,self.jp]}
        result=self.close();self.assertEqual(result['status'],m.STATUS);self.assertFalse(result['qa_certified'])
        self.assertEqual(originals,{p:p.read_bytes() for p in originals})
        self.assertFalse(q.terminal(self.state));self.assertTrue(dw.pending(self.base,self.rid))
        self.assertEqual(m.read(self.lease)['status'],m.STATUS);self.assertFalse(m.read(self.lease)['blocks_readers'])
        self.assertEqual(self.rec()['campaigns'],self.campaigns)
        self.assertEqual(self.deps(),[])

    def test_close_idempotent_same_receipt_and_lease(self):
        self.close();before=(m.path(self.base,self.rid).read_bytes(),self.lease.read_bytes())
        self.close();self.assertEqual(before,(m.path(self.base,self.rid).read_bytes(),self.lease.read_bytes()))

    def test_missing_approval_rejected_before_lease_change(self):
        before=self.lease.read_bytes()
        with self.assertRaises(ValueError):m.reconcile(self.base,self.messages[:1],expected_pins=self.pins,expected_lease_sha256=self.lease_sha)
        self.assertEqual(before,self.lease.read_bytes());self.assertFalse(m.present(self.base,self.rid))

    def test_wrong_author_content_thread_and_missing_fresh_message_rejected(self):
        for field,value in [('author_id','1055570806945620030'),('content','approve anything'),('channel_id','OTHER')]:
            with self.subTest(field=field):
                messages=copy.deepcopy(self.messages);messages[-1][field]=value
                with self.assertRaises(ValueError):m.verify_messages(messages)
        self.get_messages['1569530861022355457']['author']['id']='OTHER'
        with self.assertRaises(ValueError):self.close()
        self.assertFalse(m.present(self.base,self.rid))

    def test_live_authority_failure_no_transition(self):
        with patch.object(q,'authorize_queue_request',side_effect=ValueError('denied')):
            with self.assertRaises(ValueError):self.close()
        self.assertFalse(m.present(self.base,self.rid))

    def test_wrong_profile_denied(self):
        with patch.dict(os.environ,{'HERMES_PROFILE':'other'}):
            with self.assertRaises(ValueError):self.close()

    def test_cas_changed_pin_no_transition(self):
        q.atomic(self.spath,{**self.state,'external_delta':True})
        with self.assertRaises(ValueError):self.close()
        self.assertFalse(m.present(self.base,self.rid))

    def test_foreign_lease_and_changed_lease_no_transition(self):
        q.atomic(self.lease,{'request_id':'OTHER','account_id':self.account,'status':'IN_PROGRESS','blocks_readers':True})
        with self.assertRaises(ValueError):self.close()
        self.assertFalse(m.present(self.base,self.rid))

    def test_account_dispatch_and_engine_request_locks_block(self):
        from request_serialization import request_lock
        for path in [self.alock,self.jp.with_suffix('.dispatch.lock'),self.jp.with_suffix('.lock')]:
            with self.subTest(path=path):
                with path.open('a+') as h:
                    fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    with self.assertRaises(BlockingIOError):self.close()
        with request_lock(self.eroot/'request-locks',self.rid):
            with self.assertRaises(BlockingIOError):self.close()

    def test_hold_missing_and_wrong_delivery_owner_denied(self):
        for delta in [{'maintenance_hold':None},{'dispatch_owner':'worker'},{'delivery_owner':'OTHER'},{'attempts':1},{'notification':'123'}]:
            q.atomic(self.jp,{**self.job,**delta})
            with self.assertRaises(ValueError):self.close()
        self.assertFalse(m.present(self.base,self.rid))

    def test_crash_between_receipt_and_lease_is_fenced_and_resumable(self):
        with patch.object(AccountWriterLeaseStore,'retire_manual',side_effect=RuntimeError('fixture crash')):
            with self.assertRaises(RuntimeError):self.close()
        self.assertTrue(m.present(self.base,self.rid));self.assertEqual(self.deps(),[self.rid])
        with self.assertRaises(ValueError):self.store.claim(self.account,self.rid)
        self.close();self.assertEqual(self.deps(),[])

    def test_corrupt_receipt_never_replays_and_readers_fail_closed(self):
        self.close();r=self.rec();r['messages']=[];self.seal_record(r)
        with self.assertRaises(ValueError):m.validate(self.base,self.rid)
        self.assertEqual(self.deps(),[self.rid]);self.assertIsNotNone(reader_block_reason(self.account,self.eroot))
        with self.assertRaises(WriterLeaseConflict):self.store.claim(self.account,'newwriter')
        with self.assertRaises(ValueError):m.deny_replay(self.base,self.rid)

    def test_changed_state_checkpoint_manifest_and_activation_keep_dependency(self):
        self.close()
        for p in m.pinned_paths(self.base,self.rid,self.eroot):
            before=p.read_bytes();q.atomic(p,{'modified':'FIXTURE'})
            with self.assertRaises(ValueError):m.validate(self.base,self.rid)
            self.assertEqual(self.deps(),[self.rid]);p.write_bytes(before)

    def test_shared_media_alias_or_reservation_is_not_terminal_transfer(self):
        self.close()
        for delta in [{'image_hash':'old-video-0-0'},{'reservation_request_id':self.rid}]:
            row={'asset_id':'NEW','canonical_filename':'new.png','checksum':'new-checksum','image_hash':'new-hash',**delta}
            self.inv.write_text(json.dumps(row)+'\n');before=self.inv.read_bytes()
            self.assertEqual(self.deps(),[self.rid])
            self.assertEqual(before,self.inv.read_bytes())
        with self.assertRaises(BlockingIOError):q.claim_terminal(self.selected_request(),self.account,self.base)

    def test_other_foreign_writer_after_retirement_still_blocks(self):
        self.close();self.store.claim(self.account,'OTHER-WRITER')
        self.assertEqual(self.deps(),[self.rid])

    def test_reader_idle_and_operation_state_supported_without_qa(self):
        self.close();self.assertIsNone(reader_block_reason(self.account,self.eroot,operation_state=self.spath))
        self.assertEqual(m.read(self.spath)['phase'],'ACTIVATION_PENDING')

    def test_all_campaign_entrypoints_and_lease_reject_retired_request(self):
        self.close();manifest=SimpleNamespace(request_id=self.rid)
        with patch.object(driver,'BASE',self.base),patch.object(q,'BASE',self.base):
            for call in [lambda:driver._run_request_scoped(self.request,confirm_execute=True),
                         lambda:driver._run_bound_request(self.request,confirm_execute=True),
                         lambda:q.gate(self.request,'campaign',self.base),lambda:q.take_foreground(self.request,self.base),
                         lambda:q.notify({'request_id':self.rid},self.state),
                         lambda:self.store.claim(self.account,self.rid),lambda:self.store.mark(self.account,self.rid,'IN_PROGRESS'),
                         lambda:self.store.release(self.account,self.rid),
                         lambda:CampaignEngine.execute.__wrapped__(SimpleNamespace(config={'state_root':str(self.eroot)}),manifest),
                         lambda:activate(SimpleNamespace(config={'state_root':str(self.eroot)}),manifest,None,None)]:
                with self.subTest(call=call):
                    with self.assertRaisesRegex(ValueError,'manual takeover'):call()

    def test_worker_silent_for_retired_even_stale_job(self):
        self.close();job={'request_id':self.rid,'request':self.request,'status':'WAITING','attempts':0}
        q.atomic(q.job_path(self.base,self.rid),job)
        with patch.object(q.subprocess,'run',side_effect=AssertionError('campaign subprocess')),patch.object(q,'notify',side_effect=AssertionError('notice')):
            q.tick(copy.deepcopy(job),self.base)
        self.assertEqual(m.read(q.job_path(self.base,self.rid)),job)

    def test_live_fact_change_is_not_implicitly_accepted(self):
        self.close();self.campaigns[0]['daily_budget']='3000'
        with self.assertRaises(ValueError):m.verify_live(self.base,self.rid,None,None)

    def test_manual_status_never_in_qa_terminals(self):
        self.assertNotIn(m.STATUS,q.TERMINAL)
        self.assertFalse(q.terminal({'phase':m.STATUS,'summary':{'campaigns':[{'campaign_id':'X'}]}}))

    def test_typed_pure_clone_proof_reads_retired_history_without_qa_terminal(self):
        from ares_campaign_v3 import shein_source_media as sm
        from dataclasses import replace
        self.close();self.inv.with_suffix('.jsonl.lock').touch()
        source={'id':'FIXTURE-SOURCE','account_id':self.account,'name':'049 - FIXTURE','status':'ACTIVE'}
        children={'adsets':{'data':[{'id':'NEWSET','account_id':self.account,'campaign_id':source['id'],'status':'ACTIVE'}]},
            'ads':{'data':[{'id':'NEWAD','account_id':self.account,'campaign_id':source['id'],'adset_id':'NEWSET','status':'ACTIVE',
                           'creative':{'id':'NEWCREATIVE','object_story_spec':{'link_data':{'image_hash':'new-hash'}}}}]}}
        def batch(common,token,queries):
            return {'campaigns':{'data':[source]}} if queries[0]['name']=='campaigns' else copy.deepcopy(children)
        request={**self.newrequest,'budget_usd':'30'}
        with patch.object(driver,'_batch',side_effect=batch):
            proof=sm.resolve(request,self.account,self.base)
            self.assertIsInstance(proof,sm.SourceMediaProof)
            self.assertEqual(q.dependencies(request,self.account,self.base),[])
            self.assertIn(self.rid,json.loads(proof.historical_json))
            with self.assertRaises(ValueError):replace(proof,observed_at=proof.observed_at-121).validate(request,self.account,self.base)
            row=json.loads(self.inv.read_text());row['reservation_request_id']=self.rid
            self.inv.write_text(json.dumps(row)+'\n')
            self.assertEqual(q.dependencies(request,self.account,self.base),[self.rid])
            row.pop('reservation_request_id');row['image_hash']='old-video-0-0';self.inv.write_text(json.dumps(row)+'\n')
            children['ads']['data'][0]['creative']['object_story_spec']['link_data']['image_hash']='old-video-0-0'
            self.assertEqual(q.dependencies(request,self.account,self.base),[self.rid])

    def test_media_prepare_and_postprocess_reject_retired_request(self):
        from ares_campaign_v3 import shein_grouped_media as grouped, shein_media_handoff as handoff
        self.close()
        for call in [lambda:grouped.prepare(self.request,base=self.base),lambda:grouped._prepare_locked(self.request,base=self.base),
                     lambda:handoff.finalize_ready_assets(self.state,None,self.base,None,None)]:
            with self.assertRaisesRegex(ValueError,'manual takeover'):call()

    def test_budget_only_amendment_preserves_seals_clock_job_hold(self):
        original=self.newsp.parent.joinpath('manifest-sealed.json').read_bytes()
        result=amend.amend(self.base,self.revised());self.assertEqual(result['budget_usd'],'30')
        s=m.read(self.newsp);j=m.read(self.jp)
        self.assertEqual(s['phase'],'PREPARED');self.assertEqual(s['execution_started_at'],'ORIGINAL-CLOCK')
        self.assertTrue(s['prewrite_amendment_pending']);self.assertEqual(s['request']['budget_usd'],'30')
        self.assertEqual(j['request']['budget_usd'],'30');self.assertEqual(j['maintenance_hold'],self.job['maintenance_hold'])
        self.assertEqual(j['enqueued_at'],self.job['enqueued_at']);self.assertEqual(j['attempts'],0)
        self.assertEqual(original,self.newsp.parent.joinpath('manifest-sealed.json').read_bytes())
        with self.assertRaises(ValueError):amend.require_request(self.base,self.newrequest)
        amend.require_request(self.base,{**self.newrequest,'budget_usd':'30'})
        amend.amend(self.base,self.revised())

    def test_budget_amendment_rejects_schedule_bid_quantity_or_request_delta(self):
        for delta in [{'start_time':'OTHER'},{'bid_usd':'1.2'},{'quantity':99},{'request_id':'OTHER'},{'budget_usd':'29'}]:
            inp=self.revised();q.atomic(inp,{**m.read(inp),**delta})
            with self.assertRaises(ValueError):amend.amend(self.base,inp)
        self.assertEqual(m.read(self.jp)['request']['budget_usd'],'45')

    def test_budget_amendment_rejects_any_core_artifacts_or_writes(self):
        for section in ['checkpoints','activation']:
            p=self.eroot/section/(self.new+'-'+self.account+'.json');q.atomic(p,{'fixture':True})
            with self.assertRaises(ValueError):amend.amend(self.base,self.revised())
            p.unlink()
        s=m.read(self.newsp);s['engine_result']={'campaign_ids':['EXISTING']};q.atomic(self.newsp,s)
        with self.assertRaises(ValueError):amend.amend(self.base,self.revised())

    def test_budget_amendment_rejects_missing_hold_bad_auth_and_lock(self):
        with self.jp.with_suffix('.dispatch.lock').open('a+') as h:
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):amend.amend(self.base,self.revised())
        self.get_messages[amend.AMENDMENT]['content']='not approved'
        with self.assertRaises(ValueError):amend.amend(self.base,self.revised())

    def test_budget_amendment_engine_rejects_historical45_manifest(self):
        amend.amend(self.base,self.revised())
        def mf(budget):return SimpleNamespace(request_id=self.new,campaigns=[SimpleNamespace(account_id=self.account,campaign_updates={'daily_budget':budget},campaign_create={}) for _ in range(4)])
        with self.assertRaises(ValueError):amend.require_manifest(self.eroot,mf(4500))
        amend.require_manifest(self.eroot,mf(3000))

    def test_budget_partial_job_state_write_recovers_same_request(self):
        real=q.atomic
        def fail_job(path,value):
            if path==self.jp:raise RuntimeError('fixture crash')
            return real(path,value)
        with patch.object(q,'atomic',side_effect=fail_job):
            with self.assertRaises(RuntimeError):amend.amend(self.base,self.revised())
        with self.assertRaises(ValueError):amend.require_request(self.base,self.newrequest)
        amend.amend(self.base,self.revised())
        self.assertEqual(m.read(self.jp)['request']['budget_usd'],'30')


if __name__=='__main__':unittest.main()
