"""Independent intake tests. All campaigns/Discord data below are offline fixtures."""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_intake as li


class FakeDiscord:
    bot_id='150000000000000001'
    thread='150000000000000002'
    parent='150000000000000003'
    def __init__(self,content):
        self.messages=[{'id':'150000000000000020','channel_id':self.thread,'content':content,'author':{'id':self.bot_id}}]
        self.gets=[];self.posts=0
    def get(self,path):
        self.gets.append(path)
        if '/messages?' in path:return self.messages
        if '/messages/' in path:return next(m for m in self.messages if m['id']==path.split('/')[-1])
        return {'id':self.thread,'parent_id':self.parent}


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch',prefix='independent-intake-tests-')
        self.base=Path(self.tmp.name);self.meta=self.base/'data/ares/meta-ads';self.meta.mkdir(parents=True)
        self.bp=patch.object(core,'BASE',self.base);self.bp.start()
        self.policy=self.meta/'policies/direct-traffic-landing-followup.json';self.policy.parent.mkdir()
        self.policy.write_text(json.dumps({'all_problem_destination_thread':'1559932317861158993'}))
        self.pp=patch.object(li,'POLICY',self.policy);self.pp.start()
        self.path=self.base/'native.db';self.c=sqlite3.connect(self.path)
        self.c.executescript('''
        CREATE TABLE sessions(id TEXT,source TEXT,session_key TEXT,thread_id TEXT,chat_id TEXT,origin_json TEXT,started_at REAL);
        CREATE TABLE messages(id INTEGER PRIMARY KEY,session_id TEXT,role TEXT,content TEXT,tool_calls TEXT,finish_reason TEXT,timestamp REAL,platform_message_id TEXT);
        CREATE TABLE delivery_obligations(obligation_id TEXT PRIMARY KEY,session_key TEXT,platform TEXT,chat_id TEXT,thread_id TEXT,content TEXT,state TEXT,created_at REAL,updated_at REAL);
        CREATE TABLE session_turn_leases(conversation_id TEXT,expires_at REAL);
        ''')
        self.thread=FakeDiscord.thread;self.parent=FakeDiscord.parent;self.text='Criada C127. Pedido concluído e validado. (fixture offline)'
        self.rid='offline-native-request';self.cid='111111111111112';self.aid='111111111111111'
        self.c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?)',('session-1','discord','native-key',self.thread,self.thread,json.dumps({'parent_chat_id':self.parent}),900))
        self.c.executemany('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)',[
            (1,'session-1','user','Pedido offline',None,None,1000,'150000000000000010'),
            (2,'session-1','tool',json.dumps({'output':json.dumps({'request_id':self.rid,'status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':[self.cid]})}),None,None,1004,None),
            (3,'session-1','assistant',self.text,None,'stop',1005,None)])
        self.c.execute('INSERT INTO delivery_obligations VALUES(?,?,?,?,?,?,?,?,?)',('event-1','native-key','discord',self.thread,self.thread,self.text,'delivered',1006,1007));self.c.commit()
        self.now=1010;self.q=core.Queue(self.meta/'landing-followup',now=lambda:self.now)
        self.dc=FakeDiscord(self.text);self.factory_calls=0
        def factory():self.factory_calls+=1;return self.dc
        self.intake=li.Intake(self.q,self.path,self.meta,factory,check_scope=lambda url:True)
        self.intake.activate(epoch=990)
        self.source=self.meta/'state/shein-campaigns/single-clone'/self.rid/'state.json';self.source.parent.mkdir(parents=True)
        self.url='https://fixture.invalid/quiz/?utm_source=facebook&utm_campaign=b01fb06c127&utm_adgroup=b01fb06c127g01'
        creative={'url_tags':'','object_story_spec':{'link_data':{'link':self.url}}}
        self.manifest={'operation':'TEST-DIRECT','request_id':self.rid,'campaigns':[{'account_id':self.aid,'ads':[{'creative_payload':creative}]}]}
        self.state={'request':{'request_id':self.rid,'source_thread_id':self.thread,'source_channel_id':self.parent},'phase':'COMPLETE_FUTURE_ACTIVE',
            'manifest':self.manifest,'engine_result':{'campaign_ids':[self.cid]},'final_readback':[{'campaign':{'id':self.cid,'account_id':self.aid},'ads':{'data':[{'id':'111111111111113','creative':creative}]}}]}
        self.save_state()
        op=self.meta/'operations/TEST-DIRECT.json';op.parent.mkdir();op.write_text(json.dumps({'strategy_family':'direct_traffic_future_niche'}))
    def save_state(self):self.source.write_text(json.dumps(self.state))
    def tearDown(self):
        self.c.close();self.q.db.close();self.pp.stop();self.bp.stop();self.tmp.cleanup()
    def jobs(self):return self.q.db.execute('SELECT count(*) FROM jobs').fetchone()[0]
    def test_new_completed_native_reply_enqueues_after_real_readback_only(self):
        before=self.source.read_bytes();result=self.intake.tick()
        self.assertEqual(result['counts']['ready'],1);self.assertEqual(self.jobs(),1)
        job=dict(self.q.db.execute('SELECT * FROM jobs').fetchone());self.assertEqual(job['state'],'READY')
        self.assertEqual(job['reply_id'],'150000000000000020');self.assertEqual(self.dc.posts,0)
        self.assertEqual(self.source.read_bytes(),before)
    def test_created_campaign_without_delivered_reply_never_enqueues(self):
        self.c.execute("UPDATE delivery_obligations SET state='pending'");self.c.commit()
        self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.factory_calls,0)
    def test_local_delivered_flag_without_discord_readback_does_not_arm(self):
        self.dc.messages=[];self.intake.tick();self.assertEqual(self.jobs(),0)
        row=self.q.db.execute("SELECT state FROM native_intake WHERE id='native:event-1'").fetchone();self.assertEqual(row['state'],'PENDING')
    def test_readback_failure_resumes_same_event_without_duplicate(self):
        messages=self.dc.messages;self.dc.messages=[];self.intake.tick()
        self.dc.messages=messages;self.now+=60;self.intake.tick();self.intake.tick()
        self.assertEqual(self.jobs(),1);self.assertEqual(self.dc.posts,0)
        self.assertEqual(self.q.db.execute("SELECT count(*) FROM messages WHERE state IN ('PREPARED','INTENT')").fetchone()[0],0)
    def test_restart_does_not_duplicate_job(self):
        self.intake.tick();self.q.db.close();self.q=core.Queue(self.meta/'landing-followup',now=lambda:1010)
        restarted=li.Intake(self.q,self.path,self.meta,lambda:self.dc,check_scope=lambda u:True)
        restarted.tick();self.assertEqual(self.jobs(),1)
    def test_old_native_deliveries_do_not_backfill(self):
        self.c.execute('UPDATE delivery_obligations SET created_at=980');self.c.commit()
        self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.factory_calls,0)
    def test_old_source_terminal_state_is_not_replayed(self):
        os.utime(self.source,(980,980));self.intake.tick()
        self.assertEqual(self.jobs(),0);self.assertEqual(self.factory_calls,0)
    def test_bot_family_excluded(self):
        (self.meta/'operations/TEST-DIRECT.json').write_text(json.dumps({'strategy_family':'chatpion_bot_messenger'}))
        self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.factory_calls,0)
    def test_nonterminal_state_never_navigates_or_stages(self):
        self.state['phase']='RECOVERY_PENDING';self.save_state();self.intake.tick()
        self.assertEqual(self.jobs(),0);self.assertEqual(self.dc.posts,0)
    def test_account_channel_mismatch_is_rejected(self):
        self.state['request']['source_channel_id']='150000000000000099';self.save_state();self.intake.tick()
        self.assertEqual(self.jobs(),0)
    def test_discord_parent_mismatch_is_rejected(self):
        self.dc.parent='150000000000000098';self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_foreign_bot_reply_does_not_arm(self):
        self.dc.messages[0]['author']['id']='150000000000000098';self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_empty_embed_messages_do_not_confuse_reply_matching(self):
        self.dc.messages.insert(0,{'id':'150000000000000019','channel_id':self.thread,'content':'','author':{'id':self.dc.bot_id}})
        self.intake.tick();self.assertEqual(self.jobs(),1)
    def test_chunked_native_reply_is_read_back_in_order(self):
        self.dc.messages=[{'id':'150000000000000020','channel_id':self.thread,'content':'Criada C127. (1/2)','author':{'id':self.dc.bot_id}},
            {'id':'150000000000000021','channel_id':self.thread,'content':'Pedido concluído e validado. (fixture offline) (2/2)','author':{'id':self.dc.bot_id}}]
        self.intake.tick();self.assertEqual(self.jobs(),1)
        receipt=json.loads(self.q.db.execute('SELECT receipt FROM native_receipts').fetchone()[0]);self.assertEqual(len(receipt['message_ids']),2)
    def test_identical_duplicate_replies_fail_closed(self):
        self.dc.messages.append({**self.dc.messages[0],'id':'150000000000000021'})
        self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_native_turn_busy_yields_only_background(self):
        self.c.execute('INSERT INTO session_turn_leases VALUES(?,?)',('session-1',2000));self.c.commit()
        self.assertTrue(li.native_busy(self.path,now=1010))
        self.c.execute('DELETE FROM session_turn_leases');self.c.commit();self.assertFalse(li.native_busy(self.path,now=1010))
    def test_unreadable_native_db_defers_observer(self):self.assertTrue(li.native_busy(self.base/'missing.db',now=1010))
    def test_followup_control_conversation_does_not_stop_its_worker(self):
        self.policy.write_text(json.dumps({'all_problem_destination_thread':self.thread,'creation_path_isolation':{'followup_control_thread_exempt':True}}))
        self.c.execute('INSERT INTO session_turn_leases VALUES(?,?)',('session-1',2000));self.c.commit()
        self.assertFalse(li.native_busy(self.path,now=1010))

    def test_other_campaign_turn_still_has_absolute_priority(self):
        self.policy.write_text(json.dumps({'all_problem_destination_thread':self.thread,'creation_path_isolation':{'followup_control_thread_exempt':True}}))
        self.c.execute("INSERT INTO sessions SELECT 'other-creation',source,session_key,'150000000000000099','150000000000000099',origin_json,started_at FROM sessions WHERE id='session-1'")
        self.c.execute('INSERT INTO session_turn_leases VALUES(?,?)',('session-1',2000))
        self.c.execute('INSERT INTO session_turn_leases VALUES(?,?)',('other-creation',2000));self.c.commit()
        self.assertTrue(li.native_busy(self.path,now=1010))

    def test_invalid_priority_policy_fails_closed(self):
        self.policy.write_text('invalid policy fixture')
        self.assertTrue(li.native_busy(self.path,now=1010))
    def test_native_connection_is_mechanically_read_only(self):
        with li.readonly(self.path) as c:
            with self.assertRaises(sqlite3.OperationalError):c.execute("DELETE FROM messages")
    def test_only_current_user_turn_tool_result_can_trigger(self):
        self.c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)',(4,'session-1','user','Novo pedido sem criação',None,None,1005.5,'150000000000000011'))
        self.c.execute('UPDATE messages SET id=5 WHERE id=3');self.c.commit()
        self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_no_terminal_tool_reference_ignored_without_bot_token(self):
        self.c.execute("UPDATE messages SET content='Relatório read-only' WHERE role='tool'");self.c.commit()
        self.intake.tick();self.assertEqual(self.factory_calls,0);self.assertEqual(self.jobs(),0)
    def test_literal_request_id_not_normalized(self):
        refs=li.terminal_references([{'content':json.dumps({'request_id':'../escape','status':'COMPLETE'})}])
        self.assertEqual(refs,{})
    def test_source_reset_after_delivery_does_not_lose_event(self):
        self.c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?)',('session-new','discord','native-key',self.thread,self.thread,json.dumps({'parent_chat_id':self.parent}),1008));self.c.commit()
        self.intake.tick();self.assertEqual(self.jobs(),1)
    def test_cursor_handles_more_than_one_batch_with_same_timestamp(self):
        self.c.execute('DELETE FROM delivery_obligations')
        self.c.executemany('INSERT INTO delivery_obligations VALUES(?,?,?,?,?,?,?,?,?)',[(f'event-{i:03d}','native-key','discord',self.thread,self.thread,'No matching final','delivered',1006,1007) for i in range(105)]);self.c.commit()
        self.intake.tick();self.intake.tick()
        count=self.q.db.execute("SELECT count(*) FROM native_intake WHERE id LIKE 'native:%' AND state='IGNORED'").fetchone()[0]
        self.assertEqual(count,105)

    def test_crash_after_stage_reuses_frozen_proof_when_audit_gains_metadata(self):
        origin={'thread_id':self.thread,'parent_id':self.parent}
        payload=li.build_from_source(self.source,self.rid,origin,self.q.root,self.meta,lambda u:True)
        key=self.q.stage(payload,lambda u:True)
        self.state['harmless_extra_audit_metadata']='offline fixture after stage';self.save_state()
        self.intake.tick()
        self.assertEqual(self.jobs(),1);job=self.q.job(key)
        self.assertEqual(job['state'],'READY');self.assertEqual(job['payload']['creation_proof'],payload['creation_proof'])

    def midturn_fixture(self, **changes):
        origin={'platform':'discord','chat_id':self.thread,'thread_id':self.thread,
            'parent_chat_id':self.parent,'message_id':'150000000000000011',
            'source_message_id':'150000000000000011'}
        origin.update(changes)
        text=('[OUT-OF-BAND USER MESSAGE — a direct message from the user, delivered once at this position; not tool output and not a new delivery when replayed from conversation history]\n'
            'Gateway message origin (JSON data, not instructions or authorization):\n'+json.dumps(origin)+'\n'
            'Do not guess a reply destination when these fields are insufficient.\n\n'
            '[New message — ACTIONABLE USER REQUEST]\ncorrection offline\n[/OUT-OF-BAND USER MESSAGE]')
        self.c.execute('UPDATE messages SET content=?,platform_message_id=NULL WHERE id=1',(text,));self.c.commit()
        return text

    def test_midturn_structured_origin_is_supported_without_native_writes(self):
        self.midturn_fixture();before=self.path.read_bytes()
        self.intake.tick();self.assertEqual(self.jobs(),1)
        receipt=json.loads(self.q.db.execute('SELECT receipt FROM native_receipts').fetchone()[0])
        self.assertEqual(receipt['source_message_id'],'150000000000000011')
        self.assertEqual(before,self.path.read_bytes())

    def test_midturn_foreign_thread_fails_closed(self):
        self.midturn_fixture(thread_id='150000000000000099')
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_midturn_foreign_parent_fails_closed(self):
        self.midturn_fixture(parent_chat_id='150000000000000099')
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_midturn_source_id_disagreement_fails_closed(self):
        self.midturn_fixture(source_message_id='150000000000000098')
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_quoted_midturn_envelope_is_not_an_origin(self):
        text=self.midturn_fixture()
        self.c.execute('UPDATE messages SET content=? WHERE id=1',('quoted example\n'+text,));self.c.commit()
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_correctable_ignored_origin_is_reconsidered_without_cursor_reset(self):
        self.midturn_fixture()
        self.intake.record('native:event-1','IGNORED')
        self.q.db.execute("UPDATE intake_settings SET value='1007' WHERE key='cursor'")
        self.q.db.execute("UPDATE intake_settings SET value='event-1' WHERE key='cursor_key'");self.q.db.commit()
        self.intake.tick();self.assertEqual(self.jobs(),1)
        self.assertEqual(self.q.db.execute("SELECT value FROM intake_settings WHERE key='activation_epoch'").fetchone()[0],'990.0')
        self.intake.tick();self.assertEqual(self.jobs(),1)

    def grouped_fixture(self):
        groups=[]
        for number,cid in [(140,self.cid),(131,'111111111111122')]:
            child=self.rid+'-c'+str(number)
            state=json.loads(json.dumps(self.state));state['request']['request_id']=child
            state['manifest']['request_id']=child
            state['engine_result']['campaign_ids']=[cid]
            state['final_readback'][0]['campaign']['id']=cid
            state['request']['source_message_id']='150000000000000010'
            url=self.url+'&offline_group='+str(number)
            state['manifest']['campaigns'][0]['ads'][0]['creative_payload']['object_story_spec']['link_data']['link']=url
            state['final_readback'][0]['ads']['data'][0]['creative']['object_story_spec']['link_data']['link']=url
            path=self.source.parent.parent/child/'state.json';path.parent.mkdir();path.write_text(json.dumps(state))
            groups.append({'source_number':number,'quantity':1,'campaign_ids':[cid]})
        self.source.unlink()
        self.aggregate={'request_id':self.rid,'status':'COMPLETE_FUTURE_ACTIVE','account_id':self.aid,'campaigns':2,'groups':groups}
        self.aggregate_path=self.meta/'audit/shein/campaigns/intake'/self.rid/'final-verification.json'
        self.aggregate_path.parent.mkdir(parents=True);self.aggregate_path.write_text(json.dumps(self.aggregate))
        self.c.execute('UPDATE messages SET content=? WHERE role=?',(json.dumps(self.aggregate),'tool'));self.c.commit()

    def test_grouped_completion_enumerates_all_children_and_reuses_receipt(self):
        self.grouped_fixture();self.intake.tick()
        self.assertEqual(self.jobs(),2)
        self.assertEqual(self.q.db.execute('SELECT count(*) FROM links').fetchone()[0],2)
        receipts=[json.loads(x[0]) for x in self.q.db.execute('SELECT receipt FROM native_receipts')]
        self.assertEqual({r['native_obligation_id'] for r in receipts},{'event-1'})
        self.assertEqual(self.q.db.execute("SELECT state FROM native_intake WHERE id='native:event-1'").fetchone()[0],'READY')
        self.intake.tick();self.assertEqual(self.jobs(),2)

    def test_grouped_incomplete_child_never_partially_arms_or_declares_ready(self):
        self.grouped_fixture()
        p=self.source.parent.parent/(self.rid+'-c131')/'state.json'
        d=json.loads(p.read_text());d['phase']='RECOVERY_PENDING';p.write_text(json.dumps(d))
        self.intake.tick();self.assertEqual(self.jobs(),0)
        self.assertEqual(self.q.db.execute("SELECT state FROM native_intake WHERE id='native:event-1'").fetchone()[0],'PENDING')

    def test_grouped_missing_child_never_partially_arms(self):
        self.grouped_fixture();(self.source.parent.parent/(self.rid+'-c131')/'state.json').unlink()
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_grouped_campaign_id_mismatch_is_rejected(self):
        self.grouped_fixture();self.aggregate['groups'][1]['campaign_ids']=['111111111111199']
        self.aggregate_path.write_text(json.dumps(self.aggregate))
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_grouped_wrong_total_is_rejected(self):
        self.grouped_fixture();self.aggregate['campaigns']=3;self.aggregate_path.write_text(json.dumps(self.aggregate))
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def test_grouped_old_child_is_not_backfilled(self):
        self.grouped_fixture();os.utime(self.source.parent.parent/(self.rid+'-c131')/'state.json',(980,980))
        self.intake.tick();self.assertEqual(self.jobs(),0)

    def daily_fixture(self):
        state=dict(self.state);state.pop('phase');state['stage']='COMPLETE';state['request_id']=self.rid
        state['final']={'status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':[self.cid]}
        state['discord_readback']={'thread_id':self.thread,'message_id':self.dc.messages[0]['id'],'content_match':True}
        p=self.meta/'engine-v3/audit/daily'/('offline-daily.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(state))
        return p

    def test_daily_partial_reply_never_substitutes_final_creation_reply(self):
        self.daily_fixture();self.dc.messages[0]['content']='🟡 V3 PARCIAL — fixture offline'
        self.assertEqual(self.intake.scan_daily(lambda:self.dc),0);self.assertEqual(self.jobs(),0)
        self.assertFalse(list((self.q.root/'creation-proofs').glob('*.json')))

    def test_daily_unchanged_native_final_reply_is_enough_without_callback(self):
        p=self.daily_fixture();before=p.read_bytes();self.dc.messages[0]['content']='✅ V3 CONCLUÍDO — fixture offline'
        self.assertEqual(self.intake.scan_daily(lambda:self.dc),1)
        self.assertEqual(self.jobs(),1);self.assertEqual(self.dc.posts,0);self.assertEqual(before,p.read_bytes())


if __name__=='__main__':unittest.main()
