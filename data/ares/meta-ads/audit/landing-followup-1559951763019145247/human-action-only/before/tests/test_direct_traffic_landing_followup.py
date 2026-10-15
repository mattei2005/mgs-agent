"""Offline queue/transport regressions. Fixtures are not campaign/PC1 results."""
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import landing_followup as m


class Clock:
    def __init__(self):self.value=1000
    def __call__(self):return self.value


class FakeDiscord:
    bot_id='150000000000000001'
    def __init__(self):self.messages={};self.posts=0;self.lose_post=False;self.fail_get=False;self.channel_parents={}
    def request(self,method,path,body=None):
        self.posts+=1;mid=str(150000000000000010+self.posts)
        thread=path.split('/')[2]
        msg={**(body or {}),'id':mid,'channel_id':thread,'author':{'id':self.bot_id}}
        self.messages[mid]=msg
        if self.lose_post:
            self.lose_post=False;raise ValueError('simulated POST response loss')
        return msg
    def get(self,path):
        if self.fail_get:raise ValueError('simulated GET failure')
        if '/messages' not in path and path.startswith('/channels/'):
            thread=path.split('/')[-1]
            return {'id':thread,'parent_id':self.channel_parents.get(thread,'150000000000000003')}
        if '?limit=' in path:return list(self.messages.values())
        return self.messages[path.split('/')[-1]]
    deliver=m.Discord.deliver


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch',prefix='landing-tests-')
        self.root=Path(self.tmp.name);self.clock=Clock()
        self.bp=patch.object(m,'BASE',self.root);self.bp.start()
        self.sc=patch.object(m,'scope',return_value=True);self.sc.start()
        self.fp=patch.object(m,'file_evidence',side_effect=lambda p:{'path':p,'sha256':'offline-test-only','captured_at':float(Path(p).stem.split('-')[-1]) if Path(p).stem.split('-')[-1].isdigit() else 0});self.fp.start()
        self.pp=patch.object(m,'preserve_evidence',side_effect=lambda e,*a:e);self.pp.start()
        proof=self.root/'data/ares/meta-ads/proof.json';proof.parent.mkdir(parents=True)
        proof.write_text(json.dumps({'offline_test_fixture':True,'request_id':'offline-fixture','account_id':'111111111111111','status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':['111111111111112']}))
        self.payload={'strategy_family':'DIRECT_TRAFFIC','creation_status':'COMPLETE_FUTURE_ACTIVE',
            'account_id':'111111111111111','source_thread_id':'150000000000000002','source_channel_id':'150000000000000003',
            'request_id':'offline-fixture','operation':'TEST-DIRECT','campaign_ids':['111111111111112'],
            'creation_proof':str(proof),'creation_proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),
            'links':[{'campaign_id':'111111111111112',
                'effective_campaign_url':'https://example.invalid/quiz/test/?utm_source=facebook&utm_campaign=b01fb06c126&utm_adgroup=b01fb06c126g01&x=%2F',
                'landing_url':'https://example.invalid/rec-test/?utm_source=facebook&utm_campaign=b01fb06c126&utm_adgroup=b01fb06c126g01&x=%2F',
                'mapping_source':'offline fixture, never an operational mapping','destination_kind':'LANDING_PAGE'}]}
        self.q=m.Queue(self.root/'queue',now=self.clock);self.dc=FakeDiscord()
        self.key=self.q.stage(self.payload,lambda u:True)
    def tearDown(self):
        self.q.db.close();self.pp.stop();self.fp.stop();self.sc.stop();self.bp.stop();self.tmp.cleanup()
    def arm(self):return m.publish_creation(self.q,self.key,'Pedido offline de teste validado.',self.dc)
    def start(self):
        self.arm();self.q.claim('worker');self.q.begin(self.key,'worker',0)
    def closure(self,tab='tab-1'):
        return {'tab_closed_verified':True,'other_tabs_preserved':True,'new_tab_identity':tab,'closed_screenshot':'closed-21.png'}
    def success(self):
        return {**self.closure(),'observed_url':self.payload['links'][0]['landing_url'],
            'network_ad_confirmed':True,'ad_description':'offline test fixture, not real ad',
            'samples':[{'monotonic_seconds':t,'ad_visible':True,'tab_active':True,'screenshot':f'fixture-{t}.png'} for t in [0,5,10]]}
    def test_no_claim_before_reply(self):self.assertIsNone(self.q.claim('worker'))
    def test_idempotent_stage(self):self.assertEqual(self.key,self.q.stage(self.payload,lambda u:True))
    def test_mutated_request_rejected(self):
        p=copy.deepcopy(self.payload);p['request_id']=self.payload['request_id'];p['campaign_ids']=['111111111111113'];p['links'][0]['campaign_id']=p['campaign_ids'][0]
        with self.assertRaises(ValueError):self.q.stage(p,lambda u:True)
    def test_bot_excluded(self):
        p=copy.deepcopy(self.payload);p['strategy_family']='BOT_MESSENGER'
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_future_niche_not_hardcoded(self):
        p=copy.deepcopy(self.payload);p['operation']='FUTURE-NICHE'
        self.assertNotEqual(self.key,self.q.stage(p,lambda u:True))
    def test_quiz_cannot_be_landing(self):
        p=copy.deepcopy(self.payload);p['links'][0]['landing_url']=p['links'][0]['effective_campaign_url']
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_query_bytes_preserved(self):
        p=copy.deepcopy(self.payload);p['links'][0]['landing_url']=p['links'][0]['landing_url'].replace('%2F','/')
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_missing_landing_can_resolve_after_reply(self):
        p=copy.deepcopy(self.payload);p['links'][0].pop('landing_url');m.validate_payload(p,lambda u:True)
    def test_duplicate_utm_rejected(self):
        p=copy.deepcopy(self.payload);p['links'][0]['effective_campaign_url']+='&utm_campaign=b01fb06c126'
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_proof_digest_rejected(self):
        p=copy.deepcopy(self.payload);p['creation_proof_sha256']='bad'
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_coverage_rejected(self):
        p=copy.deepcopy(self.payload);p['campaign_ids'].append('111111111111114')
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)
    def test_reply_before_ready(self):
        self.arm();self.assertEqual(self.q.job(self.key)['state'],'READY');self.assertEqual(self.dc.posts,1)
    def test_old_arbitrary_reply_cannot_arm(self):
        with self.assertRaises(ValueError):self.q.acknowledge(self.key,{'id':'150000000000000010','channel_id':self.payload['source_thread_id'],'author':{'id':self.dc.bot_id},'content':'old'},self.dc.bot_id)
    def test_wrong_thread_rejected(self):
        with self.assertRaises(ValueError):self.q.acknowledge(self.key,{'id':'150000000000000010','channel_id':'150000000000000004','author':{'id':self.dc.bot_id},'content':'x'},self.dc.bot_id)
    def test_global_single_worker(self):
        self.arm();self.assertIsNotNone(self.q.claim('worker'));self.assertIsNone(self.q.claim('other'))
    def test_wrong_worker_cannot_open(self):
        self.arm();self.q.claim('worker')
        with self.assertRaises(ValueError):self.q.begin(self.key,'other',0)
    def test_ambiguous_open_never_replayed(self):
        self.start()
        with self.assertRaises(ValueError):self.q.begin(self.key,'worker',0)
        with self.assertRaises(ValueError):self.q.deferred(self.key,'worker')
    def test_first_no_ad_silent_sixty_second_gate(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure())
        self.assertEqual(self.q.db.execute('SELECT count(*) FROM messages').fetchone()[0],1)
        self.clock.value+=59;self.assertIsNone(self.q.claim('worker'))
        self.clock.value+=1;self.assertIsNotNone(self.q.claim('worker'))
    def test_second_no_ad_only_incident_thread(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.q.result(self.key,'worker',0,'NO_AD',self.closure('tab-2'))
        r=self.q.db.execute("SELECT * FROM messages WHERE key LIKE '%incident%'").fetchone()
        self.assertEqual(r['thread'],m.INCIDENT_THREAD);self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE content=?",(m.SUCCESS,)).fetchone())
    def test_retry_requires_new_tab(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0)
        with self.assertRaises(ValueError):self.q.result(self.key,'worker',0,'NO_AD',self.closure())
    def test_success_exact_message_no_pc1_or_gam_claim(self):
        self.start();self.q.result(self.key,'worker',0,'PASS',self.success())
        r=self.q.db.execute('SELECT * FROM messages WHERE key=?',(self.key+':success',)).fetchone()
        self.assertEqual(r['thread'],self.payload['source_thread_id']);self.assertEqual(r['content'],m.SUCCESS)
        self.assertNotIn('PC1',r['content']);self.assertNotIn('GAM',r['content'])
    def test_empty_slot_not_success(self):
        self.start();e=self.success();e['network_ad_confirmed']=False
        with self.assertRaises(ValueError):self.q.result(self.key,'worker',0,'PASS',e)
    def test_ten_seconds_required(self):
        e=self.success();e['samples'][-1]['monotonic_seconds']=9
        with self.assertRaises(ValueError):m.validate_observation(e,self.payload['links'][0])
    def test_inactive_tab_fails(self):
        e=self.success();e['samples'][1]['tab_active']=False
        with self.assertRaises(ValueError):m.validate_observation(e,self.payload['links'][0])
    def test_reused_screenshot_fails(self):
        e=self.success();e['samples'][1]['screenshot']=e['samples'][0]['screenshot']
        with self.assertRaises(ValueError):m.validate_observation(e,self.payload['links'][0])
    def test_wrong_url_fails(self):
        e=self.success();e['observed_url']='https://example.invalid/wrong'
        with self.assertRaises(ValueError):m.validate_observation(e,self.payload['links'][0])
    def test_unclosed_tab_fails(self):
        e=self.success();e['tab_closed_verified']=False
        with self.assertRaises(ValueError):m.validate_observation(e,self.payload['links'][0])
    def test_worker_expiry_does_not_reopen(self):
        self.start();self.clock.value+=601;self.q.recover_expired()
        self.assertEqual(self.q.job(self.key)['state'],'NEEDS_RECONCILIATION');self.assertIsNone(self.q.claim('new-worker'))
        r=self.q.db.execute("SELECT * FROM messages WHERE key LIKE '%expired'").fetchone();self.assertEqual(r['thread'],m.INCIDENT_THREAD)
    def test_no_success_before_all_links(self):
        p=copy.deepcopy(self.payload);p['operation']='MULTI-DIRECT';p['links'].append(copy.deepcopy(p['links'][0]))
        p['links'][1]['effective_campaign_url']=p['links'][1]['effective_campaign_url'].replace('g01','g02')
        p['links'][1]['landing_url']=p['links'][1]['landing_url'].replace('g01','g02')
        key=self.q.stage(p,lambda u:True);m.publish_creation(self.q,key,'multi completed',self.dc)
        self.q.claim('worker');self.q.begin(key,'worker',0);self.q.result(key,'worker',0,'PASS',self.success())
        self.assertEqual(self.q.job(key)['state'],'READY');self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE key=?',(key+':success',)).fetchone())
    def test_ambiguous_post_readback_nonce_no_duplicate(self):
        self.dc.lose_post=True
        with self.assertRaises(ValueError):self.arm()
        self.assertEqual(self.q.job(self.key)['state'],'WAITING_CREATION_REPLY')
        self.arm();self.assertEqual(self.dc.posts,1);self.assertEqual(self.q.job(self.key)['state'],'READY')
    def test_verified_post_replay_is_read_only(self):
        self.arm();self.arm();self.assertEqual(self.dc.posts,1)
    def test_cancelled_unsent_alert_is_never_posted(self):
        self.arm()
        with self.q.tx():
            self.q.prepare_message('cancelled-alert',m.INCIDENT_THREAD,'offline obsolete alert')
            self.q.db.execute("UPDATE messages SET state='CANCELLED_BEFORE_SEND' WHERE key='cancelled-alert'")
        with self.assertRaises(ValueError):self.dc.deliver(self.q,'cancelled-alert')
        self.assertEqual(self.dc.posts,1)
    def test_pending_message_id_survives_failed_get(self):
        original_get=self.dc.get
        def fail_message_readback(path):
            if '/messages/' in path:raise ValueError('simulated message GET failure')
            return original_get(path)
        with patch.object(self.dc,'get',side_effect=fail_message_readback):
            with self.assertRaises(ValueError):self.arm()
        row=self.q.db.execute('SELECT * FROM messages').fetchone();self.assertTrue(row['message_id'])
        self.arm();self.assertEqual(self.dc.posts,1)

    def test_first_retry_blocks_later_url_of_same_request(self):
        p=copy.deepcopy(self.payload);p['operation']='MULTI-DIRECT';p['links'].append(copy.deepcopy(p['links'][0]))
        for f in ['effective_campaign_url','landing_url']:p['links'][1][f]=p['links'][1][f].replace('g01','g02')
        key=self.q.stage(p,lambda u:True);m.publish_creation(self.q,key,'multi',self.dc)
        self.q.claim('worker');self.q.begin(key,'worker',0);self.q.result(key,'worker',0,'NO_AD',self.closure())
        self.clock.value+=30;self.assertIsNone(self.q.claim('worker'))

    def test_durable_queue_survives_connection_reopen(self):
        self.arm();self.q.db.close();self.q=m.Queue(self.root/'queue',now=self.clock)
        self.assertEqual(self.q.claim('worker')['key'],self.key)

    def test_unclosed_error_blocks_all_observers(self):
        self.start();self.q.result(self.key,'worker',0,'ERROR',{'diagnosis':'offline simulated uncertain closure'})
        self.assertEqual(self.q.job(self.key)['state'],'NEEDS_RECONCILIATION')
        self.assertIsNone(self.q.claim('other'))

    def test_preopen_mapping_error_does_not_claim_observation_success(self):
        self.start();self.q.result(self.key,'worker',0,'ERROR',{'diagnosis':'offline missing mapping','no_tab_opened':True})
        self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')

    def test_manifest_adapter_preserves_query_bytes_and_tag_precedence(self):
        from ares_campaign_v3.landing_followup_adapters import effective_url
        got=effective_url('https://example.invalid/quiz/?x=%2F&utm_campaign=old&utm_campaign=old2','utm_campaign=b01fb06c126&utm_adgroup=b01fb06c126g01')
        self.assertEqual(got,'https://example.invalid/quiz/?x=%2F&utm_campaign=b01fb06c126&utm_adgroup=b01fb06c126g01')

    def test_proof_must_be_same_terminal_request(self):
        p=copy.deepcopy(self.payload);p['request_id']='wrong-request'
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)

    def test_unresolved_macros_are_not_opened(self):
        p=copy.deepcopy(self.payload);p['links'][0]['effective_campaign_url']+='&ad={{ad.id}}'
        with self.assertRaises(ValueError):m.validate_payload(p,lambda u:True)

    def test_cpv_daily_has_no_followup_dependency(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/ares_campaign_v3/daily_cpv.py').read_text()
        self.assertNotIn('landing_followup',source)
        self.assertIn('audit["discord_readback"] = post_discord(',source)

    def test_dispatcher_integration_arms_after_reply_and_finalizes_outbox(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('landing_cli_test',path)
        assert spec is not None and spec.loader is not None
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        self.arm()
        def fake_run(command,**kw):
            if command[-1]=='status':return SimpleNamespace(returncode=0,stdout='{"locked":false}')
            j=self.q.job(self.key);owner=j['owner']
            self.q.begin(self.key,owner,0);self.q.result(self.key,owner,0,'PASS',self.success())
            return SimpleNamespace(returncode=0)
        with patch.object(cli,'BASE',Path(__file__).resolve().parents[1]),patch.object(cli,'native_busy',return_value=False),patch.object(cli.subprocess,'run',side_effect=fake_run),patch.object(cli,'Discord',return_value=self.dc):
            result=cli.tick(self.q)
        self.assertEqual(result['state'],'COMPLETE');self.assertEqual(self.dc.posts,2)
        kinds=[x['kind'] for x in self.q.db.execute('SELECT kind FROM events ORDER BY seq')]
        self.assertLess(kinds.index('creation_reply_verified'),kinds.index('open_intent'))

    def test_reconciliation_never_promotes_uncertain_view_to_success(self):
        self.start();self.clock.value+=601;self.q.recover_expired()
        self.q.reconcile(self.key,0,self.closure('reconciled-tab'))
        self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'ATTENTION')
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE key=?',(self.key+':success',)).fetchone())

    def test_reconciliation_requires_real_closure_proof(self):
        self.start();self.clock.value+=601;self.q.recover_expired()
        with self.assertRaises(ValueError):self.q.reconcile(self.key,0,{'tab_closed_verified':False})

    def second_account(self):
        p=copy.deepcopy(self.payload)
        p.update(account_id='111111111111115',source_thread_id='150000000000000006',source_channel_id='150000000000000007',request_id='second-manager-fixture',campaign_ids=['111111111111116'])
        p['links'][0]['campaign_id']='111111111111116'
        for field in ('landing_url','effective_campaign_url'):p['links'][0][field]=p['links'][0][field].replace('c126','c127')
        proof=Path(p['creation_proof']).with_name('second-manager-proof.json')
        proof.write_text(json.dumps({'offline_test_fixture':True,'request_id':p['request_id'],'account_id':p['account_id'],'status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':p['campaign_ids']}))
        p.update(creation_proof=str(proof),creation_proof_sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
        self.dc.channel_parents[p['source_thread_id']]=p['source_channel_id']
        key=self.q.stage(p,lambda u:True);m.publish_creation(self.q,key,'Segundo gestor concluído (fixture offline).',self.dc)
        return key

    def test_simultaneous_two_accounts_only_one_global_claim(self):
        import threading
        self.arm();self.clock.value+=1;self.second_account()
        barrier=threading.Barrier(2)
        def claim(owner):
            q=m.Queue(self.root/'queue',now=self.clock)
            try:
                barrier.wait(timeout=5);row=q.claim(owner)
                return row['key'] if row else None
            finally:q.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(claim,['manager-001-worker','manager-006-worker']))
        self.assertEqual([x for x in results if x],[self.key])

    def test_second_manager_waits_through_first_manager_retry(self):
        self.arm();self.clock.value+=1;other=self.second_account()
        self.assertEqual(self.q.claim('first')['key'],self.key)
        self.q.begin(self.key,'first',0);self.q.result(self.key,'first',0,'NO_AD',self.closure())
        self.assertIsNone(self.q.claim('second'))
        self.clock.value+=60;self.assertEqual(self.q.claim('first')['key'],self.key)
        self.q.begin(self.key,'first',0);self.q.result(self.key,'first',0,'NO_AD',self.closure('retry-tab-new'))
        self.assertEqual(self.q.claim('second')['key'],other)


if __name__=='__main__':unittest.main()
