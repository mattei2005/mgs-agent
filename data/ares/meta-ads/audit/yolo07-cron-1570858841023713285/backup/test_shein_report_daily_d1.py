"""Offline daily D-1 policy/renderer/delivery recovery regressions."""
import unittest,importlib.util,json,copy,tempfile
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
HOME=Path('/root/.hermes/profiles/ares')
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
runner=module('daily_report_test',HOME/'scripts/shein-daily-report.py')
layout=module('daily_layout_test',HOME/'scripts/shein-report-layout.py')
class DailyTests(unittest.TestCase):
    def model(self):
        p=Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/g001-status-blocks-1561918043305803869/787796726891306/model.json')
        m=json.loads(p.read_text());m['rows']=m['rows'][:1]
        for r in m['rows']:
            r['product']=runner.reporting_product(r['name'],layout)
            for h in r['history']:h['partial']=False
        for key in ['insights','configuration','status','budget']:m['source_timestamps'][key]='2026-10-20T07:30:00-04:00'
        m['closed_day_report']={'policy_id':'ARES-SHEIN-DAILY-D1-0800-20261020','period':{'since':'2026-10-19','until':'2026-10-19'},'day_closed':True}
        return m
    def test_closed_day_actual_collection_time_not_backdated(self):
        m=self.model();r=layout.render_model(m);layout.validate_report(m,r['text'])
        self.assertIn('dia fechado',r['text']);self.assertIn('coleta em 20/10 07:30 EDT',r['text']);self.assertIn('ATRASO GAM/SB ATUAL',r['text'])
        self.assertEqual(m['source_timestamps']['insights'],'2026-10-20T07:30:00-04:00')
        self.assertNotIn('19/10/2026 · até',r['text'])
    def test_without_explicit_daily_proof_different_civil_day_rejected(self):
        m=self.model();m.pop('closed_day_report')
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
    def test_partial_closed_day_rejected(self):
        m=self.model();m['rows'][0]['history'][-1]['partial']=True
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
    def test_wrong_policy_rejected(self):
        m=self.model();m['closed_day_report']['policy_id']='unknown'
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
    def test_wrong_period_rejected(self):
        m=self.model();m['closed_day_report']['period']['until']='2026-10-20'
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
    def test_closed_day_cannot_be_today(self):
        m=self.model();m['source_timestamps']['insights']='2026-10-19T23:30:00-04:00'
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
    def test_current_budget_and_spend_intact(self):
        m=self.model();r=m['rows'][0];before=copy.deepcopy(r);r['daily_budget']='150';out=layout.render_model(m)
        self.assertEqual(r['spend'],before['spend']);self.assertEqual(r['history'],before['history']);self.assertIn('orçamento diário vigente',out['text'])
    def test_twenty_four_targets_and_exclusions(self):
        policy=json.loads(runner.POLICY.read_text())
        with patch.object(runner.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            b=runner.resolve(policy)
        self.assertEqual(len(b),24);self.assertTrue(all(not x['account_name'].lower().startswith(('boostingecon','growpowerhub')) for x in b))
    def test_no_early_delivery(self):
        self.assertFalse(runner.delivery_ready(datetime.fromisoformat('2026-10-20T07:59:59-04:00'),'2026-10-19'))
        self.assertTrue(runner.delivery_ready(datetime.fromisoformat('2026-10-20T08:00:00-04:00'),'2026-10-19'))
        self.assertFalse(runner.delivery_ready(datetime.fromisoformat('2026-10-21T08:00:00-04:00'),'2026-10-19'))
    def test_DST_uses_new_york_civil_time(self):
        for iso,day in [('2026-11-02T08:00:00-05:00','2026-11-01'),('2027-03-15T08:00:00-04:00','2027-03-14')]:
            self.assertTrue(runner.delivery_ready(datetime.fromisoformat(iso),day))
    def test_missing_revenue_never_zero(self):
        self.assertIsNone(runner.sumfield([],'NET_REVENUE',layout));self.assertEqual(runner.sumfield([{'NET_REVENUE':0}],'NET_REVENUE',layout),Decimal(0))
        self.assertIsNone(runner.sumfield([{'NET_REVENUE':None}],'NET_REVENUE',layout))
    def delivery(self,temp):
        b={'account_id':'123','thread_id':'456','manager_code':'g001'};p=Path(temp)/'123';p.mkdir()
        runner.save(p/'model.json',{'rows':[]});runner.save(p/'report.parts.json',['valid part']);(p/'report.md').write_text('valid part')
        r=SimpleNamespace(root=Path(temp),day='2026-10-19',layout=SimpleNamespace(validate_report=lambda *a:True))
        class FakeDiscord:
            def __init__(self):self.posts=0
            def call(self,method,path,payload=None):
                if method=='POST':self.posts+=1
                return {'id':'789','channel_id':'456','author':{'id':runner.BOT_ID},'content':'valid part'}
        return b,p,r,FakeDiscord()
    def test_replay_verified_delivery_zero_new_posts(self):
        with tempfile.TemporaryDirectory(dir=HOME/'cache/scratch') as t:
            b,p,r,d=self.delivery(t);runner.deliver_account(r,b,d);self.assertEqual(d.posts,1)
            runner.deliver_account(r,b,d);self.assertEqual(d.posts,1)
    def test_ambiguous_post_never_repeated(self):
        with tempfile.TemporaryDirectory(dir=HOME/'cache/scratch') as t:
            b,p,r,d=self.delivery(t);runner.deliver_account(r,b,d);intent=runner.load(p/'delivery-intent-0.json');intent.pop('message_id');intent['status']='IN_FLIGHT';runner.save(p/'delivery-intent-0.json',intent)
            d.call=lambda *a,**k:[]
            with self.assertRaises(AssertionError):runner.deliver_account(r,b,d)
            self.assertEqual(d.posts,1)
if __name__=='__main__':unittest.main()
