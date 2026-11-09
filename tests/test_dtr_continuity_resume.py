import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

BASE=Path('/root/mgs-agent');sys.path.insert(0,str(BASE/'scripts'))
TARGET=BASE/'scripts/mgs_dtr_continuity.py'


def fixture():
    return {'summary':{'started_at_et':'2026-11-08T22:53:27-05:00','dtr_users_scanned':2,'dtr_login_ok':2,'dtr_pages_raw':2,'errors':[],'missing_1p_users':[],'op_errors':[]},'dtr_scans':[{'username':'fixture-a','login_ok':True,'accounts':[],'pages':[{'id':'1'}],'errors':[]},{'username':'fixture-b','login_ok':True,'accounts':[],'pages':[{'id':'2'}],'errors':[]}], 'issues':[],'status_counts':{},'restriction_counts':{}}


class DTRContinuityTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TARGET.exists(),'DTR durable per-user progress and delivery continuation absent')
        spec=importlib.util.spec_from_file_location('dtr_cont',TARGET);assert spec and spec.loader
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def test_partial_snapshot_never_publishes(self):
        d=fixture();d['summary']['dtr_login_ok']=1
        with self.assertRaises(ValueError):self.m.validate_snapshot(d)
        d=fixture();d['dtr_scans'][1]['username']='fixture-a'
        with self.assertRaises(ValueError):self.m.validate_snapshot(d)

    def test_resume_preserves_completed_users_after_restart(self):
        p=self.m.Progress(self.root,['a','b'],now=100)
        p.save('a',{'login_ok':True,'pages':[],'accounts':[],'errors':[]},now=110)
        p2=self.m.Progress(self.root,['a','b'],now=150)
        self.assertTrue(p2.read('a',now=150)['login_ok']);self.assertIsNone(p2.read('b',now=150))

    def test_incomplete_and_expired_reads_not_reused(self):
        p=self.m.Progress(self.root,['a'],now=100)
        p.save('a',{'login_ok':False,'pages':[],'errors':['timeout']},now=110)
        self.assertIsNone(p.read('a',now=150))
        p.save('a',{'login_ok':True,'pages':[],'accounts':[],'errors':[]},now=110)
        self.assertIsNone(p.read('a',now=8000))

    def test_delivery_accepted_before_failed_get_does_not_repost(self):
        snapshot=self.root/'snapshot.json';snapshot.write_text(json.dumps(fixture()))
        notices=[];saved=[]
        class Mod:
            def build_report(self,*a):return 'fixture verified report'
            def chunk_discord(self,s):return [s]
            def load_state(self):return {'last_issue_keys':[]}
            def save_state(self,k,s):saved.append(s)
        def post(body,**kwargs):
            if not kwargs.get('prior_id'):
                notices.append(body);kwargs['on_created']('123');raise RuntimeError('GET unavailable after accepted fixture POST')
            self.assertEqual(kwargs['prior_id'],'123');return '123'
        with self.assertRaises(RuntimeError):self.m.deliver(snapshot,self.root/'out',Mod(),post)
        result=self.m.deliver(snapshot,self.root/'out',Mod(),post)
        self.assertEqual(result['status'],'GET_VERIFIED');self.assertEqual(len(notices),1);self.assertEqual(len(saved),1)


if __name__=='__main__':unittest.main()
