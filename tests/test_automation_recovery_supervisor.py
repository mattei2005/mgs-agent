import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

BASE=Path('/root/mgs-agent');sys.path.insert(0,str(BASE/'scripts'))
from mgs_automation_continuity import Queue
SUP=BASE/'scripts/mgs_automation_supervisor.py'


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SUP.exists(),'Common recovery consumer is not implemented')
        spec=importlib.util.spec_from_file_location('supervisor',SUP);assert spec and spec.loader
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.q=Queue(Path(self.tmp.name)/'q.sqlite3');self.addCleanup(self.q.close)
        self.calls=[];self.notices=[]

    def add(self,key='native:zeus:abc',**fields):
        return self.q.enqueue(key,dict(kind='native',profile='zeus',job_id='abc',**fields),'timeout',now=100)

    def run_drive(self,obs=None,busy=False,active=False,result='Pendente: aguardando validação.'):
        def run(row,mode):self.calls.append((row['key'],mode));return result
        return self.m.drive(self.q,obs or {},run,lambda:busy,lambda s:active,lambda r,t:self.notices.append(t),now=200,max_jobs=1)

    def test_busy_queues_without_agent_call_and_no_failure_budget(self):
        j=self.add(resource='pc1');self.run_drive(busy=True)
        row=self.q.get(j['key']);self.assertEqual(row['state'],'waiting_resource');self.assertEqual(row['attempts'],0);self.assertFalse(self.calls)

    def test_resource_wait_preserves_verification_phase(self):
        j=self.add(resource='pc1');self.q.defer(j['key'],'verifying','await_readback',now=150,delay=1)
        self.run_drive(busy=True)
        self.assertEqual(self.q.get(j['key'])['state'],'verifying')
        self.assertFalse(self.calls)

    def test_resource_wait_never_shortens_existing_backoff(self):
        j=self.add(resource='pc1');self.q.defer(j['key'],'retry_scheduled','cooldown',now=150,delay=3600)
        due=self.q.get(j['key'])['due'];self.run_drive(busy=True)
        self.assertGreaterEqual(self.q.get(j['key'])['due'],due)
        self.assertFalse(self.calls)

    def test_newly_discovered_pc1_dependency_persists_without_reprobe_loop(self):
        j=self.add();self.run_drive(result='Pendente: PC1 ocupado por outra sessão.')
        self.run_drive(busy=True)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(json.loads(self.q.get(j['key'])['source'])['resource'],'pc1')

    def test_release_causes_one_resume(self):
        j=self.add(resource='pc1');self.run_drive(busy=False)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.q.get(j['key'])['state'],'retry_scheduled')

    def test_active_original_writer_prevents_duplicate(self):
        j=self.add();self.run_drive(active=True)
        self.assertFalse(self.calls);self.assertEqual(self.q.get(j['key'])['state'],'waiting_resource')

    def test_llm_claim_cannot_close_without_real_validator(self):
        j=self.add();self.run_drive(result='Resolvido: tudo passou.')
        self.assertEqual(self.q.get(j['key'])['state'],'verifying');self.assertFalse(self.notices)

    def test_real_fresh_readback_closes_without_reexecution(self):
        j=self.add();obs={'native:zeus:abc':{'status':'OK','verified':True,'target':'abc','receipt':'real-fixture-readback','at':180}}
        self.run_drive(obs)
        self.assertEqual(self.q.get(j['key'])['state'],'completed_validated');self.assertFalse(self.calls)

    def test_active_owner_prevents_green_from_fresh_progress_log(self):
        j=self.add();obs={'native:zeus:abc':{'status':'OK','verified':True,'target':'abc','receipt':'fresh-progress','at':180}}
        self.run_drive(obs,active=True)
        self.assertEqual(self.q.get(j['key'])['state'],'waiting_resource')
        self.assertFalse(self.calls)

    def test_old_success_cannot_close_new_incident(self):
        j=self.add();obs={'native:zeus:abc':{'status':'OK','verified':True,'target':'abc','receipt':'old','at':90}}
        self.run_drive(obs);self.assertNotEqual(self.q.get(j['key'])['state'],'completed_validated')

    def test_unknown_and_expired_job_only_diagnose(self):
        j=self.add(time_sensitive=True);self.run_drive();self.assertEqual(self.calls[0][1],'diagnose_only')

    def test_2fa_stays_visible_and_does_not_retry_blind_action(self):
        j=self.add();self.run_drive(result='Bloqueado: 2FA necessária no Facebook.')
        self.assertEqual(self.q.get(j['key'])['state'],'waiting_human');self.assertEqual(len(self.notices),1)
        self.calls.clear();self.run_drive();self.assertFalse(self.calls)

    def test_terminal_prefix_is_not_used_to_green_unknown(self):
        self.assertEqual(self.m.source_key_for_alert({'id':'100','embeds':[{'fields':[{'name':'Script','value':'`hermes:zeus:abc`'}]}]}),'native:zeus:abc')
        self.assertEqual(self.m.source_key_for_alert({'id':'101','embeds':[{'fields':[{'name':'Script','value':'`dtr-sb-daily-match-audit.sh`'}]}]}),'producer:dtr-sb-daily-match-audit.sh')

    def test_five_consecutive_dispatch_failures_stop_across_sources(self):
        for n in range(6):self.q.enqueue(f'fixture:job{n}',{'kind':'fixture'},'timeout',now=100+n)
        calls=[]
        def fail(*a):calls.append(a);raise TimeoutError('isolated fixture timeout')
        self.m.drive(self.q,{},fail,lambda:False,lambda s:False,lambda *a:None,now=200,max_jobs=6)
        self.assertEqual(len(calls),5)
        self.assertTrue(self.q.open())

    def test_busy_pc1_never_demotes_confirmation_gate(self):
        j=self.add();self.q.defer(j['key'],'blocked_decision','Critical Subset',now=150,delay=1)
        self.run_drive({},busy=True)
        self.assertEqual(self.q.get(j['key'])['state'],'blocked_decision')
        self.assertFalse(self.calls)

    def test_busy_pc1_keeps_auth_probe_only(self):
        j=self.add();self.q.enqueue(j['source_key'],{**json.loads(j['source']),'resource':'pc1'},'pc1_busy',now=150)
        self.q.defer(j['key'],'waiting_human','2FA',now=150,delay=1)
        self.run_drive({},busy=True)
        self.assertEqual(self.q.get(j['key'])['state'],'waiting_human')
        self.assertFalse(self.calls)

    def test_failed_blocker_notice_cannot_resume_business_work(self):
        j=self.add()
        def notify(*a):raise RuntimeError('fixture delivery unavailable')
        self.m.drive(self.q,{},lambda *a:'Bloqueado: 2FA necessária.',lambda:False,lambda s:False,notify,now=200,max_jobs=1)
        self.assertEqual(self.q.get(j['key'])['state'],'waiting_human')
        self.assertEqual(self.q.get(j['key'])['failures'],0)

    def test_dtr_no_post_validation_cannot_count_as_delivered_report(self):
        self.assertTrue(hasattr(self.m,'dtr_observation'),'Missing independent DTR delivery validator')
        obs=self.m.dtr_observation(base=Path(self.tmp.name),root=Path(self.tmp.name)/'delivery',now=200)
        self.assertEqual(obs['status'],'ERROR')
        self.assertFalse(obs['verified'])

    def test_collector_unavailable_is_explicit_not_empty_healthy(self):
        rows=self.m.monitor_observations('invalid monitor output',now=200)
        self.assertEqual(rows['service:monitor-observation']['status'],'UNKNOWN')


if __name__=='__main__':unittest.main()
