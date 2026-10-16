"""Offline completion-boundary regressions; never evidence of live ads/activation."""
import json,unittest
import test_direct_traffic_landing_intake as fixtures

class CompletionBoundaryTests(unittest.TestCase):
    setUp=fixtures.IntakeTests.setUp
    tearDown=fixtures.IntakeTests.tearDown
    save_state=fixtures.IntakeTests.save_state
    jobs=fixtures.IntakeTests.jobs
    def partial(self):
        self.state['phase']='ACTIVATION_DEFERRED';self.state['engine_result']['status']='COMPLETE_PAUSED';self.save_state()
        text='Campanha criada e validada, pausada; aguarda confirmação de ativação. (offline)'
        self.c.execute("update messages set content=? where role='tool'",(json.dumps({'request_id':self.rid,'status':'E2E_TARGET_EXCEEDED','engine_result':{'status':'COMPLETE_PAUSED'}}),))
        self.c.execute("update messages set content=? where role='assistant'",(text,));self.c.execute('update delivery_obligations set content=?',(text,));self.c.commit();self.dc.messages[0]['content']=text
    def completed_reply(self,save_terminal=True):
        if save_terminal:self.state['phase']='COMPLETE_FUTURE_ACTIVE';self.save_state()
        text='Ativação confirmada; mesmo pedido concluído e validado. (offline)'
        self.c.executemany('insert into messages values(?,?,?,?,?,?,?,?)',[(4,'session-1','user','Confirmação elegível de continuação (offline)',None,None,1011,'150000000000000021'),(5,'session-1','tool',json.dumps({'request_id':self.rid,'status':'COMPLETE_FUTURE_ACTIVE','campaign_ids':[self.cid]}),None,None,1012,None),(6,'session-1','assistant',text,None,'stop',1013,None)])
        self.c.execute('insert into delivery_obligations values(?,?,?,?,?,?,?,?,?)',('event-complete','native-key','discord',self.thread,self.thread,text,'delivered',1014,1015));self.c.commit();self.dc.messages.append({'id':'150000000000000030','channel_id':self.thread,'content':text,'author':{'id':self.dc.bot_id}});self.now=1020
    def test_deferred_activation_does_not_enqueue_pc1(self):
        self.partial();self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.dc.posts,0)
    def test_engine_complete_paused_does_not_override_request_gate(self):
        self.partial();self.intake.tick();self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.state['phase'],'ACTIVATION_DEFERRED')
    def test_saved_terminal_state_alone_does_not_promote_partial_reply(self):
        self.partial();self.intake.tick();self.state['phase']='COMPLETE_FUTURE_ACTIVE';self.save_state();self.now+=61;self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_genuine_new_completion_automatically_arms_without_user_nudge(self):
        self.partial();self.intake.tick();self.completed_reply();native_before=self.path.read_bytes();source_before=self.source.read_bytes();r=self.intake.tick()
        self.assertEqual(r['counts']['ready'],1);self.assertEqual(self.jobs(),1);j=dict(self.q.db.execute('select * from jobs').fetchone());self.assertEqual(j['state'],'READY');self.assertEqual(j['reply_id'],'150000000000000030');self.assertEqual(self.dc.posts,0);self.assertEqual(self.path.read_bytes(),native_before);self.assertEqual(self.source.read_bytes(),source_before)
    def test_repeated_ticks_never_duplicate_completion_job(self):
        self.partial();self.intake.tick();self.completed_reply();self.intake.tick();self.intake.tick();self.now+=61;self.intake.tick();self.assertEqual(self.jobs(),1);self.assertEqual(self.q.db.execute('select count(*) from links').fetchone()[0],1)
    def test_premature_success_reply_still_cannot_bypass_saved_gate(self):
        self.partial();self.intake.tick();self.completed_reply(save_terminal=False);self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.dc.posts,0)
    def test_unpublished_new_completion_does_not_arm(self):
        self.partial();self.intake.tick();self.completed_reply();self.dc.messages=self.dc.messages[:1];self.intake.tick();self.assertEqual(self.jobs(),0)
    def test_other_origin_reference_does_not_arm_or_rewrite_origin(self):
        self.partial();self.intake.tick();self.completed_reply();self.state['request']['source_thread_id']='150000000000000099';self.save_state();before=self.source.read_bytes();self.intake.tick();self.assertEqual(self.jobs(),0);self.assertEqual(self.source.read_bytes(),before)
    def test_original_activation_boundary_not_reset(self):
        self.partial();self.intake.tick();self.completed_reply();self.intake.tick();self.assertEqual(self.q.db.execute("select value from intake_settings where key='activation_epoch'").fetchone()[0],'990.0')

if __name__=='__main__':unittest.main()
