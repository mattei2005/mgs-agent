"""OS-level interleavings for release admission; synthetic files, no financial API."""
import contextlib, datetime, fcntl, importlib.util, json, os, pathlib, subprocess, sys, tempfile, time, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance_release_guard import lease, admit_entrypoint, trigger_time
from finance_release import publish, recover, LocalFiles, ReleaseError

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='finance-release-test-')
        self.root = pathlib.Path(self.temp.name)
        (self.root/'private').mkdir()
        self.addCleanup(self.temp.cleanup)
    def test_shared_jobs_can_overlap(self):
        with lease(self.root), lease(self.root, timeout=.2):
            pass
    def test_exclusive_wait_is_bounded_without_modification(self):
        with lease(self.root):
            with self.assertRaises(TimeoutError):
                with lease(self.root, exclusive=True, timeout=.1): pass
        self.assertFalse((self.root/'private/release-current.json').exists())
    def test_job_waits_and_reads_only_complete_version(self):
        (self.root/'a').write_text('old'); (self.root/'b').write_text('old')
        code = "from finance_release_guard import lease;import pathlib,json,sys;p=pathlib.Path(sys.argv[1]);\nwith lease(p): print(json.dumps([(p/'a').read_text(),(p/'b').read_text()]),flush=True)"
        with lease(self.root, exclusive=True):
            p = subprocess.Popen([sys.executable,'-c',code,str(self.root)],cwd=ROOT,stdout=subprocess.PIPE,text=True)
            self.addCleanup(lambda: p.kill() if p.poll() is None else None)
            (self.root/'a').write_text('new');time.sleep(.15)
            self.assertIsNone(p.poll())
            (self.root/'b').write_text('new')
        out,_=p.communicate(timeout=5)
        self.assertEqual(p.returncode,0);self.assertEqual(json.loads(out),['new','new'])
    def test_original_slot_survives_wait(self):
        code="from finance_release_guard import admit_entrypoint,trigger_time;import pathlib,datetime,json,sys;admit_entrypoint(pathlib.Path(sys.argv[1]));print(trigger_time(datetime.datetime.now(datetime.timezone.utc)).isoformat(),flush=True)"
        with lease(self.root,exclusive=True):
            p=subprocess.Popen([sys.executable,'-c',code,str(self.root)],cwd=ROOT,stdout=subprocess.PIPE,text=True)
            self.addCleanup(lambda:p.kill() if p.poll() is None else None)
            time.sleep(.3);released=datetime.datetime.now(datetime.timezone.utc)
        out,_=p.communicate(timeout=5);self.assertEqual(p.returncode,0)
        self.assertLess(datetime.datetime.fromisoformat(out.strip()),released)
    def test_killed_holder_does_not_leave_lock(self):
        code="from finance_release_guard import lease;import pathlib,sys,time;\nwith lease(pathlib.Path(sys.argv[1]),exclusive=True): print('ready',flush=True);time.sleep(30)"
        p=subprocess.Popen([sys.executable,'-c',code,str(self.root)],cwd=ROOT,stdout=subprocess.PIPE,text=True)
        self.assertEqual(p.stdout.readline().strip(),'ready');p.kill();p.wait(timeout=5);p.stdout.close()
        with lease(self.root,timeout=.2):pass

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='finance-publish-test-');self.root=pathlib.Path(self.temp.name);self.addCleanup(self.temp.cleanup)
        (self.root/'private').mkdir();self.candidate=self.root/'candidate';self.candidate.mkdir()
        self.targets=self.root/'targets';self.targets.mkdir()
        for name in ['one.py','two.py']:(self.targets/name).write_text('old\n');(self.candidate/name).write_text('new\n')
        self.adapter=LocalFiles(self.targets)
        import hashlib
        sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
        self.plan={'schema':1,'release_id':'test-release','authority':'1551985522380111956','files':[{'host':'local','path':n,'source':n,'before':sha('old\n'),'after':sha('new\n')} for n in ['one.py','two.py']]}
        self.adapters={'local':self.adapter}
    def call(self,**kw):
        return publish(self.root,self.candidate,self.plan,self.adapters,preflight=lambda:None,verify=lambda:None,**kw)
    def test_publish_and_readback(self):
        r=self.call();self.assertEqual(r['state'],'committed')
        self.assertEqual((self.targets/'one.py').read_text(),'new\n')
    def test_validation_failure_leaves_old_available(self):
        def bad():raise ReleaseError('catalog missing')
        with self.assertRaises(ReleaseError):publish(self.root,self.candidate,self.plan,self.adapters,preflight=bad,verify=lambda:None)
        self.assertEqual((self.targets/'one.py').read_text(),'old\n')
        with lease(self.root,timeout=.2):pass
    def test_after_write_failure_rolls_back_both(self):
        def bad():raise ReleaseError('health')
        with self.assertRaises(ReleaseError):publish(self.root,self.candidate,self.plan,self.adapters,preflight=lambda:None,verify=bad)
        for n in ['one.py','two.py']:self.assertEqual((self.targets/n).read_text(),'old\n')
        self.assertEqual(json.loads((self.root/'private/release-current.json').read_text())['state'],'rolled_back')
    def test_stale_target_aborts_before_write(self):
        (self.targets/'two.py').write_text('concurrent')
        with self.assertRaises(ReleaseError):self.call()
        self.assertEqual((self.targets/'one.py').read_text(),'old\n')
    def test_candidate_tamper_aborts(self):
        (self.candidate/'two.py').write_text('tampered')
        with self.assertRaises(ReleaseError):self.call()
        self.assertEqual((self.targets/'one.py').read_text(),'old\n')
    def test_traversal_rejected(self):
        self.plan['files'][0]['path']='../escape'
        with self.assertRaises(ReleaseError):self.call()
    def test_partial_write_crash_recovered_by_journal(self):
        original=self.adapter.write;count=0
        def crash(path,data,expected):
            nonlocal count
            original(path,data,expected);count+=1
            if count==1:raise SystemExit('simulated process death')
        self.adapter.write=crash
        with self.assertRaises(SystemExit):self.call()
        self.adapter.write=original
        self.assertEqual(recover(self.root,self.adapters)['state'],'rolled_back')
        for n in ['one.py','two.py']:self.assertEqual((self.targets/n).read_text(),'old\n')
    def test_unknown_concurrent_content_never_overwritten_by_recovery(self):
        def death():raise SystemExit('simulated')
        with self.assertRaises(SystemExit):publish(self.root,self.candidate,self.plan,self.adapters,preflight=lambda:None,verify=death)
        (self.targets/'one.py').write_text('third party')
        with self.assertRaises(ReleaseError):recover(self.root,self.adapters)
        self.assertEqual((self.targets/'one.py').read_text(),'third party')
    def test_exclusive_publisher_timeout_preserves_files(self):
        with lease(self.root):
            with self.assertRaises(TimeoutError):self.call(lock_timeout=.1)
        self.assertEqual((self.targets/'one.py').read_text(),'old\n')

