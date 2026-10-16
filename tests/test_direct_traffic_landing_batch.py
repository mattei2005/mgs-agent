"""Offline continuous-loop/outbox fixtures. They never open real pages."""
import copy,json,unittest
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
import test_direct_traffic_landing_retry_policy as retry_fixtures
from ares_campaign_v3 import landing_batch as batch,landing_retry_policy as finite,landing_followup_reporting as reporting
from ares_campaign_v3 import landing_followup as core

class BatchTests(unittest.TestCase):
    setUpBase=fixtures.FollowupTests.setUp
    tearDown=fixtures.FollowupTests.tearDown
    arm=fixtures.FollowupTests.arm
    multi=retry_fixtures.FiniteRetryTests.multi
    closure=retry_fixtures.FiniteRetryTests.closure
    def setUp(self):
        self.setUpBase();self.path=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';self.path.parent.mkdir(parents=True,exist_ok=True)
        self.cfg={'no_ad_retry_policy':{'enabled':True,'generation':'batch-offline','authority_thread_id':core.INCIDENT_THREAD,'initial_no_ad_attempts':3,'final_no_ad_attempts':1,'retry_after_seconds':0,'automatic_recovery':{'enabled':True,'additional_no_ad_attempts':1,'wait_after_round_seconds':60}},'active_observation_route':{'mode':'LEAN_NORMAL_NEW_TAB','observation_query_flag':{'name':'nocache','value':None}},'continuous_execution':{'enabled':True,'maximum_run_seconds':10800},'progress_reporting':{'enabled':True,'mode':'PER_ITEM','thread_id':core.INCIDENT_THREAD,'delivery_batch_size':5}}
        self.path.write_text(json.dumps(self.cfg));self.seen=[]
    def prepare(self,key):
        self.q.claim('worker');scope=batch.freeze_scope(self.q,key,'worker');items=[]
        for entry in scope['jobs']:
            j=self.q.job(entry['key'])
            for l in j['links']:
                if l['state'] in batch.PENDING:
                    src=j['payload']['links'][l['idx']];items.append(dict(job=j['key'],index=l['idx'],url=src.get('landing_url') or src['effective_campaign_url'].replace('/quiz/test/','/rec-test/'),mapping_source='offline fixture only'))
        batch.store_manifest(self.q,scope,{'items':items},'worker',lambda u:True)
        return scope
    def execute(self,item,attempt,result='PASS'):
        self.seen.append((item['index'],attempt,result));self.clock.value+=1
        e=self.closure(f'offline-{item["index"]}-{attempt}')
        if result=='PASS':e.update(observed_url=self.q.job(item['job'])['payload']['links'][item['index']]['landing_url'],network_ad_confirmed=True,ad_description='Offline network-ad fixture',samples=[dict(monotonic_seconds=t,ad_visible=True,tab_active=True,screenshot=f'fixture-{t}.png') for t in [0,5,10]])
        elif result=='ERROR':e['diagnosis']='offline transport failure'
        return result,e
    def test_complete_continuous_batch_without_discord_between_items(self):
        key=self.multi();scope=self.prepare(key);before=self.dc.posts
        out=batch.run(self.q,scope,'worker',self.execute)
        self.assertEqual(len(out['results']),2);self.assertEqual([x[0] for x in self.seen],[0,1]);self.assertEqual(self.q.job(key)['state'],'OBSERVED');self.assertEqual(self.dc.posts,before)
        rows=self.q.db.execute("select * from messages where key like 'landing-item:%' order by created,rowid").fetchall();self.assertEqual(len(rows),2);self.assertIn('**1/2**',rows[0]['content']);self.assertIn('**2/2**',rows[1]['content'])
    def test_partial_map_rejected_before_any_attempt(self):
        key=self.multi();self.q.claim('worker');scope=batch.freeze_scope(self.q,key,'worker');src=self.q.job(key)['payload']['links'][0]
        with self.assertRaises(ValueError):batch.store_manifest(self.q,scope,{'items':[dict(job=key,index=0,url=src['landing_url'],mapping_source='fixture')]},'worker',lambda u:True)
        self.assertEqual([l['attempt'] for l in self.q.job(key)['links']],[0,0])
    def test_duplicate_or_mutated_map_rejected(self):
        self.arm();scope=self.prepare(self.key);x=batch.cached_manifest(self.q,scope,'worker')['items'][0]
        with self.assertRaises(ValueError):batch.store_manifest(self.q,scope,{'items':[x,x]},'worker',lambda u:True)
        x=copy.deepcopy(x);x['url']+='&not-authorized=1'
        with self.assertRaises(ValueError):batch.store_manifest(self.q,scope,{'items':[x]},'worker',lambda u:True)
    def test_cooldown_releases_loop_then_cached_fifth_only(self):
        key=self.multi();scope=self.prepare(key)
        def execute(item,n):return self.execute(item,n,'NO_AD' if item['index']==0 and n<5 else 'PASS')
        out=batch.run(self.q,scope,'worker',execute);self.assertEqual(out['state'],'AUTOMATIC_RECOVERY_COOLDOWN');self.assertEqual(self.q.job(key)['links'][0]['attempt'],4);self.assertEqual(self.q.job(key)['links'][1]['state'],'PASSED')
        self.clock.value=out['transition']['due'];finite.maintain(self.q);prior=len(self.seen);out=batch.run(self.q,scope,'worker',execute)
        self.assertEqual(self.seen[prior:],[(0,5,'PASS')]);self.assertEqual(self.q.job(key)['state'],'OBSERVED')
    def test_pause_between_items_not_reopen_pass(self):
        key=self.multi();scope=self.prepare(key);batch.run(self.q,scope,'worker',self.execute,should_stop=lambda:len(self.seen)>=1)
        self.assertEqual(self.q.job(key)['links'][0]['state'],'PASSED');batch.run(self.q,scope,'worker',self.execute)
        self.assertEqual([i for i,n,r in self.seen],[0,1])
    def test_technical_error_yields_diagnosis_not_noad_retry(self):
        self.arm();scope=self.prepare(self.key);out=batch.run(self.q,scope,'worker',lambda i,n:self.execute(i,n,'ERROR'))
        self.assertEqual(out['state'],'BATCH_TECHNICAL_DIAGNOSIS');self.assertEqual(len(self.seen),1);self.assertEqual(self.q.no_ad_count(self.key,0),0)
    def test_item_delivery_is_separate_and_idempotent(self):
        self.arm();scope=self.prepare(self.key);batch.run(self.q,scope,'worker',self.execute);before=self.dc.posts
        reporting.deliver_items(self.q,lambda:self.dc,self.cfg['progress_reporting']);self.assertEqual(self.dc.posts,before+1)
        reporting.deliver_items(self.q,lambda:self.dc,self.cfg['progress_reporting']);self.assertEqual(self.dc.posts,before+1)
        self.assertIsNone(reporting.prepare(self.q,self.cfg['progress_reporting']))
    def test_reporter_failure_does_not_block_next_item(self):
        key=self.multi();scope=self.prepare(key);batch.run(self.q,scope,'worker',self.execute)
        self.dc.fail_get=True;out=reporting.deliver_items(self.q,lambda:self.dc,self.cfg['progress_reporting']);self.assertEqual(out['state'],'DELIVERY_DEFERRED');self.assertEqual(self.q.job(key)['state'],'OBSERVED')
        self.dc.fail_get=False;reporting.deliver_items(self.q,lambda:self.dc,self.cfg['progress_reporting'])
        self.assertEqual(self.q.db.execute("select count(*) from messages where key like 'landing-item:%' and state='VERIFIED'").fetchone()[0],2)
    def test_batch_prompt_uses_one_continuous_command(self):
        self.arm();scope=self.prepare(self.key);j=self.q.job(self.key);j.update(batch_scope_path='/offline/batch-scope.json',batch_jobs=[],prepared_batch={'items':[],'missing':[]})
        text=core.worker_prompt(self.key,'worker',0,j);self.assertIn('ares-direct-traffic-batch-observe.py',text);self.assertIn('sem outro turno de modelo por URL',text)
    def test_worker_repair_prompt_normal_no_gallery(self):
        self.arm();j=self.q.job(self.key);j['state']='REPAIRING';text=core.worker_prompt(self.key,'worker',0,j)
        self.assertIn('SOMENTE janela vazia NORMAL',text);self.assertNotIn('prova real de janela privada',text)
    def test_dispatcher_invokes_one_worker_for_whole_batch(self):
        import importlib.util,types
        key=self.multi();self.cfg.update(provider='openai-codex',model='offline-no-provider-call');self.path.write_text(json.dumps(self.cfg))
        path=__import__('pathlib').Path('/root/mgs-agent/scripts/ares-direct-traffic-followup.py');spec=importlib.util.spec_from_file_location('offline_batch_dispatch',path);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli);calls=[]
        def command(argv,**kwargs):
            if argv[-1]=='status':return types.SimpleNamespace(returncode=0,stdout=json.dumps({'locked':False}))
            self.assertIn('chat',argv);calls.append(argv);prompt=__import__('pathlib').Path(argv[argv.index('--query-file')+1]);scope=json.loads((prompt.parent/'batch-scope.json').read_text());self.assertIn('LOTE CONTINUO',prompt.read_text());batch.run(self.q,scope,scope['owner'],self.execute);return types.SimpleNamespace(returncode=0)
        with patch.object(cli,'report_progress'),patch.object(cli,'native_busy',return_value=False),patch.object(cli.subprocess,'run',side_effect=command),patch.object(cli.shutil,'which',return_value='/offline/hermes'),patch.object(cli,'Discord',return_value=self.dc),patch.object(cli,'flush'):
            out=cli.tick(self.q)
        self.assertEqual(len(calls),1);self.assertEqual(len(self.seen),2);self.assertEqual(out['state'],'BATCH_PROGRESS_SAVED');self.assertEqual(self.q.job(key)['state'],'OBSERVED')

    def test_report_total_includes_already_observed_human_peer(self):
        key=self.multi();self.arm()
        with self.q.tx():
            self.q.db.execute('update jobs set created=? where key=?',(self.clock.value-1,self.key))
            for k in [self.key,key]:self.q.db.execute('insert into native_receipts values(?,?)',(k,json.dumps({'native_obligation_id':'offline-human'})))
            self.q.db.execute('insert into native_intake values(?,?,?,?,?)',('native:offline-human',self.clock.value,'READY',None,None))
        self.q.claim('worker');self.q.begin(self.key,'worker',0);r,e=self.execute({'job':self.key,'index':0},1);self.q.result(self.key,'worker',0,r,e);self.seen=[]
        scope=self.prepare(key);self.assertEqual(set(scope['report_jobs']),{self.key,key});batch.run(self.q,scope,'worker',self.execute)
        rows=self.q.db.execute('select content from messages where key like ? order by created,rowid',('landing-item:'+key+':%',)).fetchall();self.assertIn('**2/3**',rows[0][0]);self.assertIn('**3/3**',rows[1][0])
    def test_resume_keeps_frozen_scope_despite_new_intake(self):
        key=self.multi();scope=self.prepare(key);batch.run(self.q,scope,'worker',self.execute,should_stop=lambda:len(self.seen)>=1)
        p=copy.deepcopy(self.payload);p['operation']='LATER-OUTSIDE-COHORT';later=self.q.stage(p,lambda u:True);core.publish_creation(self.q,later,'offline later',self.dc)
        self.q.claim('worker');resumed=batch.freeze_scope(self.q,key,'worker');self.assertNotIn(later,[x['key'] for x in resumed['jobs']]);self.assertEqual(resumed['report_jobs'],scope['report_jobs'])

    def test_missing_mapping_no_execute(self):
        p=copy.deepcopy(self.payload);p['operation']='MISSING-MAP';p['links'][0].pop('landing_url');p['links'][0].pop('mapping_source');key=self.q.stage(p,lambda u:True);core.publish_creation(self.q,key,'offline',self.dc);self.q.claim('worker');scope=batch.freeze_scope(self.q,key,'worker')
        out=batch.run(self.q,scope,'worker',lambda *a:self.fail('No input before complete mapping'));self.assertEqual(out['state'],'MAPPING_REQUIRED');self.assertEqual(out['browser_actions'],0)

if __name__=='__main__':unittest.main()
