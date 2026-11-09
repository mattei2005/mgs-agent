import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

BASE = Path('/root/mgs-agent')
sys.path.insert(0, str(BASE/'scripts'))
MODULE = BASE/'scripts/mgs_automation_continuity.py'


def load():
    spec = importlib.util.spec_from_file_location('continuity', MODULE)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def enqueue_child(path):
    load().Queue(Path(path)).enqueue('native:zeus:abc', {'kind':'native','profile':'zeus','job_id':'abc'}, 'timeout', now=100)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'Durable common continuity queue is not implemented')
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'queue.sqlite3'
        self.q = self.m.Queue(self.path)

    def job(self, key='native:zeus:abc', cause='timeout', now=100):
        return self.q.enqueue(key, {'kind':'native','profile':'zeus','job_id':'abc'}, cause, now=now)

    def test_restart_dedup_preserves_first_position_and_attempts(self):
        a = self.job()
        b = self.job(now=200)
        self.assertEqual(a['key'],b['key'])
        fresh = self.m.Queue(self.path).get(a['key'])
        self.assertEqual(fresh['created'],100)
        self.assertEqual(fresh['attempts'],0)
        self.assertEqual(len(self.q.open()),1)

    def test_busy_waits_without_consuming_attempt(self):
        j = self.job(cause='pc1_busy')
        self.q.defer(j['key'],'waiting_resource','pc1_busy',now=110,delay=60)
        self.assertEqual(self.q.get(j['key'])['attempts'],0)
        self.assertIsNone(self.q.claim('fixture',now=150))
        self.assertIsNotNone(self.q.claim('fixture',now=171))

    def test_fifo_and_single_claim(self):
        a=self.job();b=self.job('native:ares:def',now=110)
        x=self.q.claim('owner',now=200)
        self.assertEqual(x['key'],a['key'])
        self.assertIsNone(self.q.claim('owner2',now=201))

    def test_expired_dispatch_requires_reconciliation_not_blind_replay(self):
        a=self.job();self.q.claim('owner',now=200,ttl=10)
        self.assertIsNone(self.q.claim('owner2',now=211))
        x=self.q.get(a['key'])
        self.assertEqual(x['state'],'reconciling')
        self.assertTrue(x['needs_reconciliation'])

    def test_closed_requires_verified_evidence(self):
        a=self.job()
        with self.assertRaises(ValueError):self.q.complete(a['key'],{'verified':False},now=210)
        self.q.complete(a['key'],{'verified':True,'target':'fixture','receipt':'readback-1'},now=210)
        self.assertEqual(self.q.get(a['key'])['state'],'completed_validated')
        self.assertFalse(self.q.open())

    def test_human_block_is_open_without_busy_retries(self):
        a=self.job();self.q.defer(a['key'],'waiting_human','authentication_required',now=110,delay=3600)
        self.assertEqual(len(self.q.open()),1)
        self.assertIsNone(self.q.claim('owner',now=200))

    def test_backoff_and_five_failure_diagnostic_keeps_owned_request(self):
        a=self.job()
        for i in range(5):self.q.failed(a['key'],'timeout',now=200+i)
        row=self.q.get(a['key'])
        self.assertEqual(row['state'],'needs_diagnosis')
        self.assertEqual(len(self.q.open()),1)
        self.assertGreater(row['due'],204)

    def test_unknown_must_not_become_healthy(self):
        for observation in [None,{'status':'UNKNOWN'},{'status':'OK','verified':False}]:
            self.assertFalse(self.m.verified_observation(observation))
        self.assertTrue(self.m.verified_observation({'status':'OK','verified':True,'target':'fixture','receipt':'r1'}))

    def test_classification_never_auto_replays_payments_or_expired_campaigns(self):
        self.assertEqual(self.m.disposition('Pendente: PC1 ocupado, outra sessão usa a lease.'),'waiting_resource')
        self.assertEqual(self.m.disposition('Bloqueado: confirmação 2FA necessária.'),'waiting_human')
        self.assertEqual(self.m.disposition('Bloqueado: Critical Subset pagamento exige autorização.'),'blocked_decision')
        self.assertEqual(self.m.disposition('Resolvido: conferido.'),'verifying')

    def test_pc1_queue_order_prevents_newcomer_jump(self):
        self.assertTrue(hasattr(self.m,'pc1_admission'),'PC1 FIFO admission missing')
        j=self.q.enqueue('pc1:zeus:first',{'kind':'pc1','profile':'zeus','session_id':'first','thread_id':'123','resource':'pc1'},'pc1_busy',now=100)
        self.assertEqual(self.m.pc1_admission('ares','new','456',db=self.path),j['key'])
        self.assertIsNone(self.m.pc1_admission('zeus','first','123',db=self.path))
        self.assertIsNone(self.m.pc1_admission('zeus','worker','123',operation_key=j['key'],db=self.path))

    def test_timeout_requires_effect_reconciliation(self):
        a=self.job();self.q.failed(a['key'],'TimeoutExpired',now=200)
        self.assertTrue(self.q.get(a['key'])['needs_reconciliation'])

    def test_multiprocess_enqueue_same_request_is_unique(self):
        ps=[multiprocessing.Process(target=enqueue_child,args=(str(self.path),)) for _ in range(4)]
        for p in ps:p.start()
        for p in ps:p.join(10);self.assertEqual(p.exitcode,0)
        self.assertEqual(len(self.q.open()),1)


if __name__=='__main__':unittest.main()
