"""Offline intraday authorization, isolation, DST and nonce regressions."""
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

HOME = Path('/root/.hermes/profiles/ares')
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
m = load('intraday_tests', HOME/'scripts/shein-intraday-report.py')
layout = load('intraday_layout_tests', HOME/'scripts/shein-report-layout.py')

class IntradayTests(unittest.TestCase):
    def test_policy_scope_exact_D1(self):
        with patch.object(m.daily.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            policy, bindings = m.resolve_policy()
        self.assertEqual(len(bindings), 24)
        self.assertEqual(len({b['account_id'] for b in bindings}),24)
        self.assertEqual(policy['slots'], list(m.SLOTS))
        self.assertFalse(policy['meta_writes'])

    def test_scope_drift_blocked(self):
        real = m.daily.load
        def altered(p):
            value = real(p)
            if p == m.POLICY:
                value['account_ids'] = value['account_ids'][:-1]
            return value
        with patch.object(m.daily,'load',side_effect=altered):
            with self.assertRaises(AssertionError):m.resolve_policy()

    def test_all_slots_DST_both_sides(self):
        for day,offset in [('2026-10-30','-04:00'),('2026-11-02','-05:00'),('2027-03-15','-04:00')]:
            for slot in m.SLOTS:
                self.assertTrue(m.eligible(datetime.fromisoformat(day+'T'+slot+':25'+offset),slot))
                self.assertFalse(m.eligible(datetime.fromisoformat(day+'T'+slot+':00'+offset).replace(hour=1),slot))

    def test_no_implicit_catchup(self):
        self.assertFalse(m.eligible(datetime.fromisoformat('2026-10-28T09:34:00-04:00'),'09:32'))
        self.assertFalse(m.eligible(datetime.fromisoformat('2026-10-28T09:31:59-04:00'),'09:32'))

    def test_slot_roots_distinct_from_each_other_and_D1(self):
        roots=[m.run_root('2026-10-28',s) for s in m.SLOTS]
        self.assertEqual(len(set(roots)),5)
        for p in roots:self.assertNotIn('shein-daily-report',str(p))
        self.assertNotEqual(m.run_root('2026-10-28','09:32',True),roots[0])

    def test_partial_only_current_date(self):
        runner=m.Runner.__new__(m.Runner)
        runner.day='2026-10-28';runner.slot='23:31';runner.policy={'policy_id':'test'}
        self.assertTrue(runner.history_partial('2026-10-28'))
        self.assertFalse(runner.history_partial('2026-10-27'))
        self.assertNotIn('closed_day_report',runner.period_evidence())
        self.assertIn('23:31',runner.period_limitation())

    def test_D1_default_hooks_unchanged(self):
        runner=m.daily.Runner.__new__(m.daily.Runner)
        runner.day='2026-10-27';runner.policy={'policy_id':'D1'}
        self.assertFalse(runner.history_partial('2026-10-27'))
        self.assertTrue(runner.period_evidence()['closed_day_report']['day_closed'])
        self.assertIn('dia fechado',runner.period_limitation())

    def model(self):
        p=Path('/root/mgs-agent/data/ares/meta-ads/state/shein-daily-report/2026-10-27/787796726891306/model.json')
        value=json.loads(p.read_text());value['rows']=value['rows'][:1]
        value.pop('closed_day_report')
        # Synthetic current-day fixture: never written to production nor represented as live evidence.
        for key in ['insights','configuration','status','budget','sb']:
            value['source_timestamps'][key]='2026-10-27T23:35:00-04:00'
        value['rps_source']['observed_at']='2026-10-27T23:35:00-04:00'
        value['rows'][0]['history'][-1]['partial']=True
        value['configuration_limitations']=['Fixture intraday; dia parcial.']
        return value

    def test_intraday_render_and_validate(self):
        value=self.model();result=layout.render_model(value)
        layout.validate_report(value,result['text'])
        self.assertIn('parcial',result['text'].lower())
        self.assertIn('23:35',result['text'])
        self.assertNotIn('dia fechado',result['text'])

    def delivery(self, root):
        b={'account_id':'123','thread_id':'456','manager_code':'g001'}
        p=root/'123';p.mkdir()
        m.daily.save(p/'model.json',{'rows':[]})
        m.daily.save(p/'report.parts.json',['valid part'])
        (p/'report.md').write_text('valid part')
        runner=SimpleNamespace(root=root,day='2026-10-28',layout=SimpleNamespace(validate_report=lambda *a:True))
        class FakeDiscord:
            def __init__(self):self.posts=0;self.nonce=None
            def call(self,method,path,payload=None):
                if method=='POST':self.posts+=1;self.nonce=payload['nonce']
                return {'id':'789','channel_id':'456','author':{'id':m.daily.BOT_ID},'content':'valid part'}
        return b,p,runner,FakeDiscord()

    def test_slot_nonce_does_not_dedupe_another_slot(self):
        nonces=[]
        with tempfile.TemporaryDirectory(dir=HOME/'cache/scratch') as temp:
            for i,slot in enumerate(m.SLOTS):
                root=Path(temp)/str(i);root.mkdir()
                b,p,r,d=self.delivery(root)
                m.daily.deliver_account(r,b,d,run_key='2026-10-28:intraday:'+slot)
                nonces.append(d.nonce)
                m.daily.deliver_account(r,b,d,run_key='2026-10-28:intraday:'+slot)
                self.assertEqual(d.posts,1)
        self.assertEqual(len(set(nonces)),5)

    def test_legacy_nonce_bytes_preserved(self):
        with tempfile.TemporaryDirectory(dir=HOME/'cache/scratch') as temp:
            b,p,r,d=self.delivery(Path(temp));m.daily.deliver_account(r,b,d)
            sha=hashlib.sha256(b'valid part').hexdigest()
            expected=str(int(hashlib.sha256(('2026-10-28:123:0:'+sha).encode()).hexdigest()[:15],16))
            self.assertEqual(d.nonce,expected)

    def test_timezone_drift_rejected_before_collection(self):
        r=m.Runner.__new__(m.Runner);r.day=datetime.now(m.NY).date().isoformat()
        with self.assertRaises(AssertionError):r.validate_report_day({'timezone_name':'Europe/London'})

if __name__=='__main__':unittest.main()
