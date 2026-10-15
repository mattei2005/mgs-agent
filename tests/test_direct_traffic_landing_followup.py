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
    def test_second_no_ad_stays_local_without_human_action(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.q.result(self.key,'worker',0,'NO_AD',self.closure('tab-2'))
        r=self.q.db.execute("SELECT * FROM messages WHERE key LIKE '%incident%'").fetchone()
        self.assertIsNone(r);self.assertEqual(self.q.job(self.key)['state'],'ATTENTION')
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
        r=self.q.db.execute("SELECT * FROM messages WHERE key LIKE '%expired'").fetchone();self.assertIsNone(r)

    def test_recoverable_error_silent(self):
        self.start();self.q.result(self.key,'worker',0,'ERROR',{**self.closure(),'diagnosis':'Offline fixture: cadence gap, agent recovery only'})
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE key LIKE '%incident%'").fetchone())
        self.assertTrue(self.q.db.execute("SELECT 1 FROM events WHERE kind='recoverable_retry_scheduled'").fetchone())
        self.assertEqual(self.q.job(self.key)['state'],'READY')

    def test_human_action_flag_without_exact_action_is_silent(self):
        self.start();self.q.result(self.key,'worker',0,'ERROR',{**self.closure(),'diagnosis':'offline fixture','human_action_required':True})
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE key LIKE '%incident%'").fetchone())

    def test_legacy_queued_problem_never_posts_without_human_gate(self):
        self.arm()
        with self.q.tx():self.q.prepare_message('legacy-intake-alert',m.INCIDENT_THREAD,'Offline fixture technical error')
        with self.assertRaisesRegex(ValueError,'kept_local'):self.dc.deliver(self.q,'legacy-intake-alert')
        self.assertEqual(self.dc.posts,1)
        self.assertEqual(self.q.db.execute("SELECT state FROM messages WHERE key='legacy-intake-alert'").fetchone()[0],'CANCELLED_BEFORE_SEND')

    def test_explicit_human_action_only_problem_destination(self):
        self.start();self.q.result(self.key,'worker',0,'ERROR',{**self.closure(),'diagnosis':'offline fixture: interaction unavailable','human_action_required':True,'required_action':'Offline fixture: restore the authorized interactive login.'})
        r=self.q.db.execute("SELECT * FROM messages WHERE key LIKE '%incident%'").fetchone()
        self.assertEqual(r['thread'],m.INCIDENT_THREAD)
        self.assertIn('Ação necessária de Rodolfo:',r['content'])
        self.dc.deliver(self.q,r['key']);self.assertEqual(self.dc.posts,2)
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
        self.assertEqual(self.q.job(self.key)['state'],'READY')

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

    def test_expired_worker_is_claimed_for_recovery_without_navigation(self):
        self.start();self.clock.value+=601;self.q.recover_expired()
        self.assertIsNone(self.q.claim_recovery('repair'))
        self.clock.value+=60;j=self.q.claim_recovery('repair')
        self.assertEqual(j['state'],'RECONCILING');self.assertEqual(j['links'][0]['state'],'OPEN_INTENT')
        self.assertIsNone(self.q.claim('other'));self.assertIsNone(self.q.claim_recovery('other'))

    def test_valid_last_attempt_proof_can_recover_without_new_visit(self):
        self.clock.value=0;self.start();self.clock.value=601;self.q.recover_expired();self.clock.value+=60
        self.q.claim_recovery('repair');e=self.success()
        with self.assertRaises(ValueError):self.q.result(self.key,'repair',0,'PASS',e)
        self.q.result(self.key,'repair',0,'PASS',e,recovered=True)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'PASSED')
        self.assertEqual(self.q.db.execute("SELECT count(*) FROM events WHERE kind='open_intent'").fetchone()[0],1)

    def test_old_attempt_proof_cannot_recover_newer_open(self):
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60;self.q.claim_recovery('repair')
        with self.assertRaisesRegex(ValueError,'latest actual open'):self.q.result(self.key,'repair',0,'PASS',self.success(),recovered=True)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'OPEN_INTENT')

    def test_recovered_flag_cannot_promote_error_to_success(self):
        self.start()
        with self.assertRaises(ValueError):self.q.result(self.key,'worker',0,'ERROR',{'diagnosis':'offline'},recovered=True)

    def test_real_absence_proof_can_be_recorded_after_worker_timeout(self):
        self.clock.value=0;self.start();self.clock.value=601;self.q.recover_expired();self.clock.value+=60;self.q.claim_recovery('repair')
        e={**self.closure(),'network_ad_confirmed':False,'visual_review':'Offline reviewed absence fixture, not real browser result','observation_screenshot':'fixture-7.png'}
        self.q.result(self.key,'repair',0,'NO_AD',e,recovered=True)
        self.assertEqual(self.q.no_ad_count(self.key,0),1)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'WAIT_RETRY')

    def test_recovery_safe_resume_is_not_success(self):
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60
        self.q.claim_recovery('repair');self.q.reconcile(self.key,0,self.closure('old-owned-tab'),resume=True)
        j=self.q.job(self.key);self.assertEqual(j['state'],'READY');self.assertEqual(j['links'][0]['state'],'WAIT_RETRY')
        self.assertIsNone(self.q.claim('next'));self.clock.value+=60
        self.q.claim('next');self.q.begin(self.key,'next',0)
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE key=?',(self.key+':success',)).fetchone())

    def test_recovery_can_defer_without_abandoning(self):
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60;self.q.claim_recovery('repair')
        with self.assertRaises(ValueError):self.q.deferred(self.key,'wrong')
        self.q.deferred(self.key,'repair');self.assertEqual(self.q.job(self.key)['state'],'NEEDS_RECONCILIATION')
        self.assertIsNone(self.q.claim_recovery('again'));self.clock.value+=60
        self.assertIsNotNone(self.q.claim_recovery('again'))

    def test_technical_errors_do_not_consume_no_ad_limit(self):
        self.start()
        for n in range(3):
            self.q.result(self.key,'worker',0,'ERROR',{**self.closure('technical-'+str(n)),'diagnosis':'offline cadence fixture'})
            self.clock.value+=60;self.q.claim('worker');self.q.begin(self.key,'worker',0)
        self.assertEqual(self.q.no_ad_count(self.key,0),0)
        self.assertEqual(self.q.job(self.key)['links'][0]['attempt'],4)

    def test_two_confirmed_no_ads_cannot_be_reopened_by_recovery(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'NO_AD',self.closure('tab-2'))
        self.assertEqual(self.q.no_ad_count(self.key,0),2)
        self.q.claim_recovery('repair')
        self.q.reconcile(self.key,0,self.closure('tab-2'),resume=True)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'ATTENTION')
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE key=?',(self.key+':success',)).fetchone())

    def test_reconciled_absence_history_counts_once_per_real_attempt(self):
        self.start()
        with self.q.tx():
            for kind in ['reconciled_no_ad','observation_result']:
                self.q.event(self.key,kind,{'idx':0,'attempt':1,'result':'NO_AD'})
            self.q.event(self.key,'reconciled_no_ad',{'idx':0,'attempt':2,'result':'NO_AD'})
        self.assertEqual(self.q.no_ad_count(self.key,0),2)

    def test_no_tab_recovery_requires_zero_input_readback(self):
        self.start();self.clock.value+=601;self.q.recover_expired()
        with self.assertRaises(ValueError):self.q.reconcile(self.key,0,{'no_tab_opened':True,'diagnosis':'offline'},resume=True)
        self.q.reconcile(self.key,0,{'no_tab_opened':True,'browser_inputs_zero_verified':True,'diagnosis':'offline verified no inputs'},resume=True)
        self.assertEqual(self.q.job(self.key)['state'],'READY')

    def test_human_needed_after_safe_cleanup_does_not_repeat_worker(self):
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60;self.q.claim_recovery('repair')
        e={**self.closure(),'human_action_required':True,'required_action':'Offline fixture: restore human login','diagnosis':'offline authentication gate'}
        self.q.request_human(self.key,'repair',e)
        self.assertEqual(self.q.job(self.key)['state'],'WAITING_HUMAN');self.assertIsNone(self.q.claim_recovery('another'))

    def test_invalid_human_action_cannot_orphan_work_in_human_state(self):
        self.start()
        for action in ['   ',123,None]:
            with self.assertRaises(ValueError):self.q.request_human(self.key,'worker',{'human_action_required':True,'required_action':action,'diagnosis':'offline fixture'})
            self.assertEqual(self.q.job(self.key)['state'],'RUNNING')

    def test_uncertain_human_gate_blocks_all_new_inputs(self):
        self.start()
        e={'human_action_required':True,'required_action':'Offline fixture: unlock desktop','diagnosis':'offline screen locked'}
        self.q.request_human(self.key,'worker',e)
        self.assertEqual(self.q.job(self.key)['state'],'WAITING_HUMAN_UNCLOSED')
        self.assertIsNone(self.q.claim('another'));self.assertIsNone(self.q.claim_recovery('another'))

    def test_dispatcher_repairs_nonready_job_instead_of_idle(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('landing_recovery_cli_test',path)
        assert spec is not None and spec.loader is not None
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60
        def fake_run(command,**kw):
            if command[-1]=='status':return SimpleNamespace(returncode=0,stdout='{"locked":false}')
            j=self.q.job(self.key);self.assertEqual(j['state'],'RECONCILING')
            self.q.reconcile(self.key,0,self.closure('closed-by-repair'),resume=True)
            return SimpleNamespace(returncode=0)
        with patch.object(cli,'BASE',Path(__file__).resolve().parents[1]),patch.object(cli,'native_busy',return_value=False),patch.object(cli.subprocess,'run',side_effect=fake_run),patch.object(cli,'Discord',return_value=self.dc):
            result=cli.tick(self.q)
        self.assertEqual(result['state'],'READY');self.assertEqual(self.dc.posts,1)

    def test_orphan_releaser_never_touches_live_or_other_agent_lease(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('orphan_guard_test',path)
        assert spec and spec.loader
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        with patch.object(cli,'observer_process_alive',return_value=True),patch.object(cli.subprocess,'run') as run:
            self.assertFalse(cli.orphan_observer_lease(self.q,{'locked':True,'agent':'ares','session_id':'live-fixture'}));run.assert_not_called()
        with patch.object(cli,'observer_process_alive',return_value=False),patch.object(cli.subprocess,'run') as run:
            self.assertFalse(cli.orphan_observer_lease(self.q,{'locked':True,'agent':'zeus','session_id':'other-agent-fixture'}));run.assert_not_called()

    def test_skill_routes_are_dedicated_not_campaign_skill(self):
        self.arm();j=self.q.claim('worker')
        prompt=m.worker_prompt(self.key,'worker',0,j)
        self.assertIn('landing-followup-operations',prompt)
        self.assertNotIn('Carregue direct-traffic-cbo-operations',prompt)
        j['state']='RECONCILING';prompt=m.worker_prompt(self.key,'repair',0,j)
        self.assertIn('landing-followup-operations',prompt);self.assertIn('Não abrir URL',prompt)

    def test_single_native_reply_waits_for_all_technical_jobs(self):
        self.arm();self.clock.value+=1
        p=copy.deepcopy(self.payload);p['request_id']='offline-subjob-two';p['campaign_ids']=['111111111111119'];p['links'][0]['campaign_id']=p['campaign_ids'][0]
        for field in ['landing_url','effective_campaign_url']:p['links'][0][field]=p['links'][0][field].replace('c126','c127')
        proof=self.root/'data/ares/meta-ads/subjob-proof.json';proof.write_text(json.dumps({'request_id':p['request_id'],'account_id':p['account_id'],'status':'COMPLETE','campaign_ids':p['campaign_ids']}))
        p['creation_proof']=str(proof);p['creation_proof_sha256']=hashlib.sha256(proof.read_bytes()).hexdigest()
        other=self.q.stage(p,lambda u:True);m.publish_creation(self.q,other,'Second technical job offline fixture',self.dc)
        receipt=json.dumps({'native_obligation_id':'offline-human-reply'})
        with self.q.tx():
            for key in [self.key,other]:self.q.db.execute('INSERT INTO native_receipts VALUES(?,?)',(key,receipt))
            self.q.db.execute('INSERT INTO native_intake VALUES(?,?,?,?,?)',('native:offline-human-reply',self.clock(),'READY',None,None))
        self.q.claim('w');self.q.begin(self.key,'w',0);self.q.result(self.key,'w',0,'PASS',self.success())
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE content=?',(m.SUCCESS,)).fetchone())
        self.q.claim('w');self.q.begin(other,'w',0);e=self.success();e['observed_url']=p['links'][0]['landing_url'];self.q.result(other,'w',0,'PASS',e)
        self.assertEqual(self.q.db.execute('SELECT count(*) FROM messages WHERE content=?',(m.SUCCESS,)).fetchone()[0],1)
        self.assertEqual(self.q.success_key(self.key),self.q.success_key(other))

    def test_native_intake_must_finish_enumeration_before_success(self):
        self.start()
        with self.q.tx():
            self.q.db.execute('INSERT INTO native_receipts VALUES(?,?)',(self.key,json.dumps({'native_obligation_id':'offline-not-enumerated'})))
            self.q.db.execute('INSERT INTO native_intake VALUES(?,?,?,?,?)',('native:offline-not-enumerated',self.clock(),'PENDING',None,None))
        self.q.result(self.key,'worker',0,'PASS',self.success())
        self.assertIsNone(self.q.db.execute('SELECT 1 FROM messages WHERE content=?',(m.SUCCESS,)).fetchone())
        with self.q.tx():
            self.q.db.execute("UPDATE native_intake SET state='READY' WHERE id='native:offline-not-enumerated'")
            self.assertTrue(self.q.prepare_success_if_complete(self.key))

    def test_compact_result_merges_only_explicitly_reviewed_frames(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('compact_result_cli_test',path);assert spec and spec.loader
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        self.start();e=self.success();samples=e.pop('samples')
        f=self.q.root/'runs/worker/capture-series.json';f.parent.mkdir(parents=True);f.write_text(json.dumps({'state':'CAPTURED_NOT_PASS','samples':samples}))
        args=['tool','result','--key',self.key,'--owner','worker','--index','0','--pc1-session-id','offline-fixture','--result','PASS','--evidence-json',json.dumps(e),'--use-captured-samples']
        with patch.object(sys,'argv',args),patch.object(cli,'Queue',return_value=self.q),patch.object(cli,'require_pc1_lease'):
            with self.assertRaises(ValueError):cli.main()
        self.assertEqual(self.q.job(self.key)['state'],'RUNNING')
        with patch.object(sys,'argv',args+['--frames-reviewed']),patch.object(cli,'Queue',return_value=self.q),patch.object(cli,'require_pc1_lease'):
            self.assertEqual(cli.main()['state'],'OBSERVED')

    def test_prompt_omits_unrelated_large_evidence(self):
        self.arm();j=self.q.claim('worker')
        j['links'][0]['evidence']=json.dumps({'new_tab_identity':'offline-previous-tab','samples':[{'screenshot':'HUGE_UNRELATED_OFFLINE_DETAIL'}]})
        prompt=m.worker_prompt(self.key,'worker',0,j)
        self.assertNotIn('HUGE_UNRELATED_OFFLINE_DETAIL',prompt)
        self.assertIn('offline-previous-tab',prompt)

    def test_recovery_freezes_only_matching_real_attempt_metadata(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('frozen_recovery_test',path);assert spec and spec.loader
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        self.clock.value=0;self.start();e={**self.closure(),'network_ad_confirmed':False,'visual_review':'Offline fixture review','observed_url':self.payload['links'][0]['landing_url'],'observation_screenshot':'fixture-7.png'}
        with self.q.tx():self.q.event(self.key,'reconciled_no_ad',{'idx':0,'attempt':1,'result':'NO_AD','evidence':e})
        d=self.root/'frozen';d.mkdir();j=self.q.job(self.key)
        self.assertTrue(cli.prepare_recovery_proof(self.q,j,0,d))
        self.assertTrue(Path(j['recovery_evidence_path']).is_file())
        self.assertEqual(j['confirmed_no_ads'],1)
        self.assertEqual(self.q.job(self.key)['links'][0]['state'],'OPEN_INTENT')

    def test_recovery_does_not_freeze_previous_attempt_as_current(self):
        path=Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py'
        spec=importlib.util.spec_from_file_location('wrong_frozen_recovery_test',path);assert spec and spec.loader
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        self.clock.value=0;self.start();e={**self.closure(),'network_ad_confirmed':False,'visual_review':'Offline fixture review','observed_url':self.payload['links'][0]['landing_url'],'observation_screenshot':'fixture-7.png'}
        with self.q.tx():self.q.event(self.key,'reconciled_no_ad',{'idx':0,'attempt':1,'result':'NO_AD','evidence':e})
        j=self.q.job(self.key);j['links'][0]['attempt']=2;d=self.root/'wrong-frozen';d.mkdir()
        self.assertFalse(cli.prepare_recovery_proof(self.q,j,0,d));self.assertNotIn('recovery_evidence_path',j)

    def priority_fixture(self,peers):
        cfg={'current_priority':{'mode':'OTHER_CURRENT_WORK_BEFORE_C121','target_job':self.key,'target_index':0,'cohort_jobs':peers},
             'progress_reporting':{'enabled':True,'generation':'150000000000000088','authority_message_id':'150000000000000088','thread_id':m.INCIDENT_THREAD,'interval_seconds':900,'report_jobs':[self.key]+peers,'stop_when_scope_complete':True}}
        p=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(cfg))
        return cfg

    def test_c121_closed_attention_waits_for_other_frozen_jobs(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'NO_AD',self.closure('tab-2'))
        peer=self.second_account();self.priority_fixture([peer])
        self.assertTrue(self.q.target_waits_for_others(self.key));self.assertIsNone(self.q.claim_recovery('repair'))
        self.assertEqual(self.q.claim('other')['key'],peer)

    def test_c121_returns_after_peer_urls_observed_not_blocked_by_its_notice(self):
        self.start();self.q.result(self.key,'worker',0,'NO_AD',self.closure());self.clock.value+=60
        self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'NO_AD',self.closure('tab-2'))
        peer=self.second_account();self.priority_fixture([peer])
        with self.q.tx():self.q.db.execute("UPDATE jobs SET state='OBSERVED' WHERE key=?",(peer,))
        self.assertFalse(self.q.target_waits_for_others(self.key));self.assertEqual(self.q.claim_recovery('repair')['key'],self.key)

    def test_priority_never_skips_uncertain_closure(self):
        self.start();self.clock.value+=601;self.q.recover_expired();self.clock.value+=60
        peer=self.second_account();self.priority_fixture([peer])
        self.assertEqual(self.q.claim_recovery('cleanup')['key'],self.key)

    def test_safe_c121_intervention_note_waits_until_other_jobs(self):
        self.start();peer=self.second_account();self.priority_fixture([peer])
        e={**self.closure(),'human_action_required':True,'required_action':'Offline fixture: inspect publisher setting','diagnosis':'offline serving investigation'}
        self.q.request_human(self.key,'worker',e)
        self.assertEqual(self.q.job(self.key)['state'],'ATTENTION');self.assertEqual(self.q.job(self.key)['links'][0]['state'],'ATTENTION')
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM messages WHERE key=?",(self.key+':human-action',)).fetchone())

    def test_explicit_progress_reports_have_interval_readback_and_stop(self):
        from ares_campaign_v3 import landing_followup_reporting as reports
        self.arm();cfg=self.priority_fixture([])['progress_reporting']
        first=reports.cycle(self.q,lambda:self.dc,cfg);self.assertEqual(first['state'],'VERIFIED');self.assertEqual(self.dc.posts,2)
        self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'NOT_DUE');self.clock.value+=899
        self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'NOT_DUE');self.clock.value+=1
        self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'VERIFIED');self.assertEqual(self.dc.posts,3)
        with self.q.tx():
            self.q.db.execute("UPDATE jobs SET state='COMPLETE' WHERE key=?",(self.key,));self.q.db.execute("UPDATE links SET state='PASSED' WHERE job=?",(self.key,))
        self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'VERIFIED');self.assertEqual(self.dc.posts,4)
        self.clock.value+=9000;self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'NOT_DUE');self.assertEqual(self.dc.posts,4)

    def test_progress_reports_do_not_enable_technical_error_alerts(self):
        from ares_campaign_v3 import landing_followup_reporting as reports
        self.arm();cfg=self.priority_fixture([])['progress_reporting'];cfg['enabled']=False
        self.assertEqual(reports.cycle(self.q,lambda:self.dc,cfg)['state'],'DISABLED');self.assertEqual(self.dc.posts,1)
        with self.q.tx():self.q.prepare_message('still-forbidden-technical-alert',m.INCIDENT_THREAD,'Offline generic technical error')
        with self.assertRaises(ValueError):self.dc.deliver(self.q,'still-forbidden-technical-alert')
        self.assertEqual(self.dc.posts,1)

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
