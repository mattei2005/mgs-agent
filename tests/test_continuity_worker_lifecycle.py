import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')


class WorkerLifecycleTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('supervisor_lifecycle','/root/mgs-agent/scripts/mgs_automation_supervisor.py');assert spec and spec.loader
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_child_fingerprint_survives_parent_loss_without_pid_reuse(self):
        self.assertTrue(hasattr(self.m,'worker_active'),'child ownership receipt absent')
        directory=self.root/'fixture-key';directory.mkdir()
        receipt={'pid':os.getpid(),'start_ticks':self.m.process_ticks(os.getpid()),'state':'running'}
        (directory/'worker.json').write_text(json.dumps(receipt))
        self.assertTrue(self.m.worker_active('fixture-key',self.root))
        receipt['start_ticks']='wrong-pid-generation';(directory/'worker.json').write_text(json.dumps(receipt))
        self.assertFalse(self.m.worker_active('fixture-key',self.root))

    def test_worker_receives_actual_wall_budget_and_checkpoint_guard(self):
        actual=subprocess.Popen;prompts=[]
        def spawn(args,**kwargs):
            prompts.append(args[-1]);return actual([sys.executable,'-c','print("Pendente: isolated bounded fixture.")'],**kwargs)
        row={'key':'budget-fixture','source_key':'native:zeus:fixture','source':json.dumps({'kind':'native','profile':'zeus'}),'observation':None}
        with patch.dict(os.environ,{'MGS_CONTINUITY_RUN_ROOT':str(self.root)}),patch.object(self.m,'build_prompt',return_value='isolated fixture'),patch.object(self.m.subprocess,'Popen',side_effect=spawn):
            self.m.run_worker(row,'diagnose_only',timeout=17)
        self.assertIn('17 segundos',prompts[0]);self.assertIn('checkpoint',prompts[0]);self.assertIn('lotes',prompts[0])

    def test_timeout_stops_only_its_owned_worker_process_group(self):
        actual=subprocess.Popen;children=[]
        def spawn(*args,**kwargs):
            p=actual([sys.executable,'-c','import time; time.sleep(30)'],**kwargs);children.append(p);return p
        row={'key':'isolated-fixture','source_key':'native:zeus:fixture','source':json.dumps({'kind':'native','profile':'zeus'}),'observation':None}
        with patch.dict(os.environ,{'MGS_CONTINUITY_RUN_ROOT':str(self.root)}),patch.object(self.m,'build_prompt',return_value='isolated fixture; no external actions'),patch.object(self.m.subprocess,'Popen',side_effect=spawn):
            with self.assertRaises(subprocess.TimeoutExpired):self.m.run_worker(row,'diagnose_only',timeout=.05)
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll())
        self.assertFalse(Path('/proc',str(children[0].pid)).exists())

if __name__=='__main__':unittest.main()
