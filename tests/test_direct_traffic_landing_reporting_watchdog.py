"""Offline report-stagnation regressions; not live observation evidence."""
import json
import unittest
from unittest.mock import patch
import test_direct_traffic_landing_followup as fixtures
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3 import landing_followup_reporting as reporting


class ReportWatchdogTests(unittest.TestCase):
    setUp=fixtures.FollowupTests.setUp
    tearDown=fixtures.FollowupTests.tearDown
    arm=fixtures.FollowupTests.arm
    success=fixtures.FollowupTests.success
    closure=fixtures.FollowupTests.closure

    def cfg(self):
        path=self.root/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json';path.parent.mkdir(exist_ok=True);path.write_text('{}')
        return {'enabled':True,'generation':'150000000000000088','authority_message_id':'150000000000000088','thread_id':core.INCIDENT_THREAD,'interval_seconds':900,'report_jobs':[self.key],'on_material_change_only':True,'diagnose_after_equivalent_reports':3}

    def delivered_repeats(self,n,cfg):
        old={**cfg,'on_material_change_only':False}
        for _ in range(n):
            reporting.cycle(self.q,lambda:self.dc,old);self.clock.value+=900

    def test_timer_and_claim_do_not_send_same_material_again(self):
        self.arm();cfg=self.cfg();reporting.cycle(self.q,lambda:self.dc,cfg)
        self.clock.value+=900;self.q.claim('worker')
        self.assertIsNone(reporting.prepare(self.q,cfg));self.assertEqual(self.dc.posts,2)
        self.q.begin(self.key,'worker',0)
        self.assertIsNone(reporting.prepare(self.q,cfg));self.assertEqual(self.dc.posts,2)

    def test_third_delivered_equivalent_requires_diagnosis_once(self):
        self.arm();cfg=self.cfg();self.delivered_repeats(3,cfg)
        self.assertIsNone(reporting.prepare(self.q,cfg));self.assertIsNone(reporting.prepare(self.q,cfg))
        rows=self.q.db.execute("SELECT detail FROM events WHERE kind='progress_stall_diagnosis_required'").fetchall()
        self.assertEqual(len(rows),1);d=json.loads(rows[0]['detail'])
        self.assertEqual(d['equivalent_delivered_reports'],3);self.assertTrue(d['resolution_requires_real_progress'])
        self.assertEqual(d['pending'][0]['job'],self.key)

    def test_two_reports_do_not_trigger_third_report_threshold(self):
        self.arm();cfg=self.cfg();self.delivered_repeats(2,cfg);reporting.prepare(self.q,cfg)
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM events WHERE kind='progress_stall_diagnosis_required'").fetchone())

    def test_unsent_prepared_reports_are_not_delivered_duplicates(self):
        self.arm();cfg=self.cfg();old={**cfg,'on_material_change_only':False}
        for _ in range(3):reporting.prepare(self.q,old);self.clock.value+=900
        reporting.prepare(self.q,cfg)
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM events WHERE kind='progress_stall_diagnosis_required'").fetchone())

    def test_claim_or_open_intent_cannot_clear_diagnosis(self):
        self.arm();cfg=self.cfg();self.delivered_repeats(3,cfg);reporting.prepare(self.q,cfg)
        self.q.claim('worker');self.q.begin(self.key,'worker',0);reporting.prepare(self.q,cfg)
        self.assertIsNone(self.q.db.execute("SELECT 1 FROM events WHERE kind='progress_stall_progress_resumed'").fetchone())

    def test_real_validated_pass_clears_stall_and_allows_changed_report(self):
        self.arm();cfg=self.cfg();self.delivered_repeats(3,cfg);reporting.prepare(self.q,cfg)
        self.q.claim('worker');self.q.begin(self.key,'worker',0);self.q.result(self.key,'worker',0,'PASS',self.success())
        self.assertIsNotNone(reporting.prepare(self.q,cfg))
        row=self.q.db.execute("SELECT detail FROM events WHERE kind='progress_stall_progress_resumed'").fetchone();self.assertIsNotNone(row)
        self.assertIn('validated_result_seq',json.loads(row['detail']))

    def test_worker_prompt_requires_repair_not_only_silencing(self):
        self.arm();j=self.q.job(self.key);j['stagnation_diagnosis']=[{'incident':'offline','required_action':'offline diagnosis'}]
        text=core.worker_prompt(self.key,'worker',0,j)
        self.assertIn('DIAGNÓSTICO OBRIGATÓRIO POR ESTAGNAÇÃO',text);self.assertIn('Silenciar status não resolve',text)

    def test_three_consecutive_technical_errors_require_diagnosis_even_without_new_messages(self):
        self.arm();j=self.q.job(self.key);j['recent_technical_errors']=[{'idx':0,'attempt':n,'diagnosis':'offline same opening failure'} for n in [5,4,3]]
        text=core.worker_prompt(self.key,'worker',0,j)
        self.assertIn('DIAGNÓSTICO OBRIGATÓRIO POR ESTAGNAÇÃO',text)
        self.assertTrue(json.loads(text.rsplit('\n',1)[-1])['repeated_technical_failure'])


if __name__=='__main__':unittest.main()
