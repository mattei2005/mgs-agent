import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_automation_continuity import Queue
from mgs_continuity_health import rows


class HealthTests(unittest.TestCase):
    def test_enabled_consumer_heartbeat_failure_is_not_healthy_zero(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'queue.sqlite3';q=Queue(path)
            q.service('enabled',True);q.service('heartbeat',{'at':100,'phase':'idle','pid':os.getpid()});q.close()
            self.assertEqual(rows(1000,path)[0][1],'ERROR')

    def test_not_enabled_does_not_fabricate_installed_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'queue.sqlite3';q=Queue(path);q.close()
            self.assertEqual(rows(time.time(),path),[])

    def test_live_dispatch_is_bounded_and_queue_remains_observable(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'queue.sqlite3';q=Queue(path)
            q.service('enabled',True);q.service('heartbeat',{'at':100,'phase':'dispatching','pid':os.getpid()});q.close()
            self.assertEqual(rows(1000,path)[0][1],'OK')
            self.assertEqual(rows(2300,path)[0][1],'ERROR')


class FakeResolver:
    CHANNEL_ID='1498132022634483894'
    def __init__(self):
        self.state={'last_seen_id':'100','processed':{'100':{'status':'escalated','started_at':'2026-11-08T00:00:00-05:00','resolution_text':'Bloqueado: 2FA necessária.'}}}
        self.message={'id':'100','embeds':[{'fields':[{'name':'Script','value':'`hermes:zeus:fixture`'}]}]}
    def load_token(self):return 'isolated-fixture-token'
    def load_state(self):return self.state
    def save_state(self,state):self.state=state
    def fetch_messages(self,*a,**kw):return []
    def discord_api(self,*a,**kw):return 200,self.message
    def is_candidate(self,m):return True
    def message_url(self,m):return 'https://discord.com/channels/1/2/100'


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('supervisor_integration','/root/mgs-agent/scripts/mgs_automation_supervisor.py');assert spec and spec.loader
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=Path(self.tmp.name)/'queue.sqlite3'
        self.resolver=FakeResolver();self.sent=[]
        self.obs={'native:zeus:fixture':{'status':'ERROR','verified':False,'target':'fixture','receipt':'isolated producer failure','at':time.time(),'source':{'kind':'native','profile':'zeus','job_id':'fixture'}}}

    def tick(self):
        def post(body,**kw):
            self.sent.append(body)
            if kw.get('on_created'):kw['on_created']('200')
            return '200'
        with patch.dict(os.environ,{'MGS_CONTINUITY_DB':str(self.db)}),patch.object(sys,'argv',['fixture']),patch.object(self.m,'collect',return_value=(self.obs,[])),patch.object(self.m,'original_active',return_value=False),patch.object(self.m,'drive',return_value=0),patch('mgs_alert_transport.post_verified',side_effect=post):
            self.assertEqual(self.m.main(self.resolver),0)

    def test_repeated_ingress_never_postpones_or_reopens_human_gate(self):
        self.tick();q=Queue(self.db);first=q.open()[0];q.close()
        self.tick();q=Queue(self.db);second=q.open()[0];q.close()
        self.assertEqual(first['key'],second['key']);self.assertEqual(first['due'],second['due'])
        self.assertEqual(second['state'],'waiting_human');self.assertEqual(len(self.sent),1)

    def test_validated_closed_legacy_source_not_enqueued_again(self):
        self.tick();q=Queue(self.db);job=q.open()[0]
        q.complete(job['key'],{'verified':True,'target':'fixture','receipt':'isolated exact-target readback'});q.close()
        self.obs['native:zeus:fixture'].update(status='OK',verified=True,receipt='isolated exact-target readback',at=time.time())
        self.tick();q=Queue(self.db);self.assertEqual(q.open(),[]);q.close()
        self.assertEqual(self.resolver.state['processed']['100']['status'],'done')

if __name__=='__main__':unittest.main()