class RemoteFenceTests(unittest.TestCase):
    def test_late_remote_write_cannot_overwrite_rolled_back_version(self):
        import base64,hashlib
        from finance_release import REMOTE_SCRIPT,REMOTE_FENCE_SCRIPT,TARGET
        with tempfile.TemporaryDirectory(prefix='finance-remote-fence-') as d:
            p=pathlib.Path(d);(p/'private').mkdir();(p/'file.py').write_bytes(b'old')
            def run(script,payload):
                return subprocess.run([sys.executable,'-c',script.replace(TARGET,d)],input=json.dumps(payload),capture_output=True,text=True,timeout=5)
            def phase(value):
                r=run(REMOTE_FENCE_SCRIPT,{'release_id':'synthetic','phase':value});self.assertEqual(r.returncode,0,r.stderr)
            phase('applying')
            payload={'action':'write','path':'file.py','release_id':'synthetic','phase':'applying','expected':hashlib.sha256(b'old').hexdigest(),'sha256':hashlib.sha256(b'new').hexdigest(),'data':base64.b64encode(b'new').decode()}
            phase('rolling_back');phase('rolled_back')
            self.assertNotEqual(run(REMOTE_SCRIPT,payload).returncode,0)
            self.assertEqual((p/'file.py').read_bytes(),b'old')
            self.assertNotEqual(run(REMOTE_FENCE_SCRIPT,{'release_id':'synthetic','phase':'applying'}).returncode,0)
    def test_remote_roundtrip_and_rollback(self):
        import base64,hashlib
        from finance_release import REMOTE_SCRIPT,REMOTE_FENCE_SCRIPT,TARGET
        with tempfile.TemporaryDirectory(prefix='finance-remote-roundtrip-') as d:
            p=pathlib.Path(d);(p/'private').mkdir();(p/'file.py').write_bytes(b'old')
            def run(script,payload):
                r=subprocess.run([sys.executable,'-c',script.replace(TARGET,d)],input=json.dumps(payload),capture_output=True,text=True,timeout=5)
                self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
            for phase,before,after in [('applying',b'old',b'new'),('rolling_back',b'new',b'old')]:
                run(REMOTE_FENCE_SCRIPT,{'release_id':'roundtrip','phase':phase})
                run(REMOTE_SCRIPT,{'action':'write','path':'file.py','release_id':'roundtrip','phase':phase,'expected':hashlib.sha256(before).hexdigest(),'sha256':hashlib.sha256(after).hexdigest(),'data':base64.b64encode(after).decode()})
                self.assertEqual((p/'file.py').read_bytes(),after)
            run(REMOTE_FENCE_SCRIPT,{'release_id':'roundtrip','phase':'rolled_back'})

class EntrypointTests(unittest.TestCase):
    def test_admission_precedes_business_imports(self):
        for name, boundary in [('finance_gam_revenue_sync.py','from gam_revenue import'),('finance_media_spend_sync.py','from finance_spend_sources import'),('sync-quotes.py','from mgs_google_workspace_auth import')]:
            text=(ROOT/name).read_text()
            self.assertLess(text.index('admit_entrypoint('),text.index(boundary),name)
    def test_both_scheduled_clocks_preserve_dispatch_slot(self):
        for name in ['finance_gam_revenue_sync.py','finance_media_spend_sync.py']:
            self.assertIn('trigger_time(', (ROOT/name).read_text())
    def test_long_lived_worker_leases_each_tick_not_whole_lifetime(self):
        text=(ROOT/'meta-lookup-worker.py').read_text()
        self.assertIn('with lease(ROOT):\n  return _tick(target)',text)
    def test_production_policy_cannot_replace_its_guard(self):
        from finance_release import production_policy
        with self.assertRaises(ReleaseError):production_policy({'files':[{'host':'local','path':'apps/finance-system/finance_release_guard.py'}]},ROOT)

if __name__=='__main__':unittest.main()
