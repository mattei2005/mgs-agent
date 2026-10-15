"""Offline orphan-lease proof tests; all sessions and transports are fixtures."""
import contextlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import landing_intake as li
spec=importlib.util.spec_from_file_location('landing_orphan_cli',Path(__file__).resolve().parents[1]/'scripts/ares-direct-traffic-followup.py')
assert spec and spec.loader
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


class FakeQueue:
    def __init__(self,owner='worker-fixture'):
        self.owner=owner;self.events=[];self.db=self;self.root=Path('/OFFLINE_FIXTURE_ONLY')
    def job(self,key):
        if key!='offline-job':raise ValueError('unknown fixture job')
        return {'state':'NEEDS_RECONCILIATION'}
    def execute(self,*args):return SimpleNamespace(fetchone=lambda:{'detail':json.dumps({'owner':self.owner})})
    def tx(self):return contextlib.nullcontext()
    def event(self,*args):self.events.append(args)


class OrphanProofTests(unittest.TestCase):
    state={'locked':True,'agent':'ares','session_id':'offline-orphan-fixture'}
    def run_case(self,*,alive=False,agent='ares',source='tool',owner='worker-fixture',transport=0):
        q=FakeQueue(owner);rows=iter([{'source':source},{'content':'OFFLINE_FIXTURE\n'+json.dumps({'queue_key':'offline-job','owner':'worker-fixture'})}])
        conn=SimpleNamespace(execute=lambda *a:SimpleNamespace(fetchone=lambda:next(rows)))
        with patch.object(cli,'observer_process_alive',return_value=alive),patch.object(li,'readonly',return_value=contextlib.nullcontext(conn)),patch.object(cli.subprocess,'run',return_value=SimpleNamespace(returncode=transport,stdout='{"ok":true,"locked":false}')) as run:
            result=cli.orphan_observer_lease(q,{**self.state,'agent':agent})
            calls=list(run.call_args_list)
        return result,q,calls
    def test_exact_dead_observer_only_can_release(self):
        ok,q,calls=self.run_case();self.assertTrue(ok);self.assertEqual(len(calls),1)
        command=calls[0].args[0]
        self.assertEqual(command[-4:],['--agent','ares','--session-id','offline-orphan-fixture'])
        self.assertEqual(q.events[0][1],'orphan_pc1_lease_released')
        self.assertFalse(q.events[0][2]['automatic_navigation'])
    def test_live_process_never_released(self):
        ok,q,calls=self.run_case(alive=True);self.assertFalse(ok);self.assertFalse(calls)
    def test_other_agent_never_released(self):
        ok,q,calls=self.run_case(agent='zeus');self.assertFalse(ok);self.assertFalse(calls)
    def test_human_conversation_not_observer(self):
        ok,q,calls=self.run_case(source='discord');self.assertFalse(ok);self.assertFalse(calls)
    def test_wrong_worker_binding_not_released(self):
        ok,q,calls=self.run_case(owner='different-fixture');self.assertFalse(ok);self.assertFalse(calls)
    def test_failed_release_does_not_claim_cleanup(self):
        ok,q,calls=self.run_case(transport=2);self.assertFalse(ok);self.assertFalse(q.events)


if __name__=='__main__':unittest.main()
