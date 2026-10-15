"""Offline completion-barrier tests; fixture channels are never contacted."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_finish_all as finish


class FinishAllTests(unittest.TestCase):
    setUpBase=fixtures.FollowupTests.setUp
    tearDown=fixtures.FollowupTests.tearDown
    arm=fixtures.FollowupTests.arm

    def setUp(self):
        self.setUpBase();self.arm()
        self.inventory=self.root/'audit-inventory.json'
        self.targets=[{'thread_id':str(160000000000000000+i),'channel_id':str(170000000000000000+i//6)} for i in range(36)]
        self.inventory.write_text(json.dumps({'targets':self.targets}))
        self.checkpoint=self.root/'data/agent-checkpoints.json'
        self.checkpoint.write_text(json.dumps({'checkpoints':[{'id':'offline-audit','state':'completed'}]}))
        self.plan=self.q.root/'finish-all-20261015.json'
        self.plan.write_text(json.dumps({'status':'ACTIVE','origin_thread_id':core.INCIDENT_THREAD,'notification_key':'finish-all:offline','audit_checkpoint_id':'offline-audit','landing_jobs':[self.key],'audit_inventory':str(self.inventory),'layout_test_dir':str(self.root),'authority':'offline explicit fixture'}))
        self.job={'key':self.key,'state':'COMPLETE','links':[{'state':'PASSED'} for _ in range(46)]}
        with self.q.tx():self.q.prepare_message(self.key+':success','150000000000000002',core.SUCCESS)
        self.dc.deliver(self.q,self.key+':success')
        original=self.dc.get
        parents={t['thread_id']:t['channel_id'] for t in self.targets};self.not_empty=False
        def get(path):
            tid=path.split('/')[2]
            if tid in parents:
                if '/messages' in path:return [{'id':'offline-still-present'}] if self.not_empty else []
                return {'id':tid,'parent_id':parents[tid]}
            if tid in parents.values():return {'id':tid}
            return original(path)
        self.dc.get=get

    def cycle(self):
        with patch.object(self.q,'job',return_value=self.job),patch.object(finish.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            return finish.cycle(self.q,lambda:self.dc)

    def test_waits_for_audit_no_notice(self):
        self.checkpoint.write_text(json.dumps({'checkpoints':[{'id':'offline-audit','state':'in_progress'}]}))
        self.assertEqual(self.cycle()['state'],'WAITING_AUDIT');self.assertEqual(self.dc.posts,2)

    def test_waits_for_final_link_and_manager(self):
        self.job['links'][-1]['state']='WAIT_RETRY'
        self.assertEqual(self.cycle()['state'],'WAITING_LANDING_OR_MANAGER_NOTICE');self.assertEqual(self.dc.posts,2)

    def test_nonempty_thread_blocks_success(self):
        self.not_empty=True
        self.assertEqual(self.cycle()['state'],'WAITING_EMPTY_THREAD_READBACK');self.assertEqual(self.dc.posts,2)

    def test_exact_36_and_six_parent_coverage_required(self):
        self.inventory.write_text(json.dumps({'targets':self.targets[:-1]}))
        with self.assertRaisesRegex(ValueError,'36-thread'):self.cycle()

    def test_layout_failure_blocks_notice(self):
        with patch.object(self.q,'job',return_value=self.job),patch.object(finish.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(ValueError,'layout tests failed'):finish.cycle(self.q,lambda:self.dc)
        self.assertEqual(self.dc.posts,2)

    def test_verified_notice_once_after_all_real_gates(self):
        result=self.cycle();self.assertEqual(result['state'],'COMPLETE');self.assertEqual(self.dc.posts,3)
        self.assertEqual(self.cycle()['state'],'COMPLETE');self.assertEqual(self.dc.posts,3)
        row=self.q.db.execute("select * from messages where key='finish-all:offline'").fetchone()
        self.assertEqual(row['state'],'VERIFIED');self.assertEqual(row['thread'],core.INCIDENT_THREAD)
        self.assertEqual(row['content'],finish.CONTENT)

    def test_final_review_is_explicit_not_false_all_complete(self):
        policy=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';policy.parent.mkdir(exist_ok=True)
        policy.write_text(json.dumps({'no_ad_retry_policy':{'generation':'offline-final'}}))
        self.job['state']='WAITING_HUMAN';self.job['links'][-1]={'idx':45,'state':'REVIEW_REQUIRED'}
        self.assertEqual(self.cycle()['state'],'WAITING_REVIEW_NOTICE_READBACK')
        key='landing-final-review:offline-final:'+self.key+':45'
        with self.q.tx():
            self.q.prepare_message(key,core.INCIDENT_THREAD,'offline final-review fixture')
            self.q.event(self.key,'finite_review_report_authorized',{'notification_key':key})
        self.dc.deliver(self.q,key)
        self.assertEqual(self.cycle()['state'],'COMPLETE')
        row=self.q.db.execute("select content from messages where key='finish-all:offline'").fetchone()
        self.assertIn('45/46',row['content']);self.assertIn('aviso integral desse pedido ao gestor continua pendente',row['content'])
        self.assertNotIn('Tudo concluído',row['content'])


if __name__=='__main__':unittest.main()
